from __future__ import annotations

from datetime import datetime

from .confidence import calcular_confianca
from .parsers.audio_parser import extrair_transacao_por_audio
from .parsers.text_parser import extrair_transacao_por_texto
from .schemas import EntradaAudio, EntradaTexto, SugestaoTransacaoResultado
from .validators import normalizar_para_sugestao, validar_extracao


def sugerir_transacao_por_texto(texto: str, *, data_referencia: datetime | None = None) -> SugestaoTransacaoResultado:
    entrada = EntradaTexto(texto=texto, data_referencia=data_referencia)
    extracao = extrair_transacao_por_texto(entrada)
    avisos, pendencias = validar_extracao(extracao)
    confianca = calcular_confianca(
        pendencias=pendencias,
        avisos=avisos,
        justificativa=extracao.justificativa,
    )
    return SugestaoTransacaoResultado(
        sugestao=normalizar_para_sugestao(extracao),
        confianca=confianca,
        pendencias=[campo.value for campo in pendencias],
        avisos_validacao=avisos,
        origem="texto",
    )


def sugerir_transacao_por_audio(caminho_arquivo: str, *, data_referencia: datetime | None = None) -> SugestaoTransacaoResultado:
    entrada = EntradaAudio(caminho_arquivo=caminho_arquivo, data_referencia=data_referencia)
    extracao, texto = extrair_transacao_por_audio(entrada)
    avisos, pendencias = validar_extracao(extracao)
    confianca = calcular_confianca(
        pendencias=pendencias,
        avisos=avisos,
        justificativa=extracao.justificativa,
    )
    return SugestaoTransacaoResultado(
        sugestao=normalizar_para_sugestao(extracao),
        confianca=confianca,
        pendencias=[campo.value for campo in pendencias],
        avisos_validacao=avisos,
        origem="audio",
        texto_transcrito=texto,
    )
