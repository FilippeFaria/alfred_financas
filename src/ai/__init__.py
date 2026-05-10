"""Modulo de IA do Alfred Financas.

Este pacote contem apenas funcoes e contratos reutilizaveis.
Nao executa chamadas externas no import.
"""

from .schemas import (
    CampoPendente,
    EntradaAudio,
    EntradaTexto,
    ExtracaoIA,
    SugestaoTransacao,
    SugestaoTransacaoResultado,
)
from .services import sugerir_transacao_por_audio, sugerir_transacao_por_texto

__all__ = [
    "CampoPendente",
    "EntradaAudio",
    "EntradaTexto",
    "ExtracaoIA",
    "SugestaoTransacao",
    "SugestaoTransacaoResultado",
    "sugerir_transacao_por_audio",
    "sugerir_transacao_por_texto",
]
