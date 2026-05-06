"""Repositories para acesso a dados no PostgreSQL."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import os
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.database.models import Account, Category, Transaction, User


def _uuid_to_legacy_int(value: UUID) -> int:
    return int(value.int % 2_000_000_000)


class TransactionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self, *, user_id: UUID, limit: int | None = None) -> list[Transaction]:
        query = (
            self.db.query(Transaction)
            .options(joinedload(Transaction.account), joinedload(Transaction.category))
            .filter(Transaction.user_id == user_id)
            .order_by(Transaction.data.desc())
        )
        if limit:
            query = query.limit(limit)
        return query.all()

    def create(
        self,
        *,
        user_id: UUID,
        account_id: UUID,
        category_id: UUID,
        legacy_id: int | None,
        nome: str,
        tipo: str,
        valor: Decimal,
        data: datetime,
        observacao: str | None,
        tag: str | None,
        desconsiderar: bool,
        parcela: int | None,
        data_origem: datetime | None,
        origem_chave: str | None = None,
        created_at: datetime | None = None,
    ) -> Transaction:
        item = Transaction(
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            legacy_id=legacy_id,
            nome=nome,
            tipo=tipo,
            valor=valor,
            data=data,
            observacao=observacao,
            tag=tag,
            desconsiderar=desconsiderar,
            parcela=parcela,
            data_origem=data_origem,
            origem_chave=origem_chave,
        )
        if created_at is not None:
            item.created_at = created_at
        self.db.add(item)
        self.db.flush()
        self.db.refresh(item)
        return item

    def delete_by_legacy_id(self, *, user_id: UUID, legacy_id: int) -> int:
        remover = (
            self.db.query(Transaction)
            .filter(Transaction.user_id == user_id, Transaction.legacy_id == legacy_id)
            .all()
        )
        total = len(remover)
        for item in remover:
            self.db.delete(item)
        return total

    def get_next_legacy_id(self, *, user_id: UUID) -> int:
        atual = (
            self.db.query(func.max(Transaction.legacy_id))
            .filter(Transaction.user_id == user_id)
            .scalar()
        )
        return int(atual or 0) + 1


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create_default(self) -> User:
        email = os.getenv("ALFRED_DEFAULT_USER_EMAIL", "default@alfred.local").strip().lower()
        item = self.db.query(User).filter(User.email == email).one_or_none()
        if item:
            return item
        item = User(email=email, nome="Usuario Padrao")
        self.db.add(item)
        self.db.flush()
        return item


class AccountRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create(self, *, user_id: UUID, nome: str) -> Account:
        item = (
            self.db.query(Account)
            .filter(Account.user_id == user_id, Account.nome == nome)
            .one_or_none()
        )
        if item:
            return item
        item = Account(user_id=user_id, nome=nome)
        self.db.add(item)
        self.db.flush()
        return item


class CategoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create(self, *, user_id: UUID, nome: str, tipo: str) -> Category:
        item = (
            self.db.query(Category)
            .filter(Category.user_id == user_id, Category.nome == nome, Category.tipo == tipo)
            .one_or_none()
        )
        if item:
            return item
        item = Category(user_id=user_id, nome=nome, tipo=tipo)
        self.db.add(item)
        self.db.flush()
        return item
