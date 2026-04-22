import pandas as pd
import streamlit as st
import io


# --- CUSTOMIZAÇÃO CSS ---
st.markdown("""
    <style>
    /* Esconde o botão do GitHub / Deploy */
    .stAppDeployButton {visibility: hidden;}
    
    /* (Opcional) Esconde o menu de três pontinhos do Streamlit */
    #MainMenu {visibility: hidden;}
    
    /* (Opcional) Esconde o cabeçalho inteiro com a faixa de decoração */
    header {visibility: hidden;}
    /* 1. Botões de Download (Verdes) */
    div.stDownloadButton > button {
        background-color: #28a745 !important;
        color: white !important;
        border-color: #28a745 !important;
    }
    div.stDownloadButton > button:hover {
        background-color: #218838 !important;
        border-color: #1e7e34 !important;
        color: white !important;
    }
    
    /* 2. Botão Principal / Primary (Vermelho - Usado no botão de Finalizar) */
    button[kind="primary"] {
        background-color: #dc3545 !important;
        color: white !important;
        border-color: #dc3545 !important;
    }
    button[kind="primary"]:hover {
        background-color: #c82333 !important;
        border-color: #bd2130 !important;
        color: white !important;
    }

    /* 3. Textos da Caixa de Upload */
    div[data-testid="stFileUploader"] section button { font-size: 0 !important; }
    div[data-testid="stFileUploader"] section button::after {
        content: "Inserir" !important; font-size: 14px !important;
    }
    div[data-testid="stFileUploaderDropzoneInstructions"] > div > span { font-size: 0 !important; }
    div[data-testid="stFileUploaderDropzoneInstructions"] > div > span::after {
        content: "Arraste e solte o arquivo aqui" !important; font-size: 14px !important;
    }
    div[data-testid="stFileUploaderDropzoneInstructions"] > div > small { display: none !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Processador de Dados - PNP")
st.markdown("""
Faça o upload do arquivo base (**Dados QA**) e escolha quais arquivos deseja atualizar (**Etnia, Renda e/ou Cotas**). O sistema cruzará os dados usando o **CPF** e gerará os arquivos corrigidos.
""")

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Processador de Dados PNP", page_icon="📊", layout="centered")

# --- MENU LATERAL (AJUDA E MANUAL) ---
with st.sidebar:
    st.header("📖 Ajuda e Instruções")
    st.markdown(
        "Dúvidas sobre como usar o sistema ou sobre as regras de cruzamento? Baixe o manual completo da ferramenta:")

    # Tenta ler o arquivo PDF salvo na mesma pasta
    try:
        with open("Manual_PNP.pdf", "rb") as pdf_file:
            pdf_bytes = pdf_file.read()

        st.download_button(
            label="📥 Baixar Manual em PDF",
            data=pdf_bytes,
            file_name="Manual_Processador_PNP.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    except FileNotFoundError:
        # Se você esquecer de colocar o PDF na pasta, o sistema não quebra, só avisa:
        st.warning("⚠️ O arquivo 'Manual_PNP.pdf' não foi encontrado na pasta do sistema.")

    st.divider()
    st.caption("Desenvolvido para uso dos RA`s do Instituto Federal Fluminense.")


# --- CONTROLE DE ESTADO (MEMÓRIA AVANÇADA) ---
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 1

def limpar_resultados():
    """Limpa apenas os botões de download se o usuário trocar algum arquivo."""
    if 'resultados' in st.session_state:
        del st.session_state['resultados']

def limpar_tudo():
    """Função Callback que roda ANTES de a página recarregar para limpar TUDO."""
    st.session_state["uploader_key"] += 1 # Muda a chave forçando os uploaders a resetarem
    if 'resultados' in st.session_state:
        del st.session_state['resultados']

# --- DICIONÁRIOS DE MAPEAMENTO ---
map_renda = {
    '1 SM < RFP <= 1,5 SM': '1,0<RFP<=1,5',
    '0,5 SM < RFP <= 1 SM': '0,5<RFP<=1,0',
    'RFP <= 0,5 SM': '0<RFP<=0,5',
    '1,5 SM < RFP <= 2,5 SM': '1,5<RFP<=2,5',
    'RFP > 3 SM': 'RFP>3,5',
    '2,5 SM < RFP <= 3 SM': '2,5<RFP<=3,5'
}

map_cota = {
    'Processo Seletivo - Ampla Concorrência': 'AC',
    'Mulheres Mil': 'AC',
    'Processo Seletivo - Celiff': 'AC',
    'Processo Seletivo C1 PPI': 'LB_PPI',
    'Processo Seletivo C1': 'LB_PPI',
    'Partiu If - Ep+ppi': 'LB_PPI',
    'Processo Seletivo C2 R': 'LB_EP',
    'Partiu If - Ep+rf': 'LB_EP',
    'Processo Seletivo C3 PPI': 'LI_PPI',
    'Processo Seletivo C3': 'LI_PPI',
    'Processo Seletivo C4 I': 'LI_EP',
    'Partiu If - Ep': 'LI_EP',
    'Processo Seletivo C4': 'LI_EP',
    'Processo Seletivo C5 Q': 'LB_Q',
    'Processo Seletivo C6 PCD': 'LB_PCD',
    'Processo Seletivo PCD1': 'LB_PCD',
    'Partiu If - Ep+pcd': 'LB_PCD',
    'Processo Seletivo C7 Q': 'LI_Q',
    'Processo Seletivo C8 PCD': 'LI_PCD',
    'Processo Seletivo PCD4': 'LI_PCD'
}

# --- FUNÇÕES AUXILIARES ---
@st.cache_data
def processar_dados(file_qa, file_etnia, file_renda, file_cota):
    # 1. Carregar os dados AGORA LENDO EXCEL (.xlsx)
    dados_qa = pd.read_excel(file_qa, dtype={'CPF': str})
    pnp_etnia = pd.read_excel(file_etnia, dtype={'CPF': str})
    pnp_renda = pd.read_excel(file_renda, dtype={'CPF': str})
    pnp_cota = pd.read_excel(file_cota, dtype={'CPF': str})

    # 2. Limpar CPF
    dados_qa['cpf_key'] = dados_qa['CPF'].str.replace(r'\D', '', regex=True)
    pnp_etnia['cpf_key'] = pnp_etnia['CPF'].str.replace(r'\D', '', regex=True)
    pnp_renda['cpf_key'] = pnp_renda['CPF'].str.replace(r'\D', '', regex=True)
    pnp_cota['cpf_key'] = pnp_cota['CPF'].str.replace(r'\D', '', regex=True)

    # 3. Cruzamento de Dados (Join)
    lookup_etnia = dados_qa.drop_duplicates(subset=['cpf_key']).set_index('cpf_key')['Desc_Cor']
    dados_qa['renda_formatada'] = dados_qa['Renda Familiar Per Capita SIG'].map(map_renda)
    lookup_renda = dados_qa.drop_duplicates(subset=['cpf_key']).set_index('cpf_key')['renda_formatada']
    dados_qa['cota_formatada'] = dados_qa['Desc_Forma_Ingresso_Matricula'].map(map_cota)
    lookup_cota = dados_qa.drop_duplicates(subset=['cpf_key']).set_index('cpf_key')['cota_formatada']

    # Atualizações
    pnp_etnia['Cor/Raça'] = pnp_etnia['Cor/Raça'].fillna(pnp_etnia['cpf_key'].map(lookup_etnia)).fillna('Não Declarada')
    pnp_renda['Faixa de Renda'] = pnp_renda['Faixa de Renda'].fillna(pnp_renda['cpf_key'].map(lookup_renda)).fillna(
        'Não declarada')

    if 'Cota' in pnp_cota.columns:
        pnp_cota['Cota'] = pnp_cota['Cota'].fillna(pnp_cota['cpf_key'].map(lookup_cota)).fillna('')
    else:
        pnp_cota['Cota'] = pnp_cota['cpf_key'].map(lookup_cota).fillna('')

    # Remover a coluna chave temporária
    pnp_etnia = pnp_etnia.drop(columns=['cpf_key'])
    pnp_renda = pnp_renda.drop(columns=['cpf_key'])
    pnp_cota = pnp_cota.drop(columns=['cpf_key'])

    return pnp_etnia, pnp_renda, pnp_cota


# Função para converter DataFrame para Excel em memória (bytes)
@st.cache_data
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados_Corrigidos')
    return output.getvalue()


# --- INTERFACE DO USUÁRIO (FRONTEND) ---
st.subheader("1. Upload dos Arquivos (.xlsx)")

col1, col2 = st.columns(2)
with col1:
    file_qa = st.file_uploader("Upload 'Dados QA.xlsx'", type=["xlsx"])
    file_etnia = st.file_uploader("Upload 'cor_raca.xlsx'", type=["xlsx"])
with col2:
    file_renda = st.file_uploader("Upload 'renda.xlsx'", type=["xlsx"])
    file_cota = st.file_uploader("Upload 'cotas.xlsx'", type=["xlsx"])

# Verifica se todos os arquivos foram enviados
if file_qa and file_etnia and file_renda and file_cota:
    st.success("Todos os arquivos foram carregados com sucesso!")

    if st.button("🚀 Processar e Gerar os Arquivos para PNP", use_container_width=True):
        with st.spinner("Lendo arquivos Excel e cruzando dados... Isso pode levar alguns segundos."):

            try:
                # Chama a função de processamento
                df_etnia, df_renda, df_cota = processar_dados(file_qa, file_etnia, file_renda, file_cota)

                # Gera os arquivos Excel em memória
                excel_etnia = to_excel(df_etnia)
                excel_renda = to_excel(df_renda)
                excel_cota = to_excel(df_cota)

                st.subheader("2. Download dos Resultados (.xlsx)")
                st.markdown("Os dados foram processados! Baixe as planilhas Excel geradas abaixo:")

                # Botões de Download
                st.download_button(
                    label="📥 Baixar Fonte_PNP_Etnia_Final.xlsx",
                    data=excel_etnia,
                    file_name="Fonte_PNP_Etnia_Final.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                st.download_button(
                    label="📥 Baixar Fonte_PNP_Renda_Final.xlsx",
                    data=excel_renda,
                    file_name="Fonte_PNP_Renda_Final.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                st.download_button(
                    label="📥 Baixar Fonte_PNP_Cota_Final.xlsx",
                    data=excel_cota,
                    file_name="Fonte_PNP_Cota_Final.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                st.balloons()  # Efeito visual de sucesso

            except Exception as e:
                st.error(
                    f"Ocorreu um erro durante o processamento. Certifique-se de que as planilhas estão no formato correto. Erro: {e}")
    else:
        st.info("Por favor, faça o upload dos 4 arquivos Excel (.xlsx) para habilitar o processamento.")