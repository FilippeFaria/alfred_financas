from __future__ import annotations

from src.ai.clients import transcrever_audio
from src.ai.schemas import EntradaAudio, EntradaTexto, ExtracaoIA

from .text_parser import extrair_transacao_por_texto


def extrair_transacao_por_audio(entrada: EntradaAudio) -> tuple[ExtracaoIA, str]:
    texto = transcrever_audio(entrada.caminho_arquivo)
    extracao = extrair_transacao_por_texto(
        EntradaTexto(texto=texto, data_referencia=entrada.data_referencia)
    )
    return extracao, texto
