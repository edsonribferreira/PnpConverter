import src.Main as app
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import pandas as pd
import io

@patch('app.st.session_state', {'resultados': 'dados_antigos'})
def test_limpar_resultados():
    app.limpar_resultados()
    assert 'resultados' not in app.st.session_state

@patch('app.st.session_state', {'uploader_key': 1, 'resultados': 'dados_antigos'})  
def test_limpar_tudo():
    app.limpar_tudo()
    assert app.st.session_state['uploader_key'] == 2
    assert 'resultados' not in app.st.session_state



def testar_gerar_modelo_qa():
    resultado = app.gerar_modelo_qa()
    assert isinstance(resultado, bytes)
    
    df_resultado = pd.read_excel(io.BytesIO(resultado))
    colunas_esperadas = [
        'CPF', 
        'Desc_Cor', 
        'Renda Familiar Per Capita SIG', 
        'Desc_Forma_Ingresso_Matricula'
    ]
    assert list(df_resultado.columns) == colunas_esperadas

    assert df_resultado.shape == (2, 4)
    
    
    # --- FUNÇÃO AUXILIAR ---
def criar_excel_memoria(df):
    """Converte um DataFrame para um arquivo Excel em memória."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output

# --- TESTE ---
def test_processar_dados_etnia():
    # 1. Preparação (Mock dos Dados)
    df_qa = pd.DataFrame({
        'CPF': ['123.456.789-00', '111.222.333-44'], # Com pontuação
        'Desc_Cor': ['Parda', None] # Um preenchido, um vazio
    })
    
    df_etnia = pd.DataFrame({
        'CPF': ['12345678900', '11122233344', '99988877766'], # Sem pontuação
        'Cor/Raça': ['', '', ''] 
    })

    file_qa = criar_excel_memoria(df_qa)
    file_etnia = criar_excel_memoria(df_etnia)

    # 2. Execução
    resultados = app.processar_dados(file_qa=file_qa, file_etnia=file_etnia)

    # 3. Validação
    assert 'etnia' in resultados
    df_res = resultados['etnia'] 
    
    # Verifica CPF 1 (Pegou do QA corretamente)
    assert df_res.loc[df_res['CPF'] == '12345678900', 'Cor/Raça'].values[0] == 'Parda'
    
    # Verifica CPF 2 (Estava vazio no QA, virou 'Não declarada')
    assert df_res.loc[df_res['CPF'] == '11122233344', 'Cor/Raça'].values[0] == 'Não declarada'
    
    # Verifica CPF 3 (Não existe no QA, deve continuar vazio)
    assert df_res.loc[df_res['CPF'] == '99988877766', 'Cor/Raça'].values[0] == ''





CAMINHO_APP = "src/Main.py" 

def test_interface_exige_arquivo_qa():
    """Testa se o aviso aparece quando nenhum arquivo é enviado."""
    at = AppTest.from_file(CAMINHO_APP).run()
    
    # Valida se a mensagem de warning aparece pedindo o arquivo QA
    assert "O arquivo **'Dados QA.xlsx'** é obrigatório" in at.warning[0].value
    
    # Valida se o botão de processar ainda NÃO está na tela
    botoes_processar = [btn for btn in at.button if btn.label == "🚀 Processar Arquivos Selecionados"]
    assert len(botoes_processar) == 0


def test_interface_exibe_botao_download_modelo():
    """Testa se o botão de baixar a planilha modelo está presente."""
    at = AppTest.from_file(CAMINHO_APP).run()
    
    # Valida a existência do botão de download do modelo
    assert len(at.download_button) > 0
    assert at.download_button[0].label == "📄 Baixar Planilha Modelo 'Dados QA'"


    # --- TESTE DE FLOW COMPLETO (UPLOAD -> PROCESSAR -> DOWNLOAD) ---
def test_processamento_completo_sucesso():
    # 1. Prepara os dados de teste
    df_qa = pd.DataFrame({
        'CPF': ['123.456.789-00'],
        'Desc_Cor': ['Parda'],
        'Renda Familiar Per Capita SIG': ['1,0<RFP<=1,5'],
        'Desc_Forma_Ingresso_Matricula': ['Sisu LB_EP']
    })
    df_etnia = pd.DataFrame({'CPF': ['12345678900'], 'Cor/Raça': ['']})
    df_renda = pd.DataFrame({'CPF': ['12345678900'], 'Faixa de Renda': ['']})
    df_cota = pd.DataFrame({'CPF': ['12345678900'], 'Cota': ['']})

    file_qa = criar_excel_memoria(df_qa)
    file_etnia = criar_excel_memoria(df_etnia)
    file_renda = criar_excel_memoria(df_renda)
    file_cota = criar_excel_memoria(df_cota)

    # 2. Inicia o App e simula os Uploads
    at = AppTest.from_file(CAMINHO_APP).run()
    at.file_uploader("Upload 'Dados QA.xlsx'").set_value(file_qa)
    at.file_uploader("Carregar Arquivo cor_raca.xlsx").set_value(file_etnia)
    at.file_uploader("Carregar Arquivo renda.xlsx").set_value(file_renda)
    at.file_uploader("Carregar Arquivo cotas.xlsx").set_value(file_cota)

    # 3. Simula o clique no botão "Processar"
    at.button("🚀 Processar Arquivos Selecionados").click()

    # 4. Valida se os arquivos foram gerados (Se chegou até aqui, processou sem crash)
    assert len(at.session_state['resultados']) > 0
    assert 'etnia' in at.session_state['resultados']
    assert 'renda' in at.session_state['resultados']
    assert 'cota' in at.session_state['resultados']

    # 5. Valida o botão "Finalizar e Sair" (que só aparece após processar)
    assert len(at.button) > 0
    botoes_finais = [btn for btn in at.button if btn.label == "Finalizar e Sair"]
    assert len(botoes_finais) > 0

#  --- ÁREA DE DOWNLOAD ---
def test_exibicao_botoes_download():
    """Injeta resultados falsos na sessão e verifica se os botões corretos aparecem."""
    at = AppTest.from_file(CAMINHO_APP)
    
    # 1. Preparação: Injeta apenas Etnia e Renda (Cota fica de fora)
    at.session_state['resultados'] = {'etnia': b'dados', 'renda': b'dados'}
    at.run()
    
    # 2. Validação: Extrai os textos dos botões de download gerados
    labels_botoes = [btn.label for btn in at.download_button]
    
    assert "📥 Baixar Fonte_PNP_Etnia_Final.xlsx" in labels_botoes
    assert "📥 Baixar Fonte_PNP_Renda_Final.xlsx" in labels_botoes
    assert "📥 Baixar Fonte_PNP_Cota_Final.xlsx" not in labels_botoes # Confirma que não apareceu


def test_clique_botao_finalizar():
    """Testa se clicar no botão 'Finalizar' dispara o callback corretamente."""
    at = AppTest.from_file(CAMINHO_APP)
    
    # 1. Preparação
    at.session_state['resultados'] = {'etnia': b'dados'}
    at.session_state['uploader_key'] = 1
    at.run()
    
    # 2. Execução: Encontra o botão de finalizar e clica nele
    botao_finalizar = next(btn for btn in at.button if "Finalizar e Limpar Dados" in btn.label)
    botao_finalizar.click().run()
    
    # 3. Validação: Confirma que o callback (limpar_tudo) fez o trabalho dele
    assert 'resultados' not in at.session_state
    assert at.session_state['uploader_key'] == 2