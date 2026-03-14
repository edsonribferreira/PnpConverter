import pandas as pd
import streamlit as st
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Processador de Dados PNP", page_icon="📊", layout="centered")

st.title("📊 Processador de Dados - PNP")
st.markdown("""
Faça o upload do arquivo base (**Dados QA**) e escolha quais arquivos deseja atualizar (**Etnia, Renda e/ou Cotas**). O sistema cruzará os dados usando o **CPF** e gerará os arquivos corrigidos.
""")

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

# Lista estrita de categorias de Etnia
valores_validos_etnia = [
    'Branca', 'Preta', 'Parda', 'Indígena', 'Amarela', 'Não declarada'
]


# --- FUNÇÕES AUXILIARES ---
@st.cache_data
def processar_dados(file_qa, file_etnia=None, file_renda=None, file_cota=None):
    # Dicionário para guardar apenas os resultados gerados
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


# Função para converter DataFrame para Excel em memória
@st.cache_data
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados_Corrigidos')
    return output.getvalue()


# --- INTERFACE DO USUÁRIO (FRONTEND) ---
st.subheader("1. Upload dos Arquivos (.xlsx)")

# Arquivo obrigatório em destaque
st.markdown("**📂 Arquivo Base (Obrigatório)**")
file_qa = st.file_uploader("Upload 'Dados QA.xlsx'", type=["xlsx"], key="qa")

# Arquivos opcionais lado a lado
st.markdown("**📁 Arquivos para Atualizar (Opcionais - Escolha pelo menos um)**")
col1, col2, col3 = st.columns(3)
with col1:
    file_etnia = st.file_uploader("Upload 'cor_raca.xlsx'", type=["xlsx"])
with col2:
    file_renda = st.file_uploader("Upload 'renda.xlsx'", type=["xlsx"])
with col3:
    file_cota = st.file_uploader("Upload 'cotas.xlsx'", type=["xlsx"])

# Lógica de liberação do botão
if not file_qa:
    st.warning(
        "⚠️ O arquivo **'Dados QA.xlsx'** é obrigatório para realizar os cruzamentos. Faça o upload dele primeiro.")
elif not (file_etnia or file_renda or file_cota):
    st.info(
        "ℹ️ Agora, faça o upload de **pelo menos um** dos arquivos complementares (Etnia, Renda ou Cotas) para processar.")
else:
    st.success("Arquivos prontos para processamento!")

    if st.button("🚀 Processar Arquivos Selecionados", use_container_width=True):
        with st.spinner("Cruzando os dados... Isso pode levar alguns segundos."):
            try:
                # Processa dinamicamente só os arquivos enviados
                resultados = processar_dados(file_qa, file_etnia, file_renda, file_cota)

                st.subheader("2. Download dos Resultados (.xlsx)")
                st.markdown("Os dados solicitados foram processados! Baixe as planilhas geradas abaixo:")

                # Gera botões de download dinamicamente conforme o que foi gerado
                if 'etnia' in resultados:
                    st.download_button(
                        label="📥 Baixar Fonte_PNP_Etnia_Final.xlsx",
                        data=to_excel(resultados['etnia']),
                        file_name="Fonte_PNP_Etnia_Final.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                if 'renda' in resultados:
                    st.download_button(
                        label="📥 Baixar Fonte_PNP_Renda_Final.xlsx",
                        data=to_excel(resultados['renda']),
                        file_name="Fonte_PNP_Renda_Final.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                if 'cota' in resultados:
                    st.download_button(
                        label="📥 Baixar Fonte_PNP_Cota_Final.xlsx",
                        data=to_excel(resultados['cota']),
                        file_name="Fonte_PNP_Cota_Final.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                st.balloons()  # Efeito visual de sucesso

            except Exception as e:
                st.error(
                    f"Ocorreu um erro durante o processamento. Certifique-se de que as planilhas estão no formato correto. Erro: {e}")