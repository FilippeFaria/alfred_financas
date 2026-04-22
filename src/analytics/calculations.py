"""
Funções de cálculos para análise financeira.
Contém funções de agregação, forecast e métricas.
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime
from typing import Optional


# Color map para categorias
COLOR_MAP = {
    "Supermercado": "#004c9a",
    "Restaurante": "#e63946",
    "Viagem": "#47a847",
    "Transporte": "#ff9000",
    "Assinaturas": "#9c26b2",
    "Cosméticos": "#ff69b4",
    "Lazer": "#ffd400",
    "Compras": "#00b0c3",
    "Educação": "#d82d7f",
    "Multas": "#c21656",
    "Casa": "#795447",
    "Serviços": "#a0a0a0",
    "Saúde": "#008877",
    "Presentes": "#8bcd48",
    "Outros": "#c0c0c0",
    "Onix": "#000080",
    "Salário": "#04d204",
    "Cobrança": "#800000",
}


def tratar_df(df: pd.DataFrame) -> pd.DataFrame:
    """Preprocessa o DataFrame adicionando coluna anomes."""
    df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y')
    df['anomes'] = [
        f"{e.year}{e.month:02d}" for e in df['Data']
    ]
    return df


def calcular_saldo(df: pd.DataFrame) -> pd.Series:
    """
    Calcula o saldo por conta até a data atual.
    
    Args:
        df: DataFrame com dados do fluxo de caixa
    
    Returns:
        Series com saldo por conta
    """
    df = df.copy()
    df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y')
    today = date.today()
    saldo_s = df[df['Data'].dt.date <= today].groupby('Conta')['Valor'].sum()
    saldo_s = round(saldo_s, 2)
    return saldo_s


def adicionar_anomes(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona coluna anomes ao DataFrame."""
    df['anomes'] = df['Data'].apply(
        lambda x: f'{x.year}0{x.month}' if x.month < 10 else f'{x.year}{x.month}'
    )
    df['anomes'] = df['anomes'].apply(lambda x: -1 if x == 'nannan' else x)
    return df


def calcular_despesa_total(df: pd.DataFrame, anome: int) -> dict:
    """
    Calcula métricas de despesas para um mês específico.
    
    Args:
        df: DataFrame filtrado (sem desconsiderar e só despesas)
        anome: Ano+mês em formato inteiro (ex: 202403)
    
    Returns:
        Dicionário com métricas
    """
    anome_str = str(anome)
    year = int(anome_str[:4])
    month = int(anome_str[4:])

    current_month_start = pd.Timestamp(year=year, month=month, day=1)
    next_month_start = current_month_start + pd.DateOffset(months=1)
    previous_month_start = current_month_start - pd.DateOffset(months=1)
    month_before_previous_start = previous_month_start - pd.DateOffset(months=1)
    last_3_months_start = current_month_start - pd.DateOffset(months=3)
    previous_quarter_start = current_month_start - pd.DateOffset(months=6)

    gasto_atual = abs(round(df[(df['Data'] >= current_month_start) & (df['Data'] < next_month_start)]['Valor'].sum(), 2))
    gasto_anterior = abs(round(df[(df['Data'] >= previous_month_start) & (df['Data'] < current_month_start)]['Valor'].sum(), 2))
    gasto_mes_antes = abs(round(df[(df['Data'] >= month_before_previous_start) & (df['Data'] < previous_month_start)]['Valor'].sum(), 2))
    gasto_3m_media = abs(round(df[(df['Data'] >= last_3_months_start) & (df['Data'] < current_month_start)]['Valor'].sum() / 3, 2))
    gasto_trimestre_anterior_media = abs(round(df[(df['Data'] >= previous_quarter_start) & (df['Data'] < last_3_months_start)]['Valor'].sum() / 3, 2))

    delta_anterior = (gasto_anterior - gasto_mes_antes) / gasto_mes_antes if gasto_mes_antes != 0 else None
    delta_atual = (gasto_atual - gasto_anterior) / gasto_anterior if gasto_anterior != 0 else None
    delta_3m = (gasto_3m_media - gasto_trimestre_anterior_media) / gasto_trimestre_anterior_media if gasto_trimestre_anterior_media != 0 else None

    return {
        'gasto_atual': gasto_atual,
        'gasto_anterior': gasto_anterior,
        'gasto_mes_antes': gasto_mes_antes,
        'gasto_3m_media': gasto_3m_media,
        'delta_anterior': delta_anterior,
        'delta_atual': delta_atual,
        'delta_3m': delta_3m,
        'label_prev': previous_month_start.strftime('%m/%Y'),
        'label_curr': current_month_start.strftime('%m/%Y'),
        'label_3m': f'{last_3_months_start.strftime("%m/%Y")} - {previous_month_start.strftime("%m/%Y")}',
    }


def exibir_despesa_total(df: pd.DataFrame, anome: int) -> None:
    """Exibe métricas de despesas no Streamlit."""
    metricas = calcular_despesa_total(df, anome)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            f'Gasto mês anterior ({metricas["label_prev"]})',
            value=metricas['gasto_anterior'],
            delta=f'{round(metricas["delta_anterior"], 2)*100}%' if metricas["delta_anterior"] is not None else None,
            delta_color='inverse'
        )
    with col2:
        st.metric(
            f'Gasto mês atual ({metricas["label_curr"]})',
            value=metricas['gasto_atual'],
            delta=f'{round(metricas["delta_atual"], 2)*100}%' if metricas["delta_atual"] is not None else None,
            delta_color='inverse'
        )
    with col3:
        st.metric(
            f'Média últimos 3 meses ({metricas["label_3m"]})',
            value=metricas['gasto_3m_media'],
            delta=f'{round(metricas["delta_3m"], 2)*100}%' if metricas["delta_3m"] is not None else None,
            delta_color='inverse'
        )


def forecast(df: pd.DataFrame, anome: int) -> pd.DataFrame:
    """
    Calcula forecast (média dos últimos 3 meses) por categoria.
    
    Args:
        df: DataFrame filtrado
        anome: Ano+mês para forecast
    
    Returns:
        DataFrame com valores forecast por categoria
    """
    forecast_df = pd.DataFrame(columns=['Valor', 'Categoria', 'Tipo', 'anomes'])
    df = df[(df['desconsiderar'] == False) & (df['anomes'].astype(int) <= int(anome))]
    
    for e in df['Categoria'].unique():
        row = len(forecast_df)
        forecast_df.loc[row, 'Tipo'] = df[df['Categoria'] == e]['Tipo'].iloc[0]
        forecast_df.loc[row, 'anomes'] = anome
        forecast_df.loc[row, 'Categoria'] = e
        forecast_df.loc[row, 'Valor'] = df[df['Categoria'] == e].groupby('anomes')['Valor'].sum()[-4:-1].mean()
    
    return forecast_df


def calcular_custo_fixo(df: pd.DataFrame, custo_fixo: pd.DataFrame, anome: int) -> pd.DataFrame:
    """Calcula custo fixo ao longo do tempo."""
    anomeses = df['anomes'].unique()
    custo_fixo_tempo = pd.DataFrame(columns=['Nome', 'Valor', 'anomes'])
    row = 0
    
    for a in anomeses:
        for i in custo_fixo.index:
            custo_fixo_tempo.loc[row, 'Nome'] = custo_fixo.loc[i, 'Conta']
            custo_fixo_tempo.loc[row, 'Valor'] = custo_fixo.loc[i, 'Valor']
            custo_fixo_tempo.loc[row, 'anomes'] = a
            row += 1

    df = df.copy()
    df['anomes'] = df['anomes'].astype(int)
    df = df[(df['desconsiderar'] == False) & (df['Tipo'] == 'Despesa') & (df['Parcela'].isna() == False) & (df['anomes'] >= anome - 2)]
    df['Valor'] = abs(df['Valor'])
    data = df.groupby(['anomes', 'Nome'])['Valor'].sum().reset_index()
    data = pd.concat([data, custo_fixo_tempo])
    
    return data