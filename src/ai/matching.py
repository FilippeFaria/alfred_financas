from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from src.ai.clients import escolher_valor_categorico_com_llm


def normalizar_string(valor: str | None) -> str:
    texto = (valor or "").strip().lower()
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _match_exato(valor_normalizado: str, opcoes: list[str]) -> str | None:
    if not valor_normalizado:
        return None
    mapa: dict[str, str] = {}
    for opcao in opcoes:
        chave = normalizar_string(opcao)
        if chave and chave not in mapa:
            mapa[chave] = opcao
    return mapa.get(valor_normalizado)


def _candidatos_fuzzy(valor_normalizado: str, opcoes: list[str]) -> list[tuple[str, float]]:
    candidatos: list[tuple[str, float]] = []
    for opcao in opcoes:
        score = SequenceMatcher(None, valor_normalizado, normalizar_string(opcao)).ratio()
        candidatos.append((opcao, score))
    candidatos.sort(key=lambda item: item[1], reverse=True)
    return candidatos


def resolver_categorico(
    *,
    campo: str,
    valor_bruto: str | None,
    opcoes: list[str],
    fuzzy_cutoff: float = 0.84,
) -> tuple[str | None, str]:
    """Resolve valor categorico em 5 etapas: normalizar, exato, fuzzy, llm, validar."""
    valor_normalizado = normalizar_string(valor_bruto)
    if not valor_normalizado:
        return None, "vazio"

    # 1-2) normalizacao + matching exato
    exato = _match_exato(valor_normalizado, opcoes)
    if exato:
        return exato, "exato"

    # 3) fuzzy matching
    candidatos = _candidatos_fuzzy(valor_normalizado, opcoes)
    if candidatos and candidatos[0][1] >= fuzzy_cutoff:
        return candidatos[0][0], "fuzzy"

    # 4) LLM como desempate quando fuzzy nao foi suficiente
    shortlist = [opcao for opcao, _ in candidatos[:5]]
    llm_escolha = escolher_valor_categorico_com_llm(
        campo=campo,
        valor_bruto=valor_bruto or "",
        opcoes=shortlist,
    )

    # 5) validacao final contra as opcoes canonicas
    if llm_escolha in opcoes:
        return llm_escolha, "llm"
    return None, "sem_match"

