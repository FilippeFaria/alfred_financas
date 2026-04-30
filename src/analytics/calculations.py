"""
Funções de cálculos para análise financeira.
Contém funções de agregação, forecast e métricas.
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime
from typing import Optional
from src.config import (
    GRANDES_TRANSACOES,
)


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
    # Dados já normalizados em '%d/%m/%Y %H:%M' por carregar_dados()
    df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y %H:%M')
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
    # Dados já normalizados em '%d/%m/%Y %H:%M' por carregar_dados()
    df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y %H:%M')
    today = date.today()
    saldo_s = df[df['Data'].dt.date <= today].groupby('Conta')['Valor'].sum()
    saldo_s = round(saldo_s, 2)
    return saldo_s


def adicionar_anomes(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona coluna anomes ao DataFrame."""
    df = df.copy()
    # Dados já normalizados em '%d/%m/%Y %H:%M' por carregar_dados()
    df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y %H:%M')
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
    df = df.copy()
    # Dados chegam normalizados como string e precisam virar datetime para filtros mensais.
    df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y %H:%M')

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


def _preparar_datas_analiticas(df: pd.DataFrame) -> pd.DataFrame:
    """Converte a coluna Data para datetime em um dataframe de trabalho."""
    df = df.copy()
    df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y %H:%M')
    return df


def obter_data_corte_mes(df: pd.DataFrame, referencia: datetime | date) -> int:
    """
    Replica a logica de comparacao por dia do mes usada no Streamlit.

    A data de corte e definida pelo maior dia com movimentacao no mes atual,
    priorizando registros sem parcela para evitar distorcoes de lancamentos futuros.
    """
    df = _preparar_datas_analiticas(df)
    referencia_ts = pd.Timestamp(referencia)
    inicio_mes_atual = pd.Timestamp(year=referencia_ts.year, month=referencia_ts.month, day=1)
    inicio_proximo_mes = inicio_mes_atual + pd.DateOffset(months=1)

    df_mes_atual = df[(df['Data'] >= inicio_mes_atual) & (df['Data'] < inicio_proximo_mes)].copy()
    if df_mes_atual.empty:
        return int(referencia_ts.day)

    if 'Parcela' in df_mes_atual.columns:
        df_sem_parcela = df_mes_atual[df_mes_atual['Parcela'].isna()]
        if not df_sem_parcela.empty:
            df_mes_atual = df_sem_parcela

    data_corte = df_mes_atual['Data'].dt.day.max()
    if pd.isna(data_corte):
        return int(referencia_ts.day)

    return int(data_corte)


def filtrar_despesas_ate_dia_mes(
    df: pd.DataFrame,
    referencia: datetime | date,
) -> dict[str, pd.DataFrame | int | pd.Timestamp]:
    """
    Retorna despesas do mes atual e do mes anterior ate o mesmo dia do mes.
    """
    df = _preparar_datas_analiticas(df)

    referencia_ts = pd.Timestamp(referencia)
    data_corte = obter_data_corte_mes(df, referencia_ts)
    df = df[(df['desconsiderar'] == False) & (df['Tipo'] == 'Despesa') & (df["id"].isin(GRANDES_TRANSACOES)==False)].copy()
    df.copy() if "id" in df.columns else df.copy()
    inicio_mes_atual = pd.Timestamp(year=referencia_ts.year, month=referencia_ts.month, day=1)
    inicio_proximo_mes = inicio_mes_atual + pd.DateOffset(months=1)
    inicio_mes_anterior = inicio_mes_atual - pd.DateOffset(months=1)

    df_mes_atual = df[
        (df['Data'] >= inicio_mes_atual) &
        (df['Data'] < inicio_proximo_mes) &
        (df['Data'].dt.day <= data_corte)
    ].copy()

    df_mes_anterior = df[
        (df['Data'] >= inicio_mes_anterior) &
        (df['Data'] < inicio_mes_atual) &
        (df['Data'].dt.day <= data_corte)
    ].copy()

    return {
        'data_corte': data_corte,
        'inicio_mes_atual': inicio_mes_atual,
        'inicio_mes_anterior': inicio_mes_anterior,
        'df_mes_atual': df_mes_atual,
        'df_mes_anterior': df_mes_anterior,
    }


def calcular_comparativo_despesas_ate_dia_mes(
    df: pd.DataFrame,
    referencia: datetime | date,
) -> dict[str, float | int | pd.Timestamp | None]:
    """
    Calcula o gasto acumulado no mes atual versus o mesmo dia do mes anterior.
    """
    dados = filtrar_despesas_ate_dia_mes(df, referencia)
    gasto_atual = abs(round(float(dados['df_mes_atual']['Valor'].sum()), 2))
    gasto_anterior = abs(round(float(dados['df_mes_anterior']['Valor'].sum()), 2))
    delta_percentual = None
    if gasto_anterior != 0:
        delta_percentual = (gasto_atual - gasto_anterior) / gasto_anterior

    return {
        'data_corte': dados['data_corte'],
        'inicio_mes_atual': dados['inicio_mes_atual'],
        'inicio_mes_anterior': dados['inicio_mes_anterior'],
        'gasto_atual': gasto_atual,
        'gasto_anterior': gasto_anterior,
        'delta_percentual': delta_percentual,
    }


def calcular_comparativo_categorias_ate_dia_mes(
    df: pd.DataFrame,
    referencia: datetime | date,
) -> pd.DataFrame:
    """
    Compara o acumulado por categoria no mes atual versus o mesmo dia do mes anterior.
    """
    dados = filtrar_despesas_ate_dia_mes(df, referencia)
    atual = (
        dados['df_mes_atual']
        .groupby('Categoria')['Valor']
        .sum()
        .abs()
        .reset_index()
        .rename(columns={'Valor': 'valor_atual'})
    )
    anterior = (
        dados['df_mes_anterior']
        .groupby('Categoria')['Valor']
        .sum()
        .abs()
        .reset_index()
        .rename(columns={'Valor': 'valor_anterior'})
    )

    comparativo = atual.merge(anterior, on='Categoria', how='outer').fillna(0)
    comparativo['delta_valor'] = comparativo['valor_atual'] - comparativo['valor_anterior']
    comparativo['percentual_orcamento'] = np.nan

    return comparativo.sort_values('delta_valor', ascending=False).reset_index(drop=True)
