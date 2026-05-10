"""Infraestrutura centralizada de conexao com PostgreSQL (Supabase)."""

from __future__ import annotations

import os
from typing import Generator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
import logging

from src.database.base import Base

load_dotenv()
LOGGER = logging.getLogger(__name__)


def _garantir_sslmode_require(database_url: str) -> str:
    """Garante sslmode=require apenas para conexoes PostgreSQL."""
    if not database_url.startswith(("postgresql://", "postgres://")):
        return database_url

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    partes = urlsplit(database_url)
    params = dict(parse_qsl(partes.query, keep_blank_values=True))
    params.setdefault("sslmode", "require")
    nova_query = urlencode(params)
    return urlunsplit((partes.scheme, partes.netloc, partes.path, nova_query, partes.fragment))


def _obter_database_url() -> str:
    database_url = (
        os.getenv("DATABASE_URL_POOLER")
        or os.getenv("SUPABASE_SESSION_POOLER_URL")
        or os.getenv("DATABASE_URL")
    )
    if not database_url:
        raise RuntimeError("Variavel de ambiente DATABASE_URL nao configurada.")

    partes = urlsplit(database_url)
    host = (partes.hostname or "").lower()
    porta = partes.port
    usa_supabase_direto = host.startswith("db.") and host.endswith(".supabase.co") and porta == 5432
    if usa_supabase_direto:
        LOGGER.warning(
            "DATABASE_URL parece usar conexao direta IPv6 do Supabase (%s:%s). "
            "Prefira Session Pooler IPv4 (aws-*.pooler.supabase.com:5432).",
            host,
            porta,
        )
    return _garantir_sslmode_require(database_url)


DATABASE_URL = _obter_database_url()

engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency pronta para integracao futura com FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Cria as tabelas registradas na metadata ORM."""
    Base.metadata.create_all(bind=engine)
