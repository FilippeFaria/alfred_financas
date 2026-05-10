"""Repositories para acesso a dados no PostgreSQL."""

from __future__ import annotations

from datetime import datetime, date, time
from decimal import Decimal
import os
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.database.models import Account, Budget, Category, PendingTransaction, Transaction, User


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

    def list_filtered(
        self,
        *,
        user_id: UUID,
        offset: int,
        limit: int,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        categoria: str | None = None,
        conta: str | None = None,
        tipo: str | None = None,
    ) -> list[Transaction]:
        query = (
            self.db.query(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .join(Category, Transaction.category_id == Category.id)
            .options(joinedload(Transaction.account), joinedload(Transaction.category))
            .filter(Transaction.user_id == user_id)
        )

        if data_inicio is not None:
            query = query.filter(Transaction.data >= datetime.combine(data_inicio, time.min))
        if data_fim is not None:
            query = query.filter(Transaction.data <= datetime.combine(data_fim, time.max))
        if categoria:
            query = query.filter(Category.nome == categoria)
        if conta:
            query = query.filter(Account.nome == conta)
        if tipo:
            query = query.filter(Transaction.tipo == tipo)

        return query.order_by(Transaction.data.desc()).offset(offset).limit(limit).all()

    def count_filtered(
        self,
        *,
        user_id: UUID,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        categoria: str | None = None,
        conta: str | None = None,
        tipo: str | None = None,
    ) -> int:
        query = (
            self.db.query(func.count(Transaction.id))
            .join(Account, Transaction.account_id == Account.id)
            .join(Category, Transaction.category_id == Category.id)
            .filter(Transaction.user_id == user_id)
        )

        if data_inicio is not None:
            query = query.filter(Transaction.data >= datetime.combine(data_inicio, time.min))
        if data_fim is not None:
            query = query.filter(Transaction.data <= datetime.combine(data_fim, time.max))
        if categoria:
            query = query.filter(Category.nome == categoria)
        if conta:
            query = query.filter(Account.nome == conta)
        if tipo:
            query = query.filter(Transaction.tipo == tipo)

        return int(query.scalar() or 0)

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

    def get_by_legacy_id(self, *, user_id: UUID, legacy_id: int) -> list[Transaction]:
        return (
            self.db.query(Transaction)
            .filter(Transaction.user_id == user_id, Transaction.legacy_id == legacy_id)
            .order_by(Transaction.data.asc())
            .all()
        )

    def update_flags_by_legacy_id(
        self,
        *,
        user_id: UUID,
        legacy_id: int,
        desconsiderar: bool | None = None,
        tag: str | None = None,
    ) -> int:
        itens = self.get_by_legacy_id(user_id=user_id, legacy_id=legacy_id)
        for item in itens:
            if desconsiderar is not None:
                item.desconsiderar = bool(desconsiderar)
            item.tag = tag
        return len(itens)

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


class BudgetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_latest(self, *, user_id: UUID) -> tuple[datetime | None, list[Budget]]:
        data_ref = (
            self.db.query(func.max(Budget.data))
            .filter(Budget.user_id == user_id)
            .scalar()
        )
        if data_ref is None:
            return None, []

        itens = (
            self.db.query(Budget)
            .filter(Budget.user_id == user_id, Budget.data == data_ref)
            .order_by(Budget.categoria.asc())
            .all()
        )
        return data_ref, itens

    def create_snapshot(
        self,
        *,
        user_id: UUID,
        data: datetime,
        valores: dict[str, float],
    ) -> list[Budget]:
        itens: list[Budget] = []
        for categoria, valor in valores.items():
            item = Budget(
                user_id=user_id,
                data=data,
                categoria=categoria,
                valor=Decimal(str(float(valor))),
            )
            self.db.add(item)
            itens.append(item)
        self.db.flush()
        return itens


class PendingTransactionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: UUID,
        source: str,
        raw_text: str,
        transcription: str | None,
        suggested_payload: dict,
        confidence: float,
        status: str = "pending",
    ) -> PendingTransaction:
        item = PendingTransaction(
            user_id=user_id,
            source=source,
            raw_text=raw_text,
            transcription=transcription,
            suggested_payload=suggested_payload,
            confidence=confidence,
            status=status,
        )
        self.db.add(item)
        self.db.flush()
        self.db.refresh(item)
        return item

    def get_by_id(self, *, user_id: UUID, pending_id: UUID) -> PendingTransaction | None:
        return (
            self.db.query(PendingTransaction)
            .filter(PendingTransaction.user_id == user_id, PendingTransaction.id == pending_id)
            .one_or_none()
        )

    def list_by_status(self, *, user_id: UUID, status: str | None = "pending") -> list[PendingTransaction]:
        query = (
            self.db.query(PendingTransaction)
            .filter(PendingTransaction.user_id == user_id)
            .order_by(PendingTransaction.created_at.desc())
        )
        if status:
            query = query.filter(PendingTransaction.status == status)
        return query.all()

    def update_status(self, *, item: PendingTransaction, status: str) -> PendingTransaction:
        item.status = status
        self.db.flush()
        self.db.refresh(item)
        return item
