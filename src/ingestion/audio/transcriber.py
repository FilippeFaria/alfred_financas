from __future__ import annotations

from src.ai.clients import AIClientError, transcrever_audio as transcrever_audio_openai

from .normalizer import normalizar_metadados_audio


def transcrever_audio(file_path: str) -> str:
    """Transcreve um arquivo de audio em portugues sem persistir transacao."""
    metadados = normalizar_metadados_audio(file_path)
    try:
        return transcrever_audio_openai(file_path=metadados["caminho"], language="pt")
    except AIClientError as exc:
        raise RuntimeError("Nao foi possivel transcrever o audio informado.") from exc


def transcrever_arquivo_audio(caminho_arquivo: str) -> tuple[str, dict]:
    metadados = normalizar_metadados_audio(caminho_arquivo)
    texto_transcrito = transcrever_audio(metadados["caminho"])
    return texto_transcrito, metadados
