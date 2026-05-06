"""
Pagina de Extrato.
Exibe transacoes filtradas por periodo e conta.
"""

from datetime import datetime

import streamlit as st

from src.api import ApiClientError, carregar_dataframe_transacoes, excluir_transacao
from src.analytics.calculations import adicionar_anomes
from src.analytics.charts import extrato


def render(df, path):
    """Renderiza a pagina de extrato."""
    st.markdown("## Extrato")

    df = adicionar_anomes(df)

    now = datetime.now()
    if now.month >= 10:
        anome = f"{now.year}{now.month}"
    else:
        anome = f"{now.year}0{now.month}"

    st.markdown("### Excluir Registro")
    col1, col2 = st.columns([3, 1])
    with col1:
        id_to_delete = st.number_input(
            "Digite o ID do registro a excluir:",
            min_value=0,
            step=1,
            key="id_delete_input",
        )
    with col2:
        if st.button("Excluir Registro", key="delete_button"):
            if id_to_delete > 0:
                try:
                    resultado = excluir_transacao(int(id_to_delete))
                    if int(resultado.get("removidos", 0)) > 0:
                        st.success(resultado.get("mensagem", "Registro excluido com sucesso."))
                    else:
                        st.warning(resultado.get("mensagem", "Nenhum registro removido."))

                    st.session_state.df = carregar_dataframe_transacoes()
                    st.session_state.last_update = datetime.now().timestamp()
                    st.rerun()
                except ApiClientError as exc:
                    st.error(f"Erro ao excluir registro via API: {exc}")
            else:
                st.error("Por favor, insira um ID valido.")

    extrato(df, anome)
    return df

