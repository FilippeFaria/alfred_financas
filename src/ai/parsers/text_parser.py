from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from src.ai.clients import interpretar_transacao_texto
from src.ai.confidence import calcular_confianca
from src.ai.matching import resolver_categorico
from src.ai.schemas import EntradaTexto, TransacaoSugerida
from src.ai.validators import validar_transacao_sugerida
from src.config import (
    CARTOES_PAGAMENTO,
    CATEGORIAS_DESPESA,
    CATEGORIAS_INVESTIMENTO,
    CATEGORIAS_RECEITA,
    CONTAS,
    CONTAS_INVEST,
)
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


def _opcoes_tipo() -> list[str]:
    return ["Despesa", "Receita", "Transferência", "Pagamento de Cartão", "Investimento"]


def _opcoes_categoria_por_tipo(tipo: str | None) -> list[str]:
    if tipo == "Despesa":
        return CATEGORIAS_DESPESA
    if tipo == "Receita":
        return CATEGORIAS_RECEITA
    if tipo == "Investimento":
        return CATEGORIAS_INVESTIMENTO
    if tipo in {"Transferência", "Pagamento de Cartão"}:
        return ["Transferência"]
    return CATEGORIAS_DESPESA + CATEGORIAS_RECEITA + CATEGORIAS_INVESTIMENTO + ["Transferência"]


def _opcoes_conta_por_tipo(tipo: str | None) -> list[str]:
    contas_base = CONTAS + CONTAS_INVEST + CARTOES_PAGAMENTO
    opcoes = list(dict.fromkeys(contas_base))
    if tipo in {"Despesa", "Receita"}:
        return [conta for conta in opcoes if conta in CONTAS]
    return opcoes


def _parse_data(payload: dict, data_referencia: datetime | None) -> date | None:
    data_str = payload.get("data")
    if isinstance(data_str, str) and data_str.strip():
        try:
            return datetime.fromisoformat(data_str).date()
        except ValueError:
            pass
    if isinstance(data_referencia, datetime):
        return data_referencia.date()
    return datetime.now().date()


def _parse_saida_modelo(payload: dict, entrada: EntradaTexto) -> TransacaoSugerida:
    campos_incertos = payload.get("campos_incertos") or payload.get("campos_pendentes") or []
    if not isinstance(campos_incertos, list):
        campos_incertos = []

    tipo_bruto = _normalizar_tipo(payload.get("tipo"))
    tipo_canonico, tipo_match = resolver_categorico(
        campo="tipo",
        valor_bruto=tipo_bruto,
        opcoes=_opcoes_tipo(),
    )

    categoria_canonica, categoria_match = resolver_categorico(
        campo="categoria",
        valor_bruto=payload.get("categoria"),
        opcoes=_opcoes_categoria_por_tipo(tipo_canonico),
    )

    conta_canonica, conta_match = resolver_categorico(
        campo="conta",
        valor_bruto=payload.get("conta"),
        opcoes=_opcoes_conta_por_tipo(tipo_canonico),
    )

    conta_destino = payload.get("conta_destino")
    conta_destino_canonica = None
    conta_destino_match = "nao_aplicavel"
    if tipo_canonico in {"Transferência", "Pagamento de Cartão", "Investimento"}:
        conta_destino_canonica, conta_destino_match = resolver_categorico(
            campo="conta_destino",
            valor_bruto=conta_destino,
            opcoes=_opcoes_conta_por_tipo(tipo_canonico),
        )

    sugestao = TransacaoSugerida(
        data=_parse_data(payload, entrada.data_referencia),
        tipo=tipo_canonico,
        categoria=categoria_canonica,
        conta=conta_canonica,
        conta_destino=conta_destino_canonica,
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

    if tipo_match == "sem_match":
        sugestao.campos_incertos.append("tipo")
    if categoria_match == "sem_match":
        sugestao.campos_incertos.append("categoria")
    if conta_match == "sem_match":
        sugestao.campos_incertos.append("conta")
    if tipo_canonico in {"Transferência", "Pagamento de Cartão", "Investimento"} and conta_destino_match == "sem_match":
        sugestao.campos_incertos.append("conta_destino")

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
