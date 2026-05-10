import json
import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.database.connection import SessionLocal
from src.database.repositories import TransactionRepository, UserRepository
from src.services.google_sheets import read_valores_desejados
from src.services.data_handler import carregar_dados


ROOT_PATH = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger(__name__)
FALLBACK_ENABLED = os.getenv("ALFRED_SHEETS_FALLBACK_ENABLED", "true").strip().lower() in {"1", "true", "yes"}


def _map_tx_to_dataframe_row(tx) -> dict:
    """Converte um objeto Transaction do ORM para um dicionário compatível com formato esperado."""
    legacy_id = tx.legacy_id if tx.legacy_id is not None else int(tx.id.int % 2_000_000_000)
    return {
        "id_transacao": int(legacy_id),
        "Nome": tx.nome,
        "Tipo": tx.tipo,
        "Valor": float(tx.valor),
        "Categoria": tx.category.nome if tx.category else "",
        "Conta": tx.account.nome if tx.account else "",
        "Data": tx.data.strftime("%d/%m/%Y %H:%M") if tx.data else "",
        "Obs": tx.observacao or "",
        "tag": tx.tag,
        "desconsiderar": bool(tx.desconsiderar),
        "Data Criacao": tx.created_at.strftime("%d/%m/%Y %H:%M") if tx.created_at else None,
        "parcela": tx.parcela,
        "Data origem": tx.data_origem.strftime("%d/%m/%Y %H:%M") if tx.data_origem else None,
    }


def carregar_dados_financeiros() -> pd.DataFrame:
    """
    Carrega dados financeiros do PostgreSQL com fallback para Google Sheets.
    Retorna DataFrame compatível com formato legado.
    """
    try:
        with SessionLocal() as db:
            user = UserRepository(db).get_or_create_default()
            items = TransactionRepository(db).list_all(user_id=user.id)
            
            if not items:
                LOGGER.info("Nenhuma transação encontrada no PostgreSQL")
                return pd.DataFrame()
            
            rows = [_map_tx_to_dataframe_row(item) for item in items]
            df = pd.DataFrame(rows)
            LOGGER.info(f"Carregadas {len(df)} transações do PostgreSQL")
            return df
            
    except Exception as exc:
        LOGGER.exception("Falha ao carregar dados do PostgreSQL")
        _log_error(
            "postgres_read_error_telegram",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        
        if not FALLBACK_ENABLED:
            raise RuntimeError(
                "Falha ao carregar dados financeiros do PostgreSQL."
            ) from exc
        
        # Fallback para Google Sheets
        try:
            LOGGER.info("Tentando fallback para Google Sheets")
            df = carregar_dados(str(ROOT_PATH))
            if not df.empty:
                LOGGER.info(f"Carregadas {len(df)} transações do Google Sheets (fallback)")
            return df
        except Exception as exc_sheets:
            LOGGER.exception("Falha no fallback do Google Sheets")
            raise RuntimeError(
                "Falha ao carregar dados de ambas as fontes (PostgreSQL e Google Sheets)."
            ) from exc_sheets


def carregar_valores_desejados() -> dict[str, float]:
    """
    Carrega o orçamento desejado por categoria do Google Sheets.
    Em futuras iterações, essa informação virá do PostgreSQL.
    """
    try:
        df_valores = read_valores_desejados(str(ROOT_PATH))
    except Exception as exc:
        LOGGER.exception("Falha ao carregar valores desejados do Google Sheets")
        _log_error(
            "sheets_read_error_oramentos",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return {}

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


def _log_error(event: str, **fields) -> None:
    """Registra erros em formato estruturado (JSON)."""
    LOGGER.error(json.dumps({"event": event, **fields}, ensure_ascii=False, default=str))
