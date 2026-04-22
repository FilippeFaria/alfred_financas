"""
Página de Patrimônio.
Exibe investimentos e patrimônio total.
"""
import streamlit as st

from src.config import CONTAS_INVEST
from src.analytics.calculations import calcular_saldo
from src.analytics.charts import aplicacoes_resgates


def render(df):
    """Renderiza a página de patrimônio."""
    st.markdown("## 📊 Patrimônio")
    
    saldo_s = calcular_saldo(df)
    
    col1, col2, col3 = st.columns(3)
    with col2:
        st.metric('Patrimônio Total', saldo_s.reindex(CONTAS_INVEST).fillna(0).sum())
        st.write(saldo_s.reindex(CONTAS_INVEST).fillna(0))

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