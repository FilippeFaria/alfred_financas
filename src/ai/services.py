from __future__ import annotations

from datetime import datetime

from .parsers.audio_parser import extrair_transacao_por_audio
from .parsers.text_parser import extrair_transacao_por_texto
from .schemas import EntradaAudio, EntradaTexto, SugestaoTransacaoResultado
from .validators import validar_transacao_sugerida


def sugerir_transacao_por_texto(texto: str, *, data_referencia: datetime | None = None) -> SugestaoTransacaoResultado:
    entrada = EntradaTexto(texto=texto, data_referencia=data_referencia)
    sugestao = extrair_transacao_por_texto(entrada)
    avisos, campos_incertos = validar_transacao_sugerida(sugestao)
    return SugestaoTransacaoResultado(
        sugestao=sugestao,
        confianca=sugestao.confianca,
        pendencias=campos_incertos,
        avisos_validacao=avisos,
        origem="texto",
    )


def sugerir_transacao_por_audio(caminho_arquivo: str, *, data_referencia: datetime | None = None) -> SugestaoTransacaoResultado:
    entrada = EntradaAudio(caminho_arquivo=caminho_arquivo, data_referencia=data_referencia)
    sugestao = extrair_transacao_por_audio(entrada)
    avisos, campos_incertos = validar_transacao_sugerida(sugestao)
    return SugestaoTransacaoResultado(
        sugestao=sugestao,
        confianca=sugestao.confianca,
        pendencias=campos_incertos,
        avisos_validacao=avisos,
        origem="audio",
        texto_transcrito=sugestao.transcricao,
    )


def criar_pendencia_por_texto(texto: str, *, data_referencia: datetime | None = None):
    from src.services.pending_transaction_service import criar_transacao_pendente

    resultado = sugerir_transacao_por_texto(texto, data_referencia=data_referencia)
    payload = resultado.sugestao.model_dump(mode="json")
    return criar_transacao_pendente(
        source="texto",
        raw_text=resultado.sugestao.descricao_original,
        transcription=None,
        suggested_payload=payload,
        confidence=resultado.confianca,
    )


def criar_pendencia_por_audio(caminho_arquivo: str, *, data_referencia: datetime | None = None):
    from src.services.pending_transaction_service import criar_transacao_pendente

    resultado = sugerir_transacao_por_audio(caminho_arquivo, data_referencia=data_referencia)
    payload = resultado.sugestao.model_dump(mode="json")
    return criar_transacao_pendente(
        source="audio",
        raw_text=resultado.sugestao.descricao_original,
        transcription=resultado.sugestao.transcricao,
        suggested_payload=payload,
        confidence=resultado.confianca,
    )
