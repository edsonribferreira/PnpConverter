import pandas as pd
import streamlit as st
import io
import numpy as np

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

# --- CUSTOMIZAÇÃO CSS ---
st.markdown("""
/* Esconde o botão do GitHub / Deploy */
    .stAppDeployButton {visibility: hidden;}
    
    /* (Opcional) Esconde o menu de três pontinhos do Streamlit */
    #MainMenu {visibility: hidden;}
    
    /* (Opcional) Esconde o cabeçalho inteiro com a faixa de decoração */
    header {visibility: hidden;}
    <style>
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
    'Processo Seletivo C1': 'LB_PPI',
    'Processo Seletivo C1 PPI': 'LB_PPI',
    'Processo Seletivo C2': 'LB_EP',
    'Processo Seletivo C2 R': 'LB_EP',
    'Processo Seletivo C3': 'LI_PPI',
    'Processo Seletivo C3 PPI': 'LI_PPI',
    'Processo Seletivo C4': 'LI_EP',
    'Processo Seletivo C4 I': 'LI_EP',
    'Processo Seletivo C5 Q': 'LB_Q',
    'Processo Seletivo C6 PCD': 'LB_PCD',
    'Processo Seletivo C7 Q': 'LI_Q',
    'Processo Seletivo C8 PCD': 'LI_PCD',
    'Processo Seletivo - Celiff': 'AC',
    'Certific': 'AC',
    'Cadastro Eja': 'AC',
    'Transferencia Ex Officio': 'AC',
    'Escola Pública Renda Até 1 Salário': 'LB_EP',
    'Escola Pública Independente da Renda': 'LI_EP',
    'Mulheres Mil': 'AC',
    'Processo Seletivo PCD1': 'LB_PCD',
    'Processo Seletivo PCD2': 'LB_PCD',
    'Processo Seletivo PCD3': 'LI_PCD',
    'Processo Seletivo PCD4': 'LI_PCD',
    'Processo Seletivo Pec- G': 'AC',
    'Partiu If - Ep': 'LI_EP',
    'Partiu If - Ep+pcd': 'LB_PCD',
    'Partiu If - Ep+ppi': 'LB_PPI',
    'Partiu If - Ep+q': 'LB_Q',
    'Partiu If - Ep+rf': 'LB_EP',
    'Portadores de Diploma': 'AC',
    'Pronatec': 'AC',
    'Processo Seletivo - Pós-graduação': 'AC',
    'Processo Seletivo - Ampla Concorrência': 'AC',
    'Sisu - Ampla Concorrência': 'AC',
    'Sisu LB_EP': 'LB_EP',
    'Sisu LB_PCD': 'LB_PCD',
    'Sisu LB_PPI': 'LB_PPI',
    'Sisu LB_Q': 'LB_Q',
    'Sisu C1 - L2': 'LB_PPI',
    'Sisu C2 - L1': 'LB_EP',
    'Sisu C3 - L6': 'LI_PPI',
    'Sisu C4 - L5': 'LI_EP',
    'Sisu LI_EP': 'LI_EP',
    'Sisu LI_PCD': 'LI_PCD',
    'Sisu LI_PPI': 'LI_PPI',
    'Sisu LI_Q': 'LI_Q',
    'Sisu PCD1 - L10': 'LB_PCD',
    'Sisu PCD2': 'LB_PCD',
    'Sisu PCD3 - L14': 'LI_PCD',
    'Sisu PCD4': 'LI_PCD',
    'Transferência Interna': 'AC',
    'Transferência Externa': 'AC',
    'Vestibular - Ampla Concorrência': 'AC',
    'Vestibular C1 PPI': 'LB_PPI',
    'Vestibular C2 R': 'LB_EP',
    'Vestibular C3 PPI': 'LI_PPI',
    'Vestibular C4 I': 'LI_EP',
    'Vestibular C5 Q': 'LB_Q',
    'Vestibular C6 PCD': 'LB_PCD',
    'Vestibular C7 Q': 'LI_Q',
    'Vestibular C8 PCD': 'LI_PCD',
    'Vestibular C1': 'LB_PPI',
    'Vestibular C2': 'LB_EP',
    'Vestibular C3': 'LI_PPI',
    'Vestibular C4': 'LI_EP',
    'Vestibular PCD1': 'LB_PCD',
    'Vestibular PCD2': 'LB_PCD',
    'Vestibular PCD3': 'LI_PCD',
    'Vestibular PCD4': 'LI_PCD'
}

# --- LISTAS E DICIONÁRIOS ---
# Adicionamos o vazio ('') como válido para o sistema aceitar CPFs não encontrados
valores_validos_etnia = ['Branca', 'Preta', 'Parda', 'Indígena', 'Amarela', 'Não declarada', '']

# --- FUNÇÕES AUXILIARES ---
@st.cache_data(show_spinner=False)
def gerar_modelo_qa():
    modelo_df = pd.DataFrame({
        'CPF': ['12345678900', '09876543211'],
        'Desc_Cor': ['Parda', 'Branca'],
        'Renda Familiar Per Capita SIG': ['1 SM < RFP <= 1,5 SM', 'RFP <= 0,5 SM'],
        'Desc_Forma_Ingresso_Matricula': ['Processo Seletivo - Ampla Concorrência', 'Processo Seletivo C1 PPI']
    })
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        modelo_df.to_excel(writer, index=False, sheet_name='Modelo_QA')
    return output.getvalue()


@st.cache_data(show_spinner=False)
def processar_dados(file_qa, file_etnia=None, file_renda=None, file_cota=None):
    resultados = {}

    # 1. Carregar Dados QA (Obrigatório)
    dados_qa = pd.read_excel(file_qa, dtype={'CPF': str})
    dados_qa['cpf_key'] = dados_qa['CPF'].astype(str).str.replace(r'\D', '', regex=True).str.zfill(11)

    # ---- ETNIA ----
    if file_etnia is not None:
        pnp_etnia = pd.read_excel(file_etnia, dtype={'CPF': str})
        pnp_etnia['cpf_key'] = pnp_etnia['CPF'].astype(str).str.replace(r'\D', '', regex=True).str.zfill(11)

        # [NOVIDADE]: Se o aluno ESTÁ no QA, mas a etnia lá está vazia, vira 'Não declarada'
        dados_qa['Desc_Cor_Tratada'] = dados_qa['Desc_Cor'].fillna('Não declarada')
        lookup_etnia = dados_qa.drop_duplicates(subset=['cpf_key']).set_index('cpf_key')['Desc_Cor_Tratada']

        if 'Cor/Raça' in pnp_etnia.columns:
            pnp_etnia['Cor/Raça'] = pnp_etnia['Cor/Raça'].astype(str).str.strip()
            pnp_etnia.loc[
                pnp_etnia['Cor/Raça'].str.lower().isin(['nan', 'não declarada', 'none', '']), 'Cor/Raça'] = np.nan

            # Preenche com QA. Se o CPF não existir no QA, deixa VAZIO ('')
            pnp_etnia['Cor/Raça'] = pnp_etnia['Cor/Raça'].fillna(pnp_etnia['cpf_key'].map(lookup_etnia)).fillna('')
        else:
            pnp_etnia['Cor/Raça'] = pnp_etnia['cpf_key'].map(lookup_etnia).fillna('')

        pnp_etnia.loc[~pnp_etnia['Cor/Raça'].isin(valores_validos_etnia), 'Cor/Raça'] = ''
        resultados['etnia'] = pnp_etnia.drop(columns=['cpf_key'])

    # ---- RENDA ----
    if file_renda is not None:
        pnp_renda = pd.read_excel(file_renda, dtype={'CPF': str})
        pnp_renda['cpf_key'] = pnp_renda['CPF'].astype(str).str.replace(r'\D', '', regex=True).str.zfill(11)

        # [NOVIDADE]: Mapeia a renda. Se o aluno ESTÁ no QA, mas o resultado for vazio, vira 'Não declarada'
        dados_qa['renda_formatada'] = dados_qa['Renda Familiar Per Capita SIG'].map(map_renda).fillna('Não declarada')
        lookup_renda = dados_qa.drop_duplicates(subset=['cpf_key']).set_index('cpf_key')['renda_formatada']

        if 'Faixa de Renda' in pnp_renda.columns:
            pnp_renda['Faixa de Renda'] = pnp_renda['Faixa de Renda'].astype(str).str.strip()
            pnp_renda.loc[pnp_renda['Faixa de Renda'].str.lower().isin(
                ['nan', 'não declarada', 'none', '']), 'Faixa de Renda'] = np.nan

            # Preenche com QA. Se o CPF não existir no QA, deixa VAZIO ('')
            pnp_renda['Faixa de Renda'] = pnp_renda['Faixa de Renda'].fillna(
                pnp_renda['cpf_key'].map(lookup_renda)).fillna('')
        else:
            pnp_renda['Faixa de Renda'] = pnp_renda['cpf_key'].map(lookup_renda).fillna('')

        resultados['renda'] = pnp_renda.drop(columns=['cpf_key'])

    # ---- COTAS ----
    if file_cota is not None:
        pnp_cota = pd.read_excel(file_cota, dtype={'CPF': str})
        pnp_cota['cpf_key'] = pnp_cota['CPF'].astype(str).str.replace(r'\D', '', regex=True).str.zfill(11)

        # Cotas não tem 'Não declarada', então se estiver vazio no QA, continua vazio
        dados_qa['cota_formatada'] = dados_qa['Desc_Forma_Ingresso_Matricula'].map(map_cota)
        lookup_cota = dados_qa.drop_duplicates(subset=['cpf_key']).set_index('cpf_key')['cota_formatada']

        if 'Cota' in pnp_cota.columns:
            pnp_cota['Cota'] = pnp_cota['Cota'].astype(str).str.strip()
            pnp_cota.loc[pnp_cota['Cota'].str.lower().isin(['nan', 'não declarada', 'none', '']), 'Cota'] = np.nan

            pnp_cota['Cota'] = pnp_cota['Cota'].fillna(pnp_cota['cpf_key'].map(lookup_cota)).fillna('')
        else:
            pnp_cota['Cota'] = pnp_cota['cpf_key'].map(lookup_cota).fillna('')

        resultados['cota'] = pnp_cota.drop(columns=['cpf_key'])

    return resultados

@st.cache_data(show_spinner=False)
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados_Corrigidos')
    return output.getvalue()

# --- INTERFACE DO USUÁRIO (FRONTEND) ---
st.subheader("1. Upload dos Arquivos (.xlsx)")

st.markdown("**📂 Arquivo Base (Obrigatório)**")

st.download_button(
    label="📄 Baixar Planilha Modelo 'Dados QA'",
    data=gerar_modelo_qa(),
    file_name="Modelo_Dados_QA.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    help="Baixe este arquivo para ver quais colunas o sistema espera no 'Dados QA'."
)

file_qa = st.file_uploader("Upload 'Dados QA.xlsx'", type=["xlsx"], key=f"qa_{st.session_state['uploader_key']}", on_change=limpar_resultados)

st.divider()

st.markdown("**📁 Arquivos para Atualizar (Opcionais - Escolha pelo menos um)**")
col1, col2, col3 = st.columns(3)
with col1:
    file_etnia = st.file_uploader("Carregar Arquivo cor_raca.xlsx", type=["xlsx"], key=f"etnia_{st.session_state['uploader_key']}", on_change=limpar_resultados)
with col2:
    file_renda = st.file_uploader("Carregar Arquivo renda.xlsx", type=["xlsx"], key=f"renda_{st.session_state['uploader_key']}", on_change=limpar_resultados)
with col3:
    file_cota = st.file_uploader("Carregar Arquivo cotas.xlsx", type=["xlsx"], key=f"cota_{st.session_state['uploader_key']}", on_change=limpar_resultados)

if not file_qa:
    st.warning("⚠️ O arquivo **'Dados QA.xlsx'** é obrigatório para realizar os cruzamentos. Faça o upload dele primeiro.")
elif not (file_etnia or file_renda or file_cota):
    st.info("ℹ️ Agora, faça o upload de **pelo menos um** dos arquivos complementares (Etnia, Renda ou Cotas) para processar.")
else:
    st.success("Arquivos prontos para processamento!")

    if st.button("🚀 Processar Arquivos Selecionados", use_container_width=True):
        with st.spinner("Cruzando os dados... Isso pode levar alguns segundos."):
            try:
                resultados_df = processar_dados(file_qa, file_etnia, file_renda, file_cota)

                st.session_state['resultados'] = {}
                if 'etnia' in resultados_df:
                    st.session_state['resultados']['etnia'] = to_excel(resultados_df['etnia'])
                if 'renda' in resultados_df:
                    st.session_state['resultados']['renda'] = to_excel(resultados_df['renda'])
                if 'cota' in resultados_df:
                    st.session_state['resultados']['cota'] = to_excel(resultados_df['cota'])

                st.success("Processamento finalizado com sucesso! Baixe os arquivos gerados, e finalize a aplicação.")
            except Exception as e:
                st.error(f"Ocorreu um erro durante o processamento. Certifique-se de que as planilhas estão no formato correto. Erro: {e}")

# --- ÁREA DE DOWNLOAD ---
if 'resultados' in st.session_state:
    st.subheader("2. Download dos Resultados (.xlsx)")
    st.markdown("Os dados solicitados foram processados! Baixe as planilhas geradas abaixo:")

    resultados_excel = st.session_state['resultados']

    if 'etnia' in resultados_excel:
        st.download_button(
            label="📥 Baixar Fonte_PNP_Etnia_Final.xlsx",
            data=resultados_excel['etnia'],
            file_name="Fonte_PNP_Etnia_Final.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_dl_etnia"
        )

    if 'renda' in resultados_excel:
        st.download_button(
            label="📥 Baixar Fonte_PNP_Renda_Final.xlsx",
            data=resultados_excel['renda'],
            file_name="Fonte_PNP_Renda_Final.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_dl_renda"
        )

    if 'cota' in resultados_excel:
        st.download_button(
            label="📥 Baixar Fonte_PNP_Cota_Final.xlsx",
            data=resultados_excel['cota'],
            file_name="Fonte_PNP_Cota_Final.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_dl_cota"
        )

    st.divider()

    # --- NOVO BOTÃO DE FINALIZAR COM CALLBACK E COR VERMELHA ---
    # Adicionamos type="primary" para aplicar o estilo vermelho do nosso CSS!
    st.button("🔄 Finalizar e Limpar Dados", type="primary", use_container_width=True, on_click=limpar_tudo)

st.divider()  # Linha visual para separar o conteúdo do rodapé

# --- RODAPÉ EM TEXTO DISCRETO ---
rodape_html = """
    <div style="text-align: center; color: #888888; font-size: 12px; margin-top: 30px; padding-bottom: 20px;">
        <p style="margin: 0; line-height: 1.4;">
            <b>💻Desenvolvido por Edson Ferreira - 2026</b><br>
            Coordenador de Registro Acadêmico - <i>Campus</i> São João da Barra - IFFluminense <br>
             Estudante de Análise e Desenvolvimento de Sistemas - PUCPR<br>
            📧 edson.ferreira@iff.edu.br
        </p>
    </div>
    """
st.markdown(rodape_html, unsafe_allow_html=True)
