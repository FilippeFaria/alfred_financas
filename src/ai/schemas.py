from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class EntradaTexto(BaseModel):
    texto: str = Field(min_length=1)
    data_referencia: datetime | None = None


class EntradaAudio(BaseModel):
    caminho_arquivo: str = Field(min_length=1)
    data_referencia: datetime | None = None


class TransacaoSugerida(BaseModel):
    data: date | None = None
    tipo: Literal["Despesa", "Receita", "Transferência", "Pagamento de Cartão"] | None = None
    categoria: str | None = None
    conta: str | None = None
    conta_destino: str | None = None
    nome: str | None = None
    valor: float | None = None

    origem: Literal["texto", "audio"]
    descricao_original: str
    transcricao: str | None = None

    confianca: float = Field(ge=0.0, le=1.0)
    campos_incertos: list[str] = Field(default_factory=list)
    justificativa: str | None = None

    bruto_modelo: dict[str, Any] | None = None


class SugestaoTransacaoResultado(BaseModel):
    sugestao: TransacaoSugerida
    confianca: float = Field(ge=0.0, le=1.0)
    pendencias: list[str] = Field(default_factory=list)
    avisos_validacao: list[str] = Field(default_factory=list)
    origem: str = "texto"
    texto_transcrito: str | None = None
