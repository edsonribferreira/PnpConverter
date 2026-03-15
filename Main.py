import pandas as pd
import streamlit as st
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Processador de Dados PNP", page_icon="📊", layout="centered")

st.title("📊 Processador de Dados - PNP")
st.markdown("""
Faça o upload do arquivo base (**Dados QA**) e escolha quais arquivos deseja atualizar (**Etnia, Renda e/ou Cotas**). O sistema cruzará os dados usando o **CPF** e gerará os arquivos corrigidos.
""")


# --- CONTROLE DE ESTADO (MEMÓRIA) ---
def limpar_resultados():
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

valores_validos_etnia = [
    'Branca', 'Preta', 'Parda', 'Indígena', 'Amarela', 'Não declarada'
]


# --- FUNÇÕES AUXILIARES ---
@st.cache_data(show_spinner=False)
def gerar_modelo_qa():
    """Gera uma planilha de modelo do Dados QA para o usuário baixar."""
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
    dados_qa['cpf_key'] = dados_qa['CPF'].astype(str).str.replace(r'\D', '', regex=True)

    # ---- ETNIA ----
    if file_etnia is not None:
        pnp_etnia = pd.read_excel(file_etnia, dtype={'CPF': str})
        pnp_etnia['cpf_key'] = pnp_etnia['CPF'].astype(str).str.replace(r'\D', '', regex=True)

        lookup_etnia = dados_qa.drop_duplicates(subset=['cpf_key']).set_index('cpf_key')['Desc_Cor']
        pnp_etnia['Cor/Raça'] = pnp_etnia['Cor/Raça'].fillna(pnp_etnia['cpf_key'].map(lookup_etnia)).fillna(
            'Não declarada')
        pnp_etnia['Cor/Raça'] = pnp_etnia['Cor/Raça'].astype(str).str.strip()
        pnp_etnia.loc[~pnp_etnia['Cor/Raça'].isin(valores_validos_etnia), 'Cor/Raça'] = 'Não declarada'

        resultados['etnia'] = pnp_etnia.drop(columns=['cpf_key'])

    # ---- RENDA ----
    if file_renda is not None:
        pnp_renda = pd.read_excel(file_renda, dtype={'CPF': str})
        pnp_renda['cpf_key'] = pnp_renda['CPF'].astype(str).str.replace(r'\D', '', regex=True)

        dados_qa['renda_formatada'] = dados_qa['Renda Familiar Per Capita SIG'].map(map_renda)
        lookup_renda = dados_qa.drop_duplicates(subset=['cpf_key']).set_index('cpf_key')['renda_formatada']
        pnp_renda['Faixa de Renda'] = pnp_renda['Faixa de Renda'].fillna(pnp_renda['cpf_key'].map(lookup_renda)).fillna(
            'Não declarada')

        resultados['renda'] = pnp_renda.drop(columns=['cpf_key'])

    # ---- COTAS ----
    if file_cota is not None:
        pnp_cota = pd.read_excel(file_cota, dtype={'CPF': str})
        pnp_cota['cpf_key'] = pnp_cota['CPF'].astype(str).str.replace(r'\D', '', regex=True)

        dados_qa['cota_formatada'] = dados_qa['Desc_Forma_Ingresso_Matricula'].map(map_cota)
        lookup_cota = dados_qa.drop_duplicates(subset=['cpf_key']).set_index('cpf_key')['cota_formatada']

        if 'Cota' in pnp_cota.columns:
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

# Botão de modelo e Upload do QA

st.subheader("1. Download do Modelo para inserir os dados do Q-Acadêmico")
# Exibe o botão de download do modelo em uma linha amigável
st.download_button(
    label="📄 Baixar Planilha Modelo 'Dados QA'",
    data=gerar_modelo_qa(),
    file_name="Modelo_Dados_QA.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    help="Baixe este arquivo para ver quais colunas o sistema espera no 'Dados QA'."
)

st.subheader("2. Upload dos Arquivos (.xlsx)")
st.markdown("##### **📂 Arquivo Dados QA (Obrigatório)**")
file_qa = st.file_uploader("Inserir Planilha 'Dados QA.xlsx'", type=["xlsx"], key="qa", on_change=limpar_resultados)

st.divider()

st.markdown("##### **📁 Arquivos para Atualizar (Opcionais - Escolha pelo menos um)**")
st.warning(
        "⚠️ Utilize as planilhas extraídas da PNP")

col1, col2, col3 = st.columns(3)
with col1:
    file_etnia = st.file_uploader("Inserir Planilha 'cor_raca.xlsx'", type=["xlsx"], key="etnia_file",
                                  on_change=limpar_resultados)
with col2:
    file_renda = st.file_uploader("Inserir Planilha 'renda.xlsx'", type=["xlsx"], key="renda_file", on_change=limpar_resultados)
with col3:
    file_cota = st.file_uploader("Inserir Planilha 'cotas.xlsx'", type=["xlsx"], key="cota_file", on_change=limpar_resultados)

# Lógica de liberação do botão
if not file_qa:
    st.warning(
        "⚠️ O arquivo **'Dados QA.xlsx'** é obrigatório para realizar os cruzamentos. Faça o upload dele primeiro.")
elif not (file_etnia or file_renda or file_cota):
    st.info(
        "ℹ️ Agora, faça o upload de **pelo menos um** dos arquivos complementares (Etnia, Renda ou Cotas) para processar.")
else:
    st.success("Arquivos prontos para processamento!")

    # BOTÃO DE PROCESSAR
    if st.button("🚀 Processar Arquivos Selecionados", use_container_width=True):
        with st.spinner("Cruzando os dados... Isso pode levar alguns segundos."):
            try:
                resultados_df = processar_dados(file_qa, file_etnia, file_renda, file_cota)

                # Salva os arquivos prontos na "Memória" (session_state)
                st.session_state['resultados'] = {}
                if 'etnia' in resultados_df:
                    st.session_state['resultados']['etnia'] = to_excel(resultados_df['etnia'])
                if 'renda' in resultados_df:
                    st.session_state['resultados']['renda'] = to_excel(resultados_df['renda'])
                if 'cota' in resultados_df:
                    st.session_state['resultados']['cota'] = to_excel(resultados_df['cota'])

                st.balloons()  # Efeito visual de sucesso
            except Exception as e:
                st.error(
                    f"Ocorreu um erro durante o processamento. Certifique-se de que as planilhas estão no formato correto. Erro: {e}")

# --- ÁREA DE DOWNLOAD ---
if 'resultados' in st.session_state:
    st.subheader("3. Download dos Resultados (.xlsx)")
    st.markdown("Os dados solicitados foram processados! Baixe as planilhas geradas abaixo:")

    resultados_excel = st.session_state['resultados']

    # Gera botões de download dinamicamente conforme o que está na memória
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
print("")
print("")
print("")
st.markdown("💻 *Edson Ferreira - 2026*" )