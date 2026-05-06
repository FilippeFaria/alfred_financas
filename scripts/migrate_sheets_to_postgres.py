"""Migra transacoes do Google Sheets para PostgreSQL via SQLAlchemy ORM.

Fluxo:
Google Sheets -> DataFrame -> Normalizacao -> ORM -> PostgreSQL
"""

from __future__ import annotations

import logging
import os
from hashlib import sha1
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

import pandas as pd

from src.database import Account, Category, SessionLocal, Transaction, User
from src.database.connection import init_db
from src.services.google_sheets import read_sheet


LOGGER = logging.getLogger("migrate_sheets_to_postgres")


@dataclass
class MigrationStats:
    total_linhas_origem: int = 0
    linhas_validas_origem: int = 0
    linhas_invalidas_origem: int = 0
    inseridas: int = 0
    duplicadas_origem: int = 0
    duplicadas_destino: int = 0
    falhas: int = 0


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "t", "sim", "s", "yes", "y"}


def _to_decimal(value: Any) -> Decimal:
    if pd.isna(value):
        raise ValueError("Valor ausente")
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    texto = str(value).strip().replace(".", "").replace(",", ".")
    # Se o numero ja vier com ponto decimal, desfaz somente se tiver virgula tambem.
    if "," not in str(value):
        texto = str(value).strip().replace(",", ".")

    try:
        return Decimal(texto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError(f"Valor invalido: {value}") from exc


def _to_datetime(value: Any, campo: str) -> datetime | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    parsed = pd.to_datetime(value, format="mixed", dayfirst=True, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Data invalida em {campo}: {value}")
    if isinstance(parsed, pd.Timestamp):
        return parsed.to_pydatetime()
    return parsed


def _normalizar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    normalizado = df.copy()
    normalizado.columns = [str(c).strip() for c in normalizado.columns]

    # Mantem colunas essenciais com defaults seguros
    for col in ["Nome", "Tipo", "Categoria", "Conta", "Obs", "TAG", "Data", "Data origem", "Data Criacao", "Parcela", "desconsiderar", "Valor"]:
        if col not in normalizado.columns:
            normalizado[col] = None

    normalizado["Nome"] = normalizado["Nome"].astype(str).str.strip()
    normalizado["Tipo"] = normalizado["Tipo"].astype(str).str.strip()
    normalizado["Categoria"] = normalizado["Categoria"].astype(str).str.strip()
    normalizado["Conta"] = normalizado["Conta"].astype(str).str.strip()
    normalizado["Obs"] = normalizado["Obs"].fillna("").astype(str).str.strip()
    normalizado["TAG"] = normalizado["TAG"].fillna("").astype(str).str.strip()
    normalizado["Parcela"] = pd.to_numeric(normalizado["Parcela"], errors="coerce")

    return normalizado


def _legacy_id(value: Any) -> int | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    return int(float(value))


def _build_origem_chave(
    *,
    legacy_id: int | None,
    nome: str,
    tipo: str,
    valor: Decimal,
    categoria: str,
    conta: str,
    data: datetime,
    parcela: int | None,
    data_origem: datetime | None,
    data_criacao: datetime | None,
    obs: str,
    tag: str,
) -> str:
    bruto = "|".join(
        [
            str(legacy_id or ""),
            nome.strip(),
            tipo.strip(),
            str(valor),
            categoria.strip(),
            conta.strip(),
            data.isoformat(),
            str(parcela or ""),
            data_origem.isoformat() if data_origem else "",
            data_criacao.isoformat() if data_criacao else "",
            obs.strip(),
            tag.strip(),
        ]
    )
    return sha1(bruto.encode("utf-8")).hexdigest()


def _obter_ou_criar_usuario(db, email: str, nome: str | None) -> User:
    usuario = db.query(User).filter(User.email == email).one_or_none()
    if usuario:
        return usuario

    usuario = User(email=email, nome=nome)
    db.add(usuario)
    db.flush()
    return usuario


def _mapear_contas(db, user_id) -> dict[str, Account]:
    contas = db.query(Account).filter(Account.user_id == user_id).all()
    return {c.nome.strip().lower(): c for c in contas}


def _mapear_categorias(db, user_id) -> dict[tuple[str, str], Category]:
    categorias = db.query(Category).filter(Category.user_id == user_id).all()
    return {(c.nome.strip().lower(), c.tipo.strip().lower()): c for c in categorias}


def _mapear_transacoes_existentes(db, user_id) -> set[str]:
    existentes: set[str] = set()
    transacoes = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    for t in transacoes:
        if t.origem_chave:
            existentes.add(t.origem_chave)
    return existentes


def migrate() -> int:
    _setup_logging()
    LOGGER.info("Iniciando migracao Google Sheets -> PostgreSQL")

    origem = read_sheet(path=".")
    origem = _normalizar_dataframe(origem)
    stats = MigrationStats(total_linhas_origem=len(origem))

    init_db()

    migration_user_email = os.getenv("MIGRATION_USER_EMAIL", "default@alfred.local").strip().lower()
    migration_user_name = os.getenv("MIGRATION_USER_NAME", "Migracao Inicial").strip() or None

    with SessionLocal() as db:
        usuario = _obter_ou_criar_usuario(db, migration_user_email, migration_user_name)
        contas_map = _mapear_contas(db, usuario.id)
        categorias_map = _mapear_categorias(db, usuario.id)
        existentes_destino = _mapear_transacoes_existentes(db, usuario.id)
        existentes_lote: set[str] = set()

        for idx, row in origem.iterrows():
            try:
                with db.begin_nested():
                    nome = str(row.get("Nome", "")).strip()
                    tipo = str(row.get("Tipo", "")).strip()
                    categoria_nome = str(row.get("Categoria", "")).strip()
                    conta_nome = str(row.get("Conta", "")).strip()
                    if not tipo or not categoria_nome or not conta_nome:
                        raise ValueError("Campos obrigatorios ausentes (Tipo/Categoria/Conta)")

                    valor = _to_decimal(row.get("Valor"))
                    data = _to_datetime(row.get("Data"), "Data")
                    if data is None:
                        raise ValueError("Data obrigatoria ausente")

                    parcela = row.get("Parcela")
                    parcela_int = None if pd.isna(parcela) else int(parcela)
                    legacy_id = _legacy_id(row.get("id"))
                    obs = str(row.get("Obs", "") or "").strip()
                    tag = str(row.get("TAG", "") or "").strip()
                    data_origem = _to_datetime(row.get("Data origem"), "Data origem")
                    data_criacao = _to_datetime(row.get("Data Criacao"), "Data Criacao")
                    chave = _build_origem_chave(
                        legacy_id=legacy_id,
                        nome=nome,
                        tipo=tipo,
                        valor=valor,
                        categoria=categoria_nome,
                        conta=conta_nome,
                        data=data,
                        parcela=parcela_int,
                        data_origem=data_origem,
                        data_criacao=data_criacao,
                        obs=obs,
                        tag=tag,
                    )

                    if chave in existentes_lote:
                        stats.duplicadas_origem += 1
                        continue

                    if chave in existentes_destino:
                        stats.duplicadas_destino += 1
                        continue

                    conta_key = conta_nome.lower()
                    conta = contas_map.get(conta_key)
                    if conta is None:
                        conta = Account(user_id=usuario.id, nome=conta_nome)
                        db.add(conta)
                        db.flush()
                        contas_map[conta_key] = conta

                    categoria_key = (categoria_nome.lower(), tipo.lower())
                    categoria = categorias_map.get(categoria_key)
                    if categoria is None:
                        categoria = Category(user_id=usuario.id, nome=categoria_nome, tipo=tipo)
                        db.add(categoria)
                        db.flush()
                        categorias_map[categoria_key] = categoria

                    transacao = Transaction(
                        legacy_id=legacy_id,
                        user_id=usuario.id,
                        account_id=conta.id,
                        category_id=categoria.id,
                        nome=nome,
                        tipo=tipo,
                        valor=valor,
                        data=data,
                        observacao=obs or None,
                        tag=tag or None,
                        desconsiderar=_to_bool(row.get("desconsiderar")),
                        parcela=parcela_int,
                        data_origem=data_origem,
                        origem_chave=chave,
                    )
                    if data_criacao is not None:
                        transacao.created_at = data_criacao
                    db.add(transacao)
                    db.flush()
                    existentes_lote.add(chave)
                    stats.inseridas += 1
                    stats.linhas_validas_origem += 1

                    if stats.inseridas % 250 == 0:
                        LOGGER.info("Progresso: %s transacoes inseridas", stats.inseridas)
            except Exception as exc:
                stats.falhas += 1
                stats.linhas_invalidas_origem += 1
                LOGGER.exception("Falha ao processar linha %s: %s", idx, exc)

        db.commit()

        total_destino_usuario = db.query(Transaction).filter(Transaction.user_id == usuario.id).count()
        esperado_sem_falhas = (
            stats.total_linhas_origem - stats.duplicadas_origem - stats.duplicadas_destino - stats.falhas
        )

        LOGGER.info("Resumo da migracao")
        LOGGER.info("Total origem: %s", stats.total_linhas_origem)
        LOGGER.info("Validas processadas: %s", stats.linhas_validas_origem)
        LOGGER.info("Inseridas: %s", stats.inseridas)
        LOGGER.info("Duplicadas na origem: %s", stats.duplicadas_origem)
        LOGGER.info("Duplicadas no destino: %s", stats.duplicadas_destino)
        LOGGER.info("Falhas: %s", stats.falhas)
        LOGGER.info("Total no destino (usuario migracao): %s", total_destino_usuario)

        consistencia_ok = stats.inseridas == esperado_sem_falhas
        if consistencia_ok:
            LOGGER.info("Validacao de consistencia: OK")
            return 0

        LOGGER.error(
            "Validacao de consistencia: FALHOU | inseridas=%s esperado=%s",
            stats.inseridas,
            esperado_sem_falhas,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(migrate())
