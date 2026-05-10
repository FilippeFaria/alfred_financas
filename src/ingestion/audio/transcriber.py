from __future__ import annotations

from src.ai.clients import transcrever_audio

from .normalizer import normalizar_metadados_audio


def transcrever_arquivo_audio(caminho_arquivo: str) -> tuple[str, dict]:
    metadados = normalizar_metadados_audio(caminho_arquivo)
    texto_transcrito = transcrever_audio(file_path=metadados["caminho"], language="pt")
    return texto_transcrito, metadados
