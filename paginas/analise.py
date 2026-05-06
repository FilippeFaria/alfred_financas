"""
Página de Análise.
Gráficos e métricas de despesas, receitas e tendências.
"""
import streamlit as st
from datetime import datetime

from src.api import ApiClientError, obter_resumo_analise, transacoes_para_dataframe
from src.analytics.calculations import adicionar_anomes
from src.config import CONTAS_INVEST
from src.analytics.charts import (
    receitas_despesas,
    tendencia_mes,
    categorias_tempo,
    evolucao_categoria,
    render_categorias_despesas,
    monthly_spending_by_category_pie,
)


def render(df, path: str = '.'):
    """Renderiza a página de análise."""
    st.markdown("## Análise Financeira")

    col1, col2 = st.columns(2)
    with col1:
        desconsiderar = st.checkbox('Desconsiderar grandes transacoes', value=True)
        va = st.checkbox('Desconsiderar VA', value=False)
        vr = st.checkbox('Desconsiderar VR', value=False)
    with col2:
        bianca = st.checkbox('Recorte Bianca', value=False)
        filippe = st.checkbox('Recorte Filippe', value=False)

    now = datetime.now()
    anome = int(f"{now.year}{now.month:02d}")

    day_to_date = st.checkbox('Comparar aos dias do mês')
    try:
        resumo = obter_resumo_analise(
            desconsiderar=desconsiderar,
            va=va,
            vr=vr,
            bianca=bianca,
            filippe=filippe,
            day_to_date=day_to_date,
            anome_referencia=anome,
        )
    except ApiClientError as exc:
        st.error(f"Erro ao carregar resumo analitico via API: {exc}")
        return

    df_temp = transacoes_para_dataframe({"items": resumo.get("items", [])})
    if not df_temp.empty and "anomes" not in df_temp.columns:
        df_temp = adicionar_anomes(df_temp)
    metricas = resumo.get("metricas", {})

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric(
            f"Gasto mês anterior ({metricas.get('label_prev', '')})",
            value=metricas.get("gasto_anterior", 0.0),
            delta=(
                f"{round(metricas.get('delta_anterior', 0.0) * 100, 2)}%"
                if metricas.get("delta_anterior") is not None
                else None
            ),
            delta_color="inverse",
        )
    with col_m2:
        st.metric(
            f"Gasto mês atual ({metricas.get('label_curr', '')})",
            value=metricas.get("gasto_atual", 0.0),
            delta=(
                f"{round(metricas.get('delta_atual', 0.0) * 100, 2)}%"
                if metricas.get("delta_atual") is not None
                else None
            ),
            delta_color="inverse",
        )
    with col_m3:
        st.metric(
            f"Média últimos 3 meses ({metricas.get('label_3m', '')})",
            value=metricas.get("gasto_3m_media", 0.0),
            delta=(
                f"{round(metricas.get('delta_3m', 0.0) * 100, 2)}%"
                if metricas.get("delta_3m") is not None
                else None
            ),
            delta_color="inverse",
        )

    st.markdown("---")
    st.markdown("# Análises")

    anomes_disponiveis = resumo.get("anomes_disponiveis", [])
    if not anomes_disponiveis:
        st.info("Sem dados para análise no momento.")
        return

    data_escolhida = st.select_slider(
        'Escolha o anomes',
        options=anomes_disponiveis,
        value=int(resumo.get("anome_referencia", anome)),
    )
    if data_escolhida:
        anome = int(data_escolhida)

    render_categorias_despesas(df_temp, anome, path)

    col1, col2 = st.columns(2)
    with col2:
        df_tendencia = evolucao_categoria(df_temp, int(anome), now)
        monthly_spending_by_category_pie(df_temp, anome)
        categorias_tempo(df_temp)

    with col1:
        tendencia_mes(df_tendencia, int(anome))
        receitas_despesas(df_temp, CONTAS_INVEST, anome=int(anome))
