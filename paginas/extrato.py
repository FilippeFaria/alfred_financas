"""
Página de Extrato.
Exibe transações filtradas por período e conta.
"""
import streamlit as st
from datetime import datetime

from src.analytics.calculations import adicionar_anomes
from src.analytics.charts import extrato
from src.services.data_handler import excluir_registro
from src.services.google_sheets import get_sheet


def render(df, path):
    """Renderiza a página de extrato."""
    st.markdown("## 📋 Extrato")
    
    df = adicionar_anomes(df)
    
    now = datetime.now()
    if now.month >= 10:
        anome = f'{now.year}{now.month}'
    else:
        anome = f'{now.year}0{now.month}'
    
    # Campo para excluir registro por ID
    st.markdown("### Excluir Registro")
    id_to_delete = st.number_input("Digite o ID do registro a excluir:", min_value=0, step=1)
    if st.button("Excluir Registro"):
        if id_to_delete > 0:
            sheet = get_sheet(path)
            df = excluir_registro(sheet, df, id_to_delete)
        else:
            st.error("Por favor, insira um ID válido.")
    
    extrato(df, anome)
    
    return df