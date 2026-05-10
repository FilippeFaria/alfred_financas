from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.ai.clients import interpretar_transacao_texto
from src.ai.schemas import EntradaTexto, ExtracaoIA

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "transaction_from_text.md"


def _carregar_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _parse_saida_modelo(payload: dict, data_referencia: datetime | None) -> ExtracaoIA:
    data_str = payload.get("data")
    data = None
    if isinstance(data_str, str) and data_str.strip():
        try:
            data = datetime.fromisoformat(data_str)
        except ValueError:
            data = None
    if data is None:
        data = data_referencia

    campos_pendentes = payload.get("campos_pendentes", [])
    if not isinstance(campos_pendentes, list):
        campos_pendentes = []

    return ExtracaoIA(
        nome=payload.get("nome"),
        tipo=payload.get("tipo"),
        valor=payload.get("valor"),
        categoria=payload.get("categoria"),
        conta=payload.get("conta"),
        data=data,
        obs=payload.get("obs"),
        tag=payload.get("tag"),
        desconsiderar=bool(payload.get("desconsiderar", False)),
        campos_pendentes=campos_pendentes,
        justificativa=payload.get("justificativa"),
        bruto_modelo=payload,
    )


def extrair_transacao_por_texto(entrada: EntradaTexto) -> ExtracaoIA:
    prompt = _carregar_prompt()
    payload = interpretar_transacao_texto(prompt, entrada.texto)

    if not isinstance(payload, dict):
        try:
            payload = json.loads(str(payload))
        except Exception:
            payload = {}

    return _parse_saida_modelo(payload, entrada.data_referencia)
