from __future__ import annotations

from src.ai.schemas import EntradaAudio, EntradaTexto, TransacaoSugerida
from src.ingestion.audio.transcriber import transcrever_arquivo_audio

from .text_parser import extrair_transacao_por_texto


def extrair_transacao_por_audio(entrada: EntradaAudio) -> TransacaoSugerida:
    texto, _metadados = transcrever_arquivo_audio(entrada.caminho_arquivo)
    sugestao = extrair_transacao_por_texto(
        EntradaTexto(texto=texto, data_referencia=entrada.data_referencia)
    )
    return sugestao.model_copy(update={"origem": "audio", "transcricao": texto})
