import pandas as pd

# 1. Carregar os dados, especificando 'CPF' como string para preservar zeros à esquerda
dados_qa = pd.read_csv('Dados QA.csv', dtype={'CPF': str})
pnp_etnia = pd.read_csv('cor_raca.csv', dtype={'CPF': str})
pnp_renda = pd.read_csv('renda.csv', dtype={'CPF': str})
pnp_cota = pd.read_csv('cotas.csv', dtype={'CPF': str})

# 2. Função para limpar CPF (deixa apenas números)
clean_cpf = lambda x: ''.join(filter(str.isdigit, str(x)))
dados_qa['cpf_key'] = dados_qa['CPF'].apply(clean_cpf)
pnp_etnia['cpf_key'] = pnp_etnia['CPF'].apply(clean_cpf)
pnp_renda['cpf_key'] = pnp_renda['CPF'].apply(clean_cpf)
pnp_cota['cpf_key'] = pnp_cota['CPF'].apply(clean_cpf)

# 3. Dicionário de Mapeamento de Renda
map_renda = {
    '1 SM < RFP <= 1,5 SM': '1,0<RFP<=1,5',
    '0,5 SM < RFP <= 1 SM': '0,5<RFP<=1,0',
    'RFP <= 0,5 SM': '0<RFP<=0,5',
    '1,5 SM < RFP <= 2,5 SM': '1,5<RFP<=2,5',
    'RFP > 3 SM': 'RFP>3,5',
    '2,5 SM < RFP <= 3 SM': '2,5<RFP<=3,5'
}

# 4. Dicionário de Mapeamento de Cotas
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

# 5. Cruzamento de Dados (Join)
# Atualiza Etnia, mantendo valores existentes se não forem NaN
lookup_etnia = dados_qa.drop_duplicates(subset=['cpf_key']).set_index('cpf_key')['Desc_Cor']
pnp_etnia['Cor/Raça'] = pnp_etnia['Cor/Raça'].fillna(pnp_etnia['cpf_key'].map(lookup_etnia).fillna('Não Declarada'))

# Atualiza Renda, mantendo valores existentes se não forem NaN
dados_qa['renda_formatada'] = dados_qa['Renda Familiar Per Capita SIG'].map(map_renda)
lookup_renda = dados_qa.drop_duplicates(subset=['cpf_key']).set_index('cpf_key')['renda_formatada']
pnp_renda['Faixa de Renda'] = pnp_renda['Faixa de Renda'].fillna(pnp_renda['cpf_key'].map(lookup_renda).fillna('Não declarada'))

# Atualiza Cota, mantendo valores existentes se não forem NaN
dados_qa['cota_formatada'] = dados_qa['Desc_Forma_Ingresso_Matricula'].map(map_cota)
lookup_cota = dados_qa.drop_duplicates(subset=['cpf_key']).set_index('cpf_key')['cota_formatada']
pnp_cota['Cota'] = pnp_cota['cpf_key'].map(lookup_cota).fillna('Não declarada')

# 6. Salvar Resultados
pnp_etnia.drop(columns=['cpf_key']).to_excel('Fonte_PNP_Etnia_Final.xlsx', index=False)
pnp_renda.drop(columns=['cpf_key']).to_excel('Fonte_PNP_Renda_Final.xlsx', index=False)
pnp_cota.drop(columns=['cpf_key']).to_excel('Fonte_PNP_Cota_Final.xlsx', index=False)