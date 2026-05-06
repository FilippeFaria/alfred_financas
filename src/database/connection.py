"""Infraestrutura centralizada de conexao com PostgreSQL (Supabase)."""

from __future__ import annotations

import os
from typing import Generator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()


def _garantir_sslmode_require(database_url: str) -> str:
    """Garante sslmode=require na URL de conexao."""
    partes = urlsplit(database_url)
    params = dict(parse_qsl(partes.query, keep_blank_values=True))
    params.setdefault("sslmode", "require")
    nova_query = urlencode(params)
    return urlunsplit((partes.scheme, partes.netloc, partes.path, nova_query, partes.fragment))


def _obter_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Variavel de ambiente DATABASE_URL nao configurada.")
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

