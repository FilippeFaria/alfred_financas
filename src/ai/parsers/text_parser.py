from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from src.ai.clients import interpretar_transacao_texto
from src.ai.confidence import calcular_confianca
from src.ai.schemas import EntradaTexto, TransacaoSugerida
from src.ai.validators import validar_transacao_sugerida
from src.ingestion.text.normalizer import normalizar_texto_entrada

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "transaction_from_text.md"


def _carregar_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _normalizar_tipo(valor: str | None) -> str | None:
    if not valor:
        return None
    mapa = {
        "transferencia": "Transferência",
        "transferência": "Transferência",
        "pagamento de cartao": "Pagamento de Cartão",
        "pagamento de cartão": "Pagamento de Cartão",
        "despesa": "Despesa",
        "receita": "Receita",
    }
    return mapa.get(valor.strip().lower(), valor)


def _parse_data(payload: dict, data_referencia: datetime | None) -> date | None:
    data_str = payload.get("data")
    if isinstance(data_str, str) and data_str.strip():
        try:
            return datetime.fromisoformat(data_str).date()
        except ValueError:
            pass
    if isinstance(data_referencia, datetime):
        return data_referencia.date()
    return None


def _parse_saida_modelo(payload: dict, entrada: EntradaTexto) -> TransacaoSugerida:
    campos_incertos = payload.get("campos_incertos") or payload.get("campos_pendentes") or []
    if not isinstance(campos_incertos, list):
        campos_incertos = []

    sugestao = TransacaoSugerida(
        data=_parse_data(payload, entrada.data_referencia),
        tipo=_normalizar_tipo(payload.get("tipo")),
        categoria=payload.get("categoria"),
        conta=payload.get("conta"),
        conta_destino=payload.get("conta_destino"),
        nome=payload.get("nome"),
        valor=payload.get("valor"),
        origem="texto",
        descricao_original=entrada.texto,
        transcricao=None,
        confianca=0.0,
        campos_incertos=[str(item) for item in campos_incertos if str(item).strip()],
        justificativa=payload.get("justificativa"),
        bruto_modelo=payload,
    )

    avisos, campos_incertos_final = validar_transacao_sugerida(sugestao)
    sugestao.campos_incertos = campos_incertos_final
    sugestao.confianca = calcular_confianca(
        campos_incertos=campos_incertos_final,
        avisos=avisos,
        justificativa=sugestao.justificativa,
    )
    return sugestao


def extrair_transacao_por_texto(entrada: EntradaTexto) -> TransacaoSugerida:
    prompt = _carregar_prompt()
    texto_normalizado = normalizar_texto_entrada(entrada.texto)
    payload = interpretar_transacao_texto(prompt, texto_normalizado)

    if not isinstance(payload, dict):
        try:
            payload = json.loads(str(payload))
        except Exception:
            payload = {}

    entrada_normalizada = EntradaTexto(
        texto=texto_normalizado,
        data_referencia=entrada.data_referencia,
    )
    return _parse_saida_modelo(payload, entrada_normalizada)
