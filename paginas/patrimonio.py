"""
Página de Patrimônio.
Exibe investimentos e patrimônio total.
"""
import streamlit as st

from src.api import ApiClientError, obter_saldo
from src.config import CONTAS_INVEST
from src.analytics.charts import aplicacoes_resgates


def render(df):
    """Renderiza a página de patrimônio."""
    st.markdown("## 📊 Patrimônio")
    
    try:
        saldo_payload = obter_saldo()
        saldo_s = {item["conta"]: float(item["saldo"]) for item in saldo_payload}
    except ApiClientError:
        saldo_s = {}
    
    col1, col2, col3 = st.columns(3)
    with col2:
        patrimonio_total = sum(saldo_s.get(conta, 0.0) for conta in CONTAS_INVEST)
        st.metric('Patrimônio Total', patrimonio_total)
        st.write({conta: saldo_s.get(conta, 0.0) for conta in CONTAS_INVEST})

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric('Ion', saldo_s.get('Ion', 0))
    with col2:
        st.metric('Nuinvest', saldo_s.get('Nuinvest', 0))
    with col3:
        st.metric('99Pay', saldo_s.get('99Pay', 0))
    with col4:
        st.metric('C6Invest', saldo_s.get('C6Invest', 0))
    with col5:
        st.metric('InterInvest', saldo_s.get('InterInvest', 0))

    aplicacoes_resgates(df, CONTAS_INVEST)

    st.markdown('### Extrato de Investimentos')
    df_invest = df[df['Tipo'] == 'Investimento']
    st.dataframe(df_invest, hide_index=True)
