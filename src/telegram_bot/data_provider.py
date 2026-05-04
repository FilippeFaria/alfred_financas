import logging
from pathlib import Path

import pandas as pd

from src.services.google_sheets import read_valores_desejados
from src.services.data_handler import carregar_dados


ROOT_PATH = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger(__name__)


def carregar_dados_financeiros() -> pd.DataFrame:
    """Carrega os dados financeiros exclusivamente do Google Sheets."""
    try:
        return carregar_dados(str(ROOT_PATH))
    except Exception as exc:
        LOGGER.exception(
            "Falha ao carregar dados financeiros do Google Sheets. Sem fallback local."
        )
        raise RuntimeError(
            "Falha ao carregar dados financeiros do Google Sheets."
        ) from exc


def carregar_valores_desejados() -> dict[str, float]:
    """Carrega o orcamento desejado por categoria exclusivamente do Google Sheets."""
    try:
        df_valores = read_valores_desejados(str(ROOT_PATH))
    except Exception as exc:
        LOGGER.exception(
            "Falha ao carregar valores desejados do Google Sheets. Sem fallback local."
        )
        raise RuntimeError(
            "Falha ao carregar valores desejados do Google Sheets."
        ) from exc

    if df_valores.empty or "Categoria" not in df_valores.columns or "Valor" not in df_valores.columns:
        return {}

    df_valores = df_valores.copy()
    df_valores["Valor"] = pd.to_numeric(df_valores["Valor"], errors="coerce")
    df_valores = df_valores.dropna(subset=["Categoria", "Valor"])
    df_valores = df_valores[df_valores["Valor"] > 0]
    return {
        str(linha["Categoria"]).strip(): float(linha["Valor"])
        for _, linha in df_valores.iterrows()
    }
