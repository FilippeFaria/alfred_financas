"""Servico para base supervisionada de capturas (SMS/notificacao)."""

from __future__ import annotations

import logging
from threading import Thread
from uuid import UUID

from src.database.connection import SessionLocal
from src.database.repositories import CaptureTrainingExampleRepository, UserRepository

LOGGER = logging.getLogger(__name__)


def _normalizar_payload_dict(payload: dict | None) -> dict:
    return dict(payload or {})


def _extrair_capture_payload(suggested_payload: dict) -> dict:
    sms = suggested_payload.get("sms")
    if isinstance(sms, dict):
        return {"sms": dict(sms)}
    notificacao = suggested_payload.get("notificacao")
    if isinstance(notificacao, dict):
        return {"notificacao": dict(notificacao)}
    return {}


def _campos_editados(*, inicial: dict, confirmado: dict) -> list[str]:
    campos_candidatos = (
        "data",
        "tipo",
        "categoria",
        "conta",
        "conta_destino",
        "nome",
        "valor",
        "obs",
        "tag",
        "desconsiderar",
        "parcelas",
    )
    alterados: list[str] = []
    for campo in campos_candidatos:
        if inicial.get(campo) != confirmado.get(campo):
            alterados.append(campo)
    return alterados


def registrar_exemplo_captura_confirmada(
    *,
    user_id: UUID,
    pending_transaction_id: UUID,
    source: str,
    raw_text: str,
    suggested_payload_inicial: dict,
    payload_confirmado: dict,
    transacao_confirmada: dict,
) -> None:
    if source not in {"android_sms", "android_notification"}:
        return

    suggested_inicial = _normalizar_payload_dict(suggested_payload_inicial)
    confirmado = _normalizar_payload_dict(payload_confirmado)
    transacao = _normalizar_payload_dict(transacao_confirmada)
    capture_payload = _extrair_capture_payload(suggested_inicial)
    campos_editados = _campos_editados(inicial=suggested_inicial, confirmado=confirmado)

    with SessionLocal() as db:
        repo = CaptureTrainingExampleRepository(db)
        repo.create(
            user_id=user_id,
            pending_transaction_id=pending_transaction_id,
            source=source,
            raw_text=str(raw_text or ""),
            capture_payload=capture_payload,
            suggested_payload_inicial=suggested_inicial,
            payload_confirmado=confirmado,
            transacao_confirmada=transacao,
            campos_editados=campos_editados,
        )
        db.commit()


def registrar_exemplo_captura_confirmada_async(
    *,
    user_id: UUID,
    pending_transaction_id: UUID,
    source: str,
    raw_text: str,
    suggested_payload_inicial: dict,
    payload_confirmado: dict,
    transacao_confirmada: dict,
) -> None:
    def _worker() -> None:
        try:
            registrar_exemplo_captura_confirmada(
                user_id=user_id,
                pending_transaction_id=pending_transaction_id,
                source=source,
                raw_text=raw_text,
                suggested_payload_inicial=suggested_payload_inicial,
                payload_confirmado=payload_confirmado,
                transacao_confirmada=transacao_confirmada,
            )
        except Exception:
            LOGGER.exception(
                "Falha ao registrar exemplo supervisionado em background",
                extra={
                    "source": source,
                    "pending_transaction_id": str(pending_transaction_id),
                },
            )

    Thread(target=_worker, name=f"capture-training-{pending_transaction_id}", daemon=True).start()


def listar_exemplos_captura_treinamento(*, limit: int = 200, source: str | None = None) -> list[dict]:
    with SessionLocal() as db:
        user = UserRepository(db).get_or_create_default()
        itens = CaptureTrainingExampleRepository(db).list_recent(
            user_id=user.id,
            limit=limit,
            source=source,
        )
        resposta: list[dict] = []
        for item in itens:
            resposta.append(
                {
                    "id": str(item.id),
                    "user_id": str(item.user_id),
                    "pending_transaction_id": str(item.pending_transaction_id) if item.pending_transaction_id else None,
                    "source": str(item.source),
                    "raw_text": str(item.raw_text),
                    "capture_payload": dict(item.capture_payload or {}),
                    "suggested_payload_inicial": dict(item.suggested_payload_inicial or {}),
                    "payload_confirmado": dict(item.payload_confirmado or {}),
                    "transacao_confirmada": dict(item.transacao_confirmada or {}),
                    "campos_editados": [str(v) for v in (item.campos_editados or [])],
                    "created_at": item.created_at,
                }
            )
        return resposta
