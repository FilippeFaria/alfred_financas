from __future__ import annotations

import re


_RE_MOEDA = re.compile(r"(?<!\d)(\d{1,3}(?:\.\d{3})*),(\d{2})(?!\d)")


def normalizar_texto_entrada(texto: str) -> str:
    texto_limpo = (texto or "").strip()
    if not texto_limpo:
        raise ValueError("Texto de entrada vazio.")

    texto_limpo = re.sub(r"\s+", " ", texto_limpo)

    # Converte formatos como 1.234,56 para 1234.56, facilitando leitura consistente.
    texto_limpo = _RE_MOEDA.sub(lambda m: f"{m.group(1).replace('.', '')}.{m.group(2)}", texto_limpo)

    return texto_limpo
