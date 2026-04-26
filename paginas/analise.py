"""
Página de Análise.
Gráficos e métricas de despesas, receitas e tendências.
"""
import streamlit as st
from datetime import datetime

from src.config import CONTAS_INVEST
from src.services.data_handler import aplicar_filtros
from src.analytics.calculations import adicionar_anomes, exibir_despesa_total
from src.analytics.charts import (
    receitas_despesas,
    tendencia_mes,
    categorias_tempo,
    evolucao_categoria,
    render_categorias_despesas,
    monthly_spending_by_category_pie,
    tendencia_saldo,
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

    df_temp = aplicar_filtros(df, desconsiderar, va, vr, bianca, filippe)

    now = datetime.now()
    if now.month >= 10:
        anome = f'{now.year}{now.month}'
    else:
        anome = f'{now.year}0{now.month}'

    day_to_date = st.checkbox('Comparar aos dias do mês')
    if day_to_date:
        df_temp = adicionar_anomes(df_temp)
        data_max = df_temp[(df_temp['anomes'] == anome) & (df_temp['Parcela'].isna())].Data.dt.day.max()
        df_temp = df_temp[df_temp.Data.dt.day <= data_max]

    df_temp = adicionar_anomes(df_temp)

    df_despesa = df_temp[(df_temp['desconsiderar'] == False) & (df_temp['Tipo'] == 'Despesa')]
    exibir_despesa_total(df_despesa, int(anome))

    st.markdown("---")
    st.markdown("# Análises")

    anomes_disponiveis = sorted(df_temp['anomes'].unique(), key=lambda x: int(x))
    data_escolhida = st.select_slider('Escolha o anomes', options=anomes_disponiveis, value=anome)
    if data_escolhida:
        anome = data_escolhida

    render_categorias_despesas(df_temp, anome, path)

    col1, col2 = st.columns(2)
    with col2:
        df_tendencia = evolucao_categoria(df_temp, int(anome), now)
        monthly_spending_by_category_pie(df_temp, anome)
        categorias_tempo(df_temp)

    with col1:
        tendencia_mes(df_tendencia, int(anome))
        receitas_despesas(df_temp, CONTAS_INVEST, anome=int(anome))

    # with col2:
    #     tendencia_saldo(df_temp, 'Itaú CC', anome)
