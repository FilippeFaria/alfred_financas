"""
Página de Extrato.
Exibe transações filtradas por período e conta.
"""
import streamlit as st
from datetime import datetime

from src.analytics.calculations import adicionar_anomes
from src.analytics.charts import extrato


def render(df):
    """Renderiza a página de extrato."""
    st.markdown("## 📋 Extrato")
    
    df = adicionar_anomes(df)
    
    now = datetime.now()
    if now.month >= 10:
        anome = f'{now.year}{now.month}'
    else:
        anome = f'{now.year}0{now.month}'
    
    extrato(df, anome)