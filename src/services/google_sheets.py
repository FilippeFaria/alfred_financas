"""
Serviço de integração com Google Sheets.
Gerencia autenticação, leitura e escrita de dados.
"""
import streamlit as st
import pandas as pd
import gspread
import json
from google.oauth2.service_account import Credentials
from pathlib import Path
from typing import Optional

from src.config import SPREADSHEET_NAME, SPREADSHEET_VALORES_NAME


@st.cache_resource
def authorize_google_sheets(path: str = '.') -> gspread.Client:
    """
    Autentica e retorna cliente do Google Sheets.
    
    Args:
        path: Caminho para credentials local (usado em desenvolvimento)
    
    Returns:
        Cliente autenticado do gspread
    """
    if path == '.':
        # Produção: usar secrets do Streamlit
        creds_dict = json.loads(st.secrets["gcp_service_account"])
    else:
        # Desenvolvimento local: carregar do arquivo
        with open(f'{path}/credentials.json') as f:
            creds_dict = json.load(f)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(credentials)


def get_sheet(path: str = '.') -> gspread.Worksheet:
    """
    Abre a planilha principal de fluxo de caixa.
    
    Args:
        path: Caminho para credentials local
    
    Returns:
        Primeira aba da planilha
    """
    client = authorize_google_sheets(path)
    spreadsheet = client.open(SPREADSHEET_NAME)
    return spreadsheet.sheet1


def get_sheet_valores_desejados(path: str = '.') -> gspread.Worksheet:
    """
    Abre a planilha de valores desejados.
    
    Args:
        path: Caminho para credentials local
    
    Returns:
        Primeira aba da planilha de valores desejados
    """
    client = authorize_google_sheets(path)
    spreadsheet = client.open(SPREADSHEET_VALORES_NAME)
    return spreadsheet.sheet1


@st.cache_data
def read_sheet(path: str = '.', trigger: Optional[float] = None) -> pd.DataFrame:
    """
    Lê todos os registros da planilha de fluxo de caixa.
    
    Args:
        path: Caminho para credentials local
        trigger: Timestamp para invalidar cache
    
    Returns:
        DataFrame com os dados
    """
    sheet = get_sheet(path)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # Converter colunas numéricas
    for col in df.columns:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='ignore')
    
    return df


def _limpar_valores_invalidos(x):
    """Remove valores inválidos (listas/dicts) para escrita no Sheets."""
    if isinstance(x, (list, dict)):
        return ''
    return x


def write_sheet(sheet: gspread.Worksheet, df: pd.DataFrame) -> None:
    """
    Escreve DataFrame na planilha.
    
    Args:
        sheet: Worksheet do gspread
        df: DataFrame a ser escrito
    """
    df = df.fillna('')
    df['Valor'] = df['Valor'].astype(str)
    # Aplicar limpeza de valores inválidos
    try:
        df = df.applymap(_limpar_valores_invalidos)
    except AttributeError:
        # Para versões recentes do pandas, applymap foi renomeado para map
        df = df.map(_limpar_valores_invalidos)
    
    # Atualizar a planilha com os dados
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())


@st.cache_data
def read_valores_desejados(path: str = '.', trigger: Optional[float] = None) -> pd.DataFrame:
    """
    Lê os valores desejados por categoria.
    
    Args:
        path: Caminho para credentials local
        trigger: Timestamp para invalidar cache
    
    Returns:
        DataFrame com valores desejados
    """
    sheet = get_sheet_valores_desejados(path)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    if 'Valor' in df.columns:
        df['Valor'] = pd.to_numeric(df['Valor'].astype(str).str.replace(',', '.'), errors='ignore')
    
    return df


def write_valores_desejados(path: str, df: pd.DataFrame) -> None:
    """
    Salva os valores desejados no Google Sheets.
    
    Args:
        path: Caminho para credentials local
        df: DataFrame com valores desejados
    """
    sheet = get_sheet_valores_desejados(path)
    df = df.fillna('')
    df['Valor'] = df['Valor'].astype(str)
    df = df.applymap(_limpar_valores_invalidos)
    sheet.update([df.columns.values.tolist()] + df.values.tolist())