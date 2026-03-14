import pandas as pd
import streamlit as st


# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Processador de Dados PNP", page_icon="📊", layout="centered")

st.title("📊 Processador de Dados - Etnia, Renda e Cotas")
st.markdown("""
Faça o upload dos arquivos **Excel (.xlsx)** originais abaixo. O sistema fará o cruzamento dos dados usando o **CPF** e gerará os arquivos **.csv** finais e corrigidos para download.
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
        pnp_cota['Cota'] = pnp_cota['Cota'].fillna(pnp_cota['cpf_key'].map(lookup_cota)).fillna('Não declarada')
    else:
        pnp_cota['Cota'] = pnp_cota['cpf_key'].map(lookup_cota).fillna('Não declarada')

    # Remover a coluna chave temporária
    pnp_etnia = pnp_etnia.drop(columns=['cpf_key'])
    pnp_renda = pnp_renda.drop(columns=['cpf_key'])
    pnp_cota = pnp_cota.drop(columns=['cpf_key'])

    return pnp_etnia, pnp_renda, pnp_cota


# Função para converter DataFrame para CSV formatado para o Brasil
@st.cache_data
def to_csv(df):
    # sep=';' e utf-8-sig garantem que o Excel abra o CSV com acentos e colunas corretas
    return df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')


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

    if st.button("🚀 Processar e Gerar CSVs", use_container_width=True):
        with st.spinner("Lendo arquivos Excel e cruzando dados... Isso pode levar alguns segundos."):

            try:
                # Chama a função de processamento
                df_etnia, df_renda, df_cota = processar_dados(file_qa, file_etnia, file_renda, file_cota)

                # Gera os arquivos CSV em memória
                csv_etnia = to_csv(df_etnia)
                csv_renda = to_csv(df_renda)
                csv_cota = to_csv(df_cota)

                st.subheader("2. Download dos Resultados (.csv)")
                st.markdown("Os dados foram processados! Baixe os arquivos CSV gerados abaixo:")

                # Botões de Download
                st.download_button(
                    label="📥 Baixar Fonte_PNP_Etnia_Final.csv",
                    data=csv_etnia,
                    file_name="Fonte_PNP_Etnia_Final.csv",
                    mime="text/csv"
                )

                st.download_button(
                    label="📥 Baixar Fonte_PNP_Renda_Final.csv",
                    data=csv_renda,
                    file_name="Fonte_PNP_Renda_Final.csv",
                    mime="text/csv"
                )

                st.download_button(
                    label="📥 Baixar Fonte_PNP_Cota_Final.csv",
                    data=csv_cota,
                    file_name="Fonte_PNP_Cota_Final.csv",
                    mime="text/csv"
                )

                st.balloons()  # Efeito visual de sucesso

            except Exception as e:
                st.error(
                    f"Ocorreu um erro durante o processamento. Certifique-se de que os arquivos estão no formato correto. Erro: {e}")
else:
    st.info("Por favor, faça o upload dos 4 arquivos Excel (.xlsx) para habilitar o processamento.")