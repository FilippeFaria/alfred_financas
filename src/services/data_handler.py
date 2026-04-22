"""
Serviço de manipulação de dados do fluxo de caixa.
Gerencia operações de CRUD e transformações nos dados.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Optional

from src.services.google_sheets import read_sheet, write_sheet
from src.config import CONTAS, CONTAS_INVEST


def carregar_dados(path: str = '.', trigger: Optional[float] = None) -> pd.DataFrame:
    """
    Carrega e preprocessa os dados do fluxo de caixa.
    
    Args:
        path: Caminho para credentials local
        trigger: Timestamp para invalidar cache
    
    Returns:
        DataFrame processado
    """
    df = read_sheet(path, trigger)
    
    # Preprocessamento
    df['Valor'] = df['Valor'].astype('float64')
    df['desconsiderar'] = df['desconsiderar'].replace('TRUE', True).replace('FALSE', False)
    df['Categoria'] = df['Categoria'].str.replace('TV.Internet.Telefone', 'Assinaturas')
    df['Data'] = pd.to_datetime(df['Data'], format="%d/%m/%Y %H:%M")
    
    return df


def excluir_registro(sheet, df: pd.DataFrame, id: int) -> pd.DataFrame:
    """
    Exclui um registro pelo ID e atualiza no Google Sheets.
    
    Args:
        sheet: Worksheet do Google Sheets
        df: DataFrame atual
        id: ID do registro a excluir
    
    Returns:
        DataFrame atualizado
    """
    df_atualizado = df[df['id'] != id].copy()
    
    if len(df_atualizado) == len(df):
        st.error(f"Nenhum registro encontrado com o ID {id}")
        return df
    
    # Formatar a data corretamente antes de salvar
    df_atualizado['Data'] = pd.to_datetime(df_atualizado['Data'], format="%Y-%m-%d %H:%M:%S", errors='coerce')
    df_atualizado['Data'] = df_atualizado['Data'].dt.strftime('%d/%m/%Y %H:%M')
    
    write_sheet(sheet, df_atualizado)
    st.cache_data.clear()
    st.session_state.last_update = datetime.now().timestamp()
    st.success(f"Registro com ID {id} excluído com sucesso!")
    
    return df_atualizado


def salvar_transacao(
    sheet,
    df: pd.DataFrame,
    id: int,
    nome: str,
    tipo: str,
    valor: float,
    categoria: str,
    conta: str,
    data: datetime,
    obs: str = '',
    tag: Optional[str] = None,
    parcelas: Optional[int] = None,
    desconsiderar: bool = False,
    adicionar_transferencia: bool = False
) -> pd.DataFrame:
    """
    Salva uma nova transação no DataFrame e Google Sheets.
    
    Args:
        sheet: Worksheet do Google Sheets
        df: DataFrame atual
        id: ID da transação
        nome: Nome da transação
        tipo: Tipo (Receita, Despesa, Transferência, Investimento)
        valor: Valor da transação
        categoria: Categoria
        conta: Conta
        data: Data da transação
        obs: Observação
        tag: TAG(s)
        parcelas: Número de parcelas (opcional)
        desconsiderar: Se deve ser desconsiderada na análise
        adicionar_transferencia: Se é parte de uma transferência
    
    Returns:
        DataFrame atualizado
    """
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    data_criacao = dt_string

    if parcelas is None:
        # Transação única
        nova_linha = pd.DataFrame([{
            'id': id,
            'Nome': nome,
            'Tipo': tipo,
            'Valor': valor,
            'Categoria': categoria,
            'Conta': conta,
            'Data': data.strftime("%Y-%m-%d %H:%M:%S"),
            'Obs': obs,
            'desconsiderar': desconsiderar,
            'Data Criacao': data_criacao,
            'TAG': tag
        }])
        df = pd.concat([df, nova_linha], ignore_index=True)
    else:
        # Transação parcelada
        for i in range(parcelas):
            nova_linha = pd.DataFrame([{
                'id': id,
                'Nome': nome,
                'Tipo': tipo,
                'Valor': valor,
                'Categoria': categoria,
                'Conta': conta,
                'Data': (data + relativedelta(months=i)).strftime("%Y-%m-%d %H:%M:%S"),
                'Obs': obs,
                'desconsiderar': desconsiderar,
                'Parcela': i + 1,
                'Data origem': data.strftime("%Y-%m-%d %H:%M:%S"),
                'Data Criacao': data_criacao,
                'TAG': tag
            }])
            df = pd.concat([df, nova_linha], ignore_index=True)

    # Corrigir bug da transferência
    if adicionar_transferencia and valor < 0:
        return df
    else:
        df['Data'] = pd.to_datetime(df['Data'], format="%Y-%m-%d %H:%M:%S")
        df['Data'] = df['Data'].dt.strftime('%d/%m/%Y %H:%M')
        
        write_sheet(sheet, df)
        st.cache_data.clear()
        st.session_state.last_update = datetime.now().timestamp()
        st.success("Dados salvos com sucesso!")
    
    return df


def aplicar_filtros(
    df: pd.DataFrame,
    desconsiderar: bool = True,
    va: bool = False,
    vr: bool = False,
    bianca: bool = False,
    filippe: bool = False
) -> pd.DataFrame:
    """
    Aplica filtros ao DataFrame baseado nas opções do usuário.
    
    Args:
        df: DataFrame original
        desconsiderar: Se deve filtrar grandes transações
        va: Se deve desconsiderar VA
        vr: Se deve desconsiderar VR
        bianca: Se deve filtrar só contas da Bianca
        filippe: Se deve filtrar só contas do Filippe
    
    Returns:
        DataFrame filtrado
    """
    df_temp = df.copy()
    
    from src.config import GRANDES_TRANSACOES
    
    if desconsiderar:
        idx = df_temp[df_temp['id'].isin(GRANDES_TRANSACOES)].index
        df_temp = df_temp.drop(idx)
    
    if va:
        idx = df_temp[df_temp['Conta'].isin(['VA'])].index
        df_temp = df_temp.drop(idx)
    
    if vr:
        idx = df_temp[df_temp['Conta'].isin(['VR'])].index
        df_temp = df_temp.drop(idx)
    
    if bianca:
        contas_filtradas = ['Cartão Bianca', 'Inter', 'Itaú CC', 'Cartão Nath', 'VA', 'VR']
        df_temp = df_temp[df_temp['Conta'].isin(contas_filtradas)]
        contas_multiplicar = ['Itaú CC', 'Cartão Nath', 'VA', 'VR']
        df_temp.loc[df_temp['Conta'].isin(contas_multiplicar), 'Valor'] *= 0.3
    
    elif filippe:
        contas_filtradas = ['Cartão Filippe', 'Nubank', 'Itaú CC', 'Cartão Nath', 'VA', 'VR']
        df_temp = df_temp[df_temp['Conta'].isin(contas_filtradas)]
        contas_multiplicar = ['Itaú CC', 'Cartão Nath', 'VA', 'VR']
        df_temp.loc[df_temp['Conta'].isin(contas_multiplicar), 'Valor'] *= 0.7
    
    return df_temp