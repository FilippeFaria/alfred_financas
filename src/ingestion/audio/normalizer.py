from __future__ import annotations

from pathlib import Path

EXTENSOES_AUDIO_PERMITIDAS = {".mp3", ".wav", ".m4a", ".ogg", ".webm"}
TAMANHO_MAXIMO_PADRAO_BYTES = 25 * 1024 * 1024


def normalizar_metadados_audio(caminho_arquivo: str, *, tamanho_maximo_bytes: int = TAMANHO_MAXIMO_PADRAO_BYTES) -> dict:
    caminho = Path(caminho_arquivo).expanduser().resolve()

    if not caminho.exists() or not caminho.is_file():
        raise ValueError("Arquivo de audio nao encontrado.")

    extensao = caminho.suffix.lower()
    if extensao not in EXTENSOES_AUDIO_PERMITIDAS:
        raise ValueError(f"Extensao de audio nao suportada: {extensao}")

    tamanho_bytes = caminho.stat().st_size
    if tamanho_bytes <= 0:
        raise ValueError("Arquivo de audio vazio.")

    if tamanho_bytes > tamanho_maximo_bytes:
        raise ValueError(
            f"Arquivo de audio excede tamanho maximo de {tamanho_maximo_bytes} bytes."
        )

    return {
        "caminho": str(caminho),
        "nome": caminho.name,
        "extensao": extensao,
        "tamanho_bytes": int(tamanho_bytes),
    }
