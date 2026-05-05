"""
Servico de integracao com Google Sheets.
Gerencia autenticacao, leitura e escrita de dados.
"""

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

from src.config import SPREADSHEET_NAME, SPREADSHEET_VALORES_NAME


LOGGER = logging.getLogger(__name__)


def _load_creds_from_streamlit_secrets() -> Optional[dict]:
    """Tenta carregar credenciais do Streamlit Secrets."""
    try:
        import streamlit as st
    except Exception:
        return None

    # Em ambientes fora do Streamlit Cloud (ex.: Render bot), acessar st.secrets pode falhar.
    # Nesses casos retornamos None para permitir fallback via variável de ambiente.
    try:
        if "google_service_account" in st.secrets:
            return dict(st.secrets["google_service_account"])
    except Exception:
        return None

    try:
        raw_value = st.secrets.get("GOOGLE_SHEETS_CREDS_JSON", "")
    except Exception:
        return None

    raw_json = str(raw_value).strip()
    if not raw_json:
        return None

    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "GOOGLE_SHEETS_CREDS_JSON em Streamlit Secrets esta em formato invalido."
        ) from exc

    return None


@lru_cache(maxsize=4)
def authorize_google_sheets(path: str = ".") -> gspread.Client:
    """Autentica e retorna cliente do Google Sheets."""
    creds_path = Path(path) / "credentials.json"
    creds_dict = None

    if creds_path.exists():
        with open(creds_path, encoding="utf-8") as f:
            creds_dict = json.load(f)
        LOGGER.info("Google Sheets auth: usando credentials.json local.")
    else:
        creds_dict = _load_creds_from_streamlit_secrets()
        if creds_dict is not None:
            LOGGER.info("Google Sheets auth: usando Streamlit Secrets.")
        else:
            creds_json_env = os.getenv("GOOGLE_SHEETS_CREDS_JSON", "").strip()
            LOGGER.info(
                "Google Sheets auth: credentials.json e Streamlit Secrets ausentes; GOOGLE_SHEETS_CREDS_JSON configurado=%s tamanho=%s",
                bool(creds_json_env),
                len(creds_json_env),
            )
            if not creds_json_env:
                raise RuntimeError(
                    "Credenciais do Google Sheets nao encontradas. Configure Streamlit Secrets ([google_service_account]) ou GOOGLE_SHEETS_CREDS_JSON."
                )

            creds_dict = json.loads(creds_json_env)
            LOGGER.info("Google Sheets auth: usando GOOGLE_SHEETS_CREDS_JSON.")


    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(credentials)


def get_sheet(path: str = ".") -> gspread.Worksheet:
    client = authorize_google_sheets(path)
    spreadsheet = client.open(SPREADSHEET_NAME)
    return spreadsheet.sheet1


def get_sheet_valores_desejados(path: str = ".") -> gspread.Worksheet:
    client = authorize_google_sheets(path)
    spreadsheet = client.open(SPREADSHEET_VALORES_NAME)
    return spreadsheet.sheet1


def read_sheet(path: str = ".", trigger: Optional[float] = None) -> pd.DataFrame:
    sheet = get_sheet(path)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    numeric_cols = ["Valor", "id", "Parcela"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "."), errors="coerce")

    return df


def _limpar_valores_invalidos(x):
    if isinstance(x, (list, dict)):
        return ""
    return x


def write_sheet(sheet: gspread.Worksheet, df: pd.DataFrame) -> None:
    df = df.fillna("")
    df["Valor"] = df["Valor"].astype(str)
    try:
        df = df.applymap(_limpar_valores_invalidos)
    except AttributeError:
        df = df.map(_limpar_valores_invalidos)

    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())


def read_valores_desejados(path: str = ".", trigger: Optional[float] = None) -> pd.DataFrame:
    sheet = get_sheet_valores_desejados(path)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if "Valor" in df.columns:
        df["Valor"] = pd.to_numeric(df["Valor"].astype(str).str.replace(",", "."), errors="ignore")

    return df


def write_valores_desejados(path: str, df: pd.DataFrame) -> None:
    sheet = get_sheet_valores_desejados(path)
    df = df.fillna("")
    df["Valor"] = df["Valor"].astype(str)
    df = df.applymap(_limpar_valores_invalidos)
    sheet.update([df.columns.values.tolist()] + df.values.tolist())
