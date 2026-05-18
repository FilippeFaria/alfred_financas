"""Repositories para acesso a dados no PostgreSQL."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
import os
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.database.models import (
    Account,
    Budget,
    CaptureTrainingExample,
    Category,
    PendingTransaction,
    SmsCapturePreference,
    Transaction,
    User,
)


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
        contas: list[str] | None = None,
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
        elif contas:
            query = query.filter(Account.nome.in_(contas))
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
        contas: list[str] | None = None,
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
        elif contas:
            query = query.filter(Account.nome.in_(contas))
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
            .options(joinedload(Transaction.account), joinedload(Transaction.category))
            .filter(Transaction.user_id == user_id, Transaction.legacy_id == legacy_id)
            .order_by(Transaction.data.asc())
            .all()
        )

    def get_by_row_id(self, *, user_id: UUID, row_id: UUID) -> Transaction | None:
        return (
            self.db.query(Transaction)
            .options(joinedload(Transaction.account), joinedload(Transaction.category))
            .filter(Transaction.user_id == user_id, Transaction.id == row_id)
            .one_or_none()
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

    def exists_duplicate(
        self,
        *,
        user_id: UUID,
        account_id: UUID,
        valor: Decimal,
        data: datetime,
    ) -> bool:
        return (
            self.db.query(Transaction.id)
            .filter(
                Transaction.user_id == user_id,
                Transaction.account_id == account_id,
                Transaction.valor == valor,
                Transaction.data == data,
            )
            .first()
            is not None
        )


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

    def find_pending_android_notification_by_key(
        self,
        *,
        user_id: UUID,
        notification_key: str,
    ) -> PendingTransaction | None:
        notification_key = (notification_key or "").strip()
        if not notification_key:
            return None

        itens = (
            self.db.query(PendingTransaction)
            .filter(
                PendingTransaction.user_id == user_id,
                PendingTransaction.source == "android_notification",
                PendingTransaction.status == "pending",
            )
            .order_by(PendingTransaction.created_at.desc())
            .all()
        )
        for item in itens:
            payload = item.suggested_payload if isinstance(item.suggested_payload, dict) else {}
            notificacao = payload.get("notificacao") if isinstance(payload.get("notificacao"), dict) else {}
            if str(notificacao.get("notification_key") or "").strip() == notification_key:
                return item
        return None

    def update_status(self, *, item: PendingTransaction, status: str) -> PendingTransaction:
        item.status = status
        self.db.flush()
        self.db.refresh(item)
        return item

    def list_recent_auto_captured(
        self,
        *,
        user_id: UUID,
        since: datetime,
        sources: list[str] | tuple[str, ...],
        statuses: list[str] | tuple[str, ...] = ("pending", "confirmed", "auto_confirmed"),
    ) -> list[PendingTransaction]:
        if not sources:
            return []
        if not statuses:
            return []
        return (
            self.db.query(PendingTransaction)
            .filter(
                PendingTransaction.user_id == user_id,
                PendingTransaction.source.in_(list(sources)),
                PendingTransaction.status.in_(list(statuses)),
                PendingTransaction.created_at >= since,
            )
            .order_by(PendingTransaction.created_at.desc())
            .all()
        )


class CaptureTrainingExampleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: UUID,
        pending_transaction_id: UUID | None,
        source: str,
        raw_text: str,
        capture_payload: dict,
        suggested_payload_inicial: dict,
        payload_confirmado: dict,
        transacao_confirmada: dict,
        campos_editados: list[str],
    ) -> CaptureTrainingExample:
        item = CaptureTrainingExample(
            user_id=user_id,
            pending_transaction_id=pending_transaction_id,
            source=source,
            raw_text=raw_text,
            capture_payload=capture_payload,
            suggested_payload_inicial=suggested_payload_inicial,
            payload_confirmado=payload_confirmado,
            transacao_confirmada=transacao_confirmada,
            campos_editados=campos_editados,
        )
        self.db.add(item)
        self.db.flush()
        self.db.refresh(item)
        return item

    def list_recent(
        self,
        *,
        user_id: UUID,
        limit: int = 200,
        source: str | None = None,
    ) -> list[CaptureTrainingExample]:
        query = (
            self.db.query(CaptureTrainingExample)
            .filter(CaptureTrainingExample.user_id == user_id)
            .order_by(CaptureTrainingExample.created_at.desc())
        )
        if source:
            query = query.filter(CaptureTrainingExample.source == source)
        return query.limit(max(1, min(int(limit), 1000))).all()


class SmsCapturePreferenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create_default(self, *, user_id: UUID) -> SmsCapturePreference:
        item = (
            self.db.query(SmsCapturePreference)
            .filter(SmsCapturePreference.user_id == user_id)
            .one_or_none()
        )
        if item is not None:
            return item

        item = SmsCapturePreference(
            user_id=user_id,
            sms_enabled=False,
            bancos_selecionados=[],
            mapeamento_cartao_ultimos4={},
        )
        self.db.add(item)
        self.db.flush()
        self.db.refresh(item)
        return item

    def update_preferences(
        self,
        *,
        item: SmsCapturePreference,
        sms_enabled: bool,
        bancos_selecionados: list[str],
        mapeamento_cartao_ultimos4: dict[str, str],
    ) -> SmsCapturePreference:
        item.sms_enabled = bool(sms_enabled)
        item.bancos_selecionados = list(bancos_selecionados)
        item.mapeamento_cartao_ultimos4 = dict(mapeamento_cartao_ultimos4)
        self.db.flush()
        self.db.refresh(item)
        return item
