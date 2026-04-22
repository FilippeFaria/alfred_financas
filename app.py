"""
Alfred Finanças - Aplicação principal Streamlit.
Ponto de entrada da aplicação.
"""
import streamlit as st
from datetime import datetime

from src.config import CONTAS, CONTAS_INVEST
from src.services.data_handler import carregar_dados
from src.services.google_sheets import get_sheet
from src.analytics.calculations import adicionar_anomes, calcular_saldo

# Configuração da página
st.set_page_config(layout="wide")

# Caminho para credentials
PATH = '.'

# Inicializar session state
if "last_update" not in st.session_state:
    st.session_state.last_update = None


def main():
    # Botão de atualização
    atualizar = st.button('Atualizar dados')
    if atualizar:
        st.session_state.last_update = datetime.now().timestamp()
        st.cache_data.clear()
    
    # Carregar dados
    df = carregar_dados(PATH, trigger=st.session_state.last_update)
    
    # Obter última data e conta para uso nos formulários
    last_date = df['Data'].iloc[-1]
    last_account = df['Conta'].iloc[-1]
    
    # Calcular saldo
    saldo_s = calcular_saldo(df)
    
    # Criar abas
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Transação", "Análise", "Alfred", "Patrimônio", "Extrato"
    ])
    
    with tab1:
        from paginas.transacao import render as render_transacao
        render_transacao(df, PATH)
    
    with tab2:
        from paginas.analise import render as render_analise
        render_analise(df, PATH)
    
    with tab3:
        from paginas.alfred import render as render_alfred
        render_alfred()
    
    with tab4:
        from paginas.patrimonio import render as render_patrimonio
        render_patrimonio(df)
    
    with tab5:
        from paginas.extrato import render as render_extrato
        df = render_extrato(df, PATH)


if __name__ == "__main__":
    main()
