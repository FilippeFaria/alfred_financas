from __future__ import annotations

import os
from functools import lru_cache

DEFAULT_OPENAI_MODEL = os.getenv("ALFRED_OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


@lru_cache(maxsize=1)
def get_openai_client():
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY nao configurada.")
    return OpenAI(api_key=api_key)


def interpretar_transacao_texto(prompt_sistema: str, texto_usuario: str, *, model: str | None = None) -> dict:
    client = get_openai_client()
    resposta = client.responses.create(
        model=model or DEFAULT_OPENAI_MODEL,
        input=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": texto_usuario},
        ],
        response_format={"type": "json_object"},
    )

    if not resposta.output_text:
        return {}

    import json

    try:
        return json.loads(resposta.output_text)
    except Exception:
        return {"texto": resposta.output_text}


def transcrever_audio(caminho_arquivo: str, *, model: str = "gpt-4o-mini-transcribe") -> str:
    client = get_openai_client()
    with open(caminho_arquivo, "rb") as arquivo:
        transcricao = client.audio.transcriptions.create(
            model=model,
            file=arquivo,
        )
    return (getattr(transcricao, "text", "") or "").strip()
