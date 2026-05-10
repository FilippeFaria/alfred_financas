from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CampoPendente(str, Enum):
    NOME = "nome"
    TIPO = "tipo"
    VALOR = "valor"
    CATEGORIA = "categoria"
    CONTA = "conta"
    DATA = "data"


class EntradaTexto(BaseModel):
    texto: str = Field(min_length=1)
    data_referencia: datetime | None = None


class EntradaAudio(BaseModel):
    caminho_arquivo: str = Field(min_length=1)
    data_referencia: datetime | None = None


class ExtracaoIA(BaseModel):
    nome: str | None = None
    tipo: str | None = None
    valor: float | None = None
    categoria: str | None = None
    conta: str | None = None
    data: datetime | None = None
    obs: str | None = None
    tag: str | None = None
    desconsiderar: bool = False
    campos_pendentes: list[CampoPendente] = Field(default_factory=list)
    justificativa: str | None = None
    bruto_modelo: dict[str, Any] | None = None


class SugestaoTransacao(BaseModel):
    nome: str | None = None
    tipo: str | None = None
    valor: float | None = None
    categoria: str | None = None
    conta: str | None = None
    data: datetime | None = None
    obs: str = ""
    tag: str | None = None
    desconsiderar: bool = False


class SugestaoTransacaoResultado(BaseModel):
    sugestao: SugestaoTransacao
    confianca: float = Field(ge=0.0, le=1.0)
    pendencias: list[str] = Field(default_factory=list)
    avisos_validacao: list[str] = Field(default_factory=list)
    origem: str = "texto"
    texto_transcrito: str | None = None
