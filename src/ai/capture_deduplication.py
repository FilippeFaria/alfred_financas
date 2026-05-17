"""Deduplicacao cruzada para capturas automaticas (notificacao/SMS)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.database.repositories import PendingTransactionRepository


AUTO_CAPTURE_SOURCES = ("android_notification", "android_sms")
AUTO_CAPTURE_WINDOW_MINUTES = 5


@dataclass
class CaptureDuplicateResult:
    is_duplicate: bool
    reason: str | None = None
    fingerprint: str | None = None


def _parse_iso(value: str | None) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _normalizar_texto(value: str | None) -> str:
    base = (value or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", base).strip()


def _bucket_5_min(dt: datetime) -> str:
    minute = (dt.minute // AUTO_CAPTURE_WINDOW_MINUTES) * AUTO_CAPTURE_WINDOW_MINUTES
    bucket = dt.replace(minute=minute, second=0, microsecond=0)
    return bucket.isoformat()


def construir_fingerprint_captura(*, sugestao_payload: dict, occurred_at_iso: str | None) -> str:
    tipo = _normalizar_texto(str(sugestao_payload.get("tipo") or ""))
    nome = _normalizar_texto(str(sugestao_payload.get("nome") or ""))
    conta = _normalizar_texto(str(sugestao_payload.get("conta") or ""))
    valor = round(float(sugestao_payload.get("valor") or 0.0), 2)
    occurred_at = _parse_iso(occurred_at_iso) or datetime.now(timezone.utc)
    bucket = _bucket_5_min(occurred_at)
    return f"{tipo}|{valor:.2f}|{nome}|{conta}|{bucket}"


def detectar_duplicidade_captura(
    *,
    pending_repo: PendingTransactionRepository,
    user_id,
    source: str,
    event_key: str | None,
    sugestao_payload: dict,
    occurred_at_iso: str | None,
) -> CaptureDuplicateResult:
    event_key_norm = (event_key or "").strip()
    fingerprint = construir_fingerprint_captura(
        sugestao_payload=sugestao_payload,
        occurred_at_iso=occurred_at_iso,
    )
    now_utc = datetime.now(timezone.utc)
    since = now_utc - timedelta(minutes=AUTO_CAPTURE_WINDOW_MINUTES)
    recentes = pending_repo.list_recent_auto_captured(
        user_id=user_id,
        since=since,
        sources=AUTO_CAPTURE_SOURCES,
    )

    for item in recentes:
        payload = dict(item.suggested_payload or {})
        metadata = dict(payload.get("capture_metadata") or {})
        event_key_existente = str(metadata.get("event_key") or "").strip()
        if not event_key_existente:
            notificacao = payload.get("notificacao") if isinstance(payload.get("notificacao"), dict) else {}
            sms = payload.get("sms") if isinstance(payload.get("sms"), dict) else {}
            event_key_existente = str(
                notificacao.get("notification_key") or sms.get("sms_message_id") or ""
            ).strip()
        if event_key_norm and event_key_existente and event_key_norm == event_key_existente:
            return CaptureDuplicateResult(
                is_duplicate=True,
                reason="Duplicada por event_key ja processada na janela de 5 minutos.",
                fingerprint=fingerprint,
            )

    for item in recentes:
        payload = dict(item.suggested_payload or {})
        metadata = dict(payload.get("capture_metadata") or {})
        fingerprint_existente = str(metadata.get("fingerprint") or "").strip()
        if not fingerprint_existente:
            fingerprint_existente = construir_fingerprint_captura(
                sugestao_payload=payload,
                occurred_at_iso=metadata.get("occurred_at"),
            )
        if fingerprint_existente and fingerprint_existente == fingerprint:
            return CaptureDuplicateResult(
                is_duplicate=True,
                reason="Duplicada por fingerprint canonico na janela de 5 minutos.",
                fingerprint=fingerprint,
            )

    return CaptureDuplicateResult(is_duplicate=False, fingerprint=fingerprint)
