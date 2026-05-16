"""Deduplicacao local para notificacoes de transacao."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.config import HISTORICO_PATH


STATE_PATH = HISTORICO_PATH / "notification_dedup_state.json"
MAX_EVENTS = 5000
TIME_WINDOW_MINUTES = 5


@dataclass
class DuplicateCheckResult:
    is_duplicate: bool
    reason: str | None = None


@dataclass
class NotificationDeduplicator:
    state_path: Path = STATE_PATH

    def _carregar(self) -> dict:
        if not self.state_path.exists():
            return {"events": [], "updated_at": None}
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return {"events": [], "updated_at": None}
            if not isinstance(payload.get("events"), list):
                payload["events"] = []
            return payload
        except Exception:
            return {"events": [], "updated_at": None}

    def _salvar(self, payload: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _parse_iso(self, value: str | None) -> datetime | None:
        raw = (value or "").strip()
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None

    def _normalizar_nome(self, nome: str | None) -> str:
        base = (nome or "").lower()
        base = re.sub(r"[^a-z0-9]+", " ", base).strip()
        return base

    def check_duplicate(
        self,
        *,
        notification_key: str,
        package_name: str,
        valor: float,
        nome_estabelecimento: str,
        posted_at_iso: str | None,
    ) -> DuplicateCheckResult:
        state = self._carregar()
        eventos = [item for item in state.get("events", []) if isinstance(item, dict)]

        notification_key = (notification_key or "").strip()
        valor_round = round(float(valor), 2)
        if notification_key:
            for evento in eventos:
                if str(evento.get("notification_key") or "").strip() == notification_key:
                    try:
                        valor_evento = round(float(evento.get("valor") or 0), 2)
                    except Exception:
                        valor_evento = 0.0
                    if valor_evento == 0.0 and valor_round != 0.0:
                        continue
                    return DuplicateCheckResult(
                        is_duplicate=True,
                        reason="Duplicada por notification_key ja processada.",
                    )

        posted_at = self._parse_iso(posted_at_iso) or datetime.now(timezone.utc)
        nome_norm = self._normalizar_nome(nome_estabelecimento)
        package_name = (package_name or "").strip()

        for evento in eventos:
            if str(evento.get("package_name") or "").strip() != package_name:
                continue
            try:
                valor_evento = round(float(evento.get("valor") or 0), 2)
            except Exception:
                continue
            if valor_evento != valor_round:
                continue
            nome_evento = self._normalizar_nome(str(evento.get("nome_estabelecimento") or ""))
            if not nome_evento or nome_evento != nome_norm:
                continue

            evento_at = self._parse_iso(str(evento.get("posted_at") or "")) or self._parse_iso(
                str(evento.get("processed_at") or "")
            )
            if evento_at is None:
                continue

            delta = abs(posted_at - evento_at)
            if delta <= timedelta(minutes=TIME_WINDOW_MINUTES):
                return DuplicateCheckResult(
                    is_duplicate=True,
                    reason="Duplicada por similaridade (app, valor, estabelecimento) na janela de 5 minutos.",
                )

        return DuplicateCheckResult(is_duplicate=False)

    def mark_processed(
        self,
        *,
        notification_key: str,
        package_name: str,
        valor: float,
        nome_estabelecimento: str,
        posted_at_iso: str | None,
    ) -> None:
        state = self._carregar()
        eventos = [item for item in state.get("events", []) if isinstance(item, dict)]
        eventos.append(
            {
                "notification_key": (notification_key or "").strip(),
                "package_name": (package_name or "").strip(),
                "valor": round(float(valor), 2),
                "nome_estabelecimento": (nome_estabelecimento or "").strip(),
                "posted_at": (posted_at_iso or "").strip() or None,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        eventos = eventos[-MAX_EVENTS:]
        self._salvar(
            {
                "events": eventos,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

