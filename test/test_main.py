import pytest
import pandas as pd
import io
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import src.Main as app

CAMINHO_APP = "src/Main.py"
MIME_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Função auxiliar para criar arquivo Excel em memória
def criar_excel_memoria(df):
    """Gera um arquivo Excel em memória para simular uploads."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output


# Testes com Mock e lógicos
@patch('src.Main.st.session_state', {'resultados': 'dados_antigos'})
def test_limpar_resultados():
    app.limpar_resultados()
    assert 'resultados' not in app.st.session_state

@patch('src.Main.st.session_state', {'uploader_key': 1, 'resultados': 'dados_antigos'})  
def test_limpar_tudo():
    app.limpar_tudo()
    assert app.st.session_state['uploader_key'] == 2
    assert 'resultados' not in app.st.session_state

def test_gerar_modelo_qa():
    resultado = app.gerar_modelo_qa()
    assert isinstance(resultado, bytes)
    df_gerado = pd.read_excel(io.BytesIO(resultado))
    colunas_esperadas = ['CPF', 'Desc_Cor', 'Renda Familiar Per Capita SIG', 'Desc_Forma_Ingresso_Matricula']
    assert list(df_gerado.columns) == colunas_esperadas

def test_processar_dados_etnia():
    df_qa = pd.DataFrame({
        'CPF': ['123.456.789-00', '111.222.333-44'], 
        'Desc_Cor': ['Parda', None] 
    })
    df_etnia = pd.DataFrame({
        'CPF': ['12345678900', '11122233344', '99988877766'], 
        'Cor/Raça': ['', '', ''] 
    })

    file_qa = criar_excel_memoria(df_qa)
    file_etnia = criar_excel_memoria(df_etnia)

    resultados = app.processar_dados(file_qa=file_qa, file_etnia=file_etnia)
    
    assert 'etnia' in resultados
    df_res = resultados['etnia']
    assert df_res.loc[df_res['CPF'] == '12345678900', 'Cor/Raça'].values[0] == 'Parda'
    assert df_res.loc[df_res['CPF'] == '11122233344', 'Cor/Raça'].values[0] == 'Não declarada'


# Testes de Interface com AppTest
@pytest.mark.ui_tests
def test_interface_exige_arquivo_qa():
    at = AppTest.from_file(CAMINHO_APP).run()
    assert "O arquivo **'Dados QA.xlsx'** é obrigatório" in at.warning[0].value
    botoes_processar = [btn for btn in at.button if "Processar" in btn.label]
    assert len(botoes_processar) == 0

@pytest.mark.ui_tests
def test_processamento_completo_sucesso():
    # 1. Prepara dados e arquivos em memória
    df_qa = pd.DataFrame({'CPF': ['123.456.789-00'], 'Desc_Cor': ['Parda'], 'Renda Familiar Per Capita SIG': ['1,0<RFP<=1,5'], 'Desc_Forma_Ingresso_Matricula': ['Sisu LB_EP']})
    df_etnia = pd.DataFrame({'CPF': ['12345678900'], 'Cor/Raça': ['']})
    df_renda = pd.DataFrame({'CPF': ['12345678900'], 'Faixa de Renda': ['']})
    df_cota = pd.DataFrame({'CPF': ['12345678900'], 'Cota': ['']})

    file_qa = criar_excel_memoria(df_qa)
    file_etnia = criar_excel_memoria(df_etnia)
    file_renda = criar_excel_memoria(df_renda)
    file_cota = criar_excel_memoria(df_cota)

    # 2. Inicia o App
    at = AppTest.from_file(CAMINHO_APP).run()

    # 3. Faz o Upload (passando a tupla exata de 3 itens que o Streamlit exige)
    at.file_uploader("qa_1").set_value(("qa.xlsx", file_qa.getvalue(), MIME_EXCEL))
    at.file_uploader("etnia_1").set_value(("etnia.xlsx", file_etnia.getvalue(), MIME_EXCEL))
    at.file_uploader("renda_1").set_value(("renda.xlsx", file_renda.getvalue(), MIME_EXCEL))
    at.file_uploader("cota_1").set_value(("cota.xlsx", file_cota.getvalue(), MIME_EXCEL))
    
    # Roda a tela para processar o upload e liberar o botão
    at.run()

    # 4. Simula clique no botão processar
    botao_processar = next(btn for btn in at.button if "Processar" in btn.label)
    botao_processar.click().run()

    # 5. Validações finais
    assert len(at.session_state['resultados']) > 0
    assert 'etnia' in at.session_state['resultados']
    assert 'renda' in at.session_state['resultados']
    assert 'cota' in at.session_state['resultados']
    
    # Verifica se o botão de limpar apareceu
    assert any("Finalizar" in btn.label for btn in at.button)