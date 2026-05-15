"""Servico para ciclo de vida de transacoes pendentes de IA."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from src.api.services import criar_transacao
from src.database.connection import SessionLocal
from src.database.repositories import PendingTransactionRepository, UserRepository
from src.models.pending_transaction import PendingTransaction

STATUS_PENDING = "pending"
STATUS_CONFIRMED = "confirmed"
STATUS_IGNORED = "ignored"
STATUS_AUTO_CONFIRMED = "auto_confirmed"
STATUS_VALIDOS = {STATUS_PENDING, STATUS_CONFIRMED, STATUS_IGNORED, STATUS_AUTO_CONFIRMED}
SOURCE_VALIDOS = {"texto", "audio", "android_notification"}


def _map_pending(item) -> PendingTransaction:
    return PendingTransaction(
        id=str(item.id),
        user_id=str(item.user_id),
        source=str(item.source),
        raw_text=str(item.raw_text),
        transcription=item.transcription,
        suggested_payload=dict(item.suggested_payload or {}),
        confidence=float(item.confidence),
        status=str(item.status),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _parse_data_transacao(valor) -> datetime:
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime.combine(valor, datetime.min.time())
    if isinstance(valor, str) and valor.strip():
        texto = valor.strip()
        for parser in (
            lambda v: datetime.fromisoformat(v),
            lambda v: datetime.strptime(v, "%d/%m/%Y %H:%M"),
            lambda v: datetime.strptime(v, "%d/%m/%Y"),
            lambda v: datetime.strptime(v, "%Y-%m-%d"),
        ):
            try:
                return parser(texto)
            except ValueError:
                continue
    raise ValueError("Data invalida para confirmacao da transacao pendente.")


def _validar_payload_para_confirmacao(payload: dict) -> None:
    obrigatorios = ("nome", "tipo", "valor", "categoria", "conta", "data")
    faltantes = [campo for campo in obrigatorios if payload.get(campo) in (None, "")]
    if faltantes:
        raise ValueError(f"Campos obrigatorios ausentes na pendencia: {', '.join(faltantes)}")


def criar_transacao_pendente(
    *,
    source: str,
    raw_text: str,
    suggested_payload: dict,
    confidence: float,
    transcription: str | None = None,
) -> PendingTransaction:
    if source not in SOURCE_VALIDOS:
        raise ValueError("source invalido. Use 'texto', 'audio' ou 'android_notification'.")
    if not raw_text or not raw_text.strip():
        raise ValueError("raw_text obrigatorio para criar pendencia.")

    with SessionLocal() as db:
        user = UserRepository(db).get_or_create_default()
        item = PendingTransactionRepository(db).create(
            user_id=user.id,
            source=source,
            raw_text=raw_text.strip(),
            transcription=transcription.strip() if transcription else None,
            suggested_payload=suggested_payload,
            confidence=max(0.0, min(float(confidence), 1.0)),
            status=STATUS_PENDING,
        )
        db.commit()
        return _map_pending(item)


def listar_transacoes_pendentes(*, status: str | None = STATUS_PENDING) -> list[PendingTransaction]:
    if status is not None and status not in STATUS_VALIDOS:
        raise ValueError(f"status invalido: {status}")

    with SessionLocal() as db:
        user = UserRepository(db).get_or_create_default()
        itens = PendingTransactionRepository(db).list_by_status(user_id=user.id, status=status)
        return [_map_pending(item) for item in itens]


def ignorar_transacao_pendente(*, pending_id: str) -> PendingTransaction:
    with SessionLocal() as db:
        user = UserRepository(db).get_or_create_default()
        item = PendingTransactionRepository(db).get_by_id(
            user_id=user.id,
            pending_id=UUID(pending_id),
        )
        if item is None:
            raise ValueError("Transacao pendente nao encontrada.")
        if item.status != STATUS_PENDING:
            raise ValueError("Somente pendencias com status 'pending' podem ser ignoradas.")

        atualizado = PendingTransactionRepository(db).update_status(item=item, status=STATUS_IGNORED)
        db.commit()
        return _map_pending(atualizado)


def confirmar_transacao_pendente(
    *,
    pending_id: str,
    payload_confirmado: dict | None = None,
    auto_confirmed: bool = False,
) -> tuple[PendingTransaction, dict]:
    with SessionLocal() as db:
        user = UserRepository(db).get_or_create_default()
        item = PendingTransactionRepository(db).get_by_id(
            user_id=user.id,
            pending_id=UUID(pending_id),
        )
        if item is None:
            raise ValueError("Transacao pendente nao encontrada.")
        if item.status != STATUS_PENDING:
            raise ValueError("Somente pendencias com status 'pending' podem ser confirmadas.")

        payload_base = dict(item.suggested_payload or {})
        if payload_confirmado:
            payload_base.update(payload_confirmado)
        _validar_payload_para_confirmacao(payload_base)

        transacao_oficial = criar_transacao(
            nome=str(payload_base["nome"]),
            tipo=str(payload_base["tipo"]),
            valor=float(payload_base["valor"]),
            categoria=str(payload_base["categoria"]),
            conta=str(payload_base["conta"]),
            conta_destino=payload_base.get("conta_destino"),
            data=_parse_data_transacao(payload_base["data"]),
            obs=str(payload_base.get("obs") or ""),
            tag=payload_base.get("tag"),
            desconsiderar=bool(payload_base.get("desconsiderar", False)),
            parcelas=payload_base.get("parcelas"),
        )

        item.suggested_payload = payload_base
        novo_status = STATUS_AUTO_CONFIRMED if auto_confirmed else STATUS_CONFIRMED
        atualizado = PendingTransactionRepository(db).update_status(item=item, status=novo_status)
        db.commit()
        return _map_pending(atualizado), transacao_oficial
