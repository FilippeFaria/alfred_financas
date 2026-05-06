"""Schemas da API FastAPI."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SaldoContaResponse(BaseModel):
    conta: str
    saldo: float


class TransacaoResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    valor: float
    categoria: str
    conta: str
    data: str
    obs: str = ""
    tag: Optional[str] = None
    desconsiderar: bool = False
    data_criacao: Optional[str] = None
    parcela: Optional[int] = None
    data_origem: Optional[str] = None


class CriarTransacaoRequest(BaseModel):
    nome: str = Field(min_length=1)
    tipo: str = Field(min_length=1)
    valor: float
    categoria: str = Field(min_length=1)
    conta: str = Field(min_length=1)
    data: datetime
    obs: str = ""
    tag: Optional[str] = None
    desconsiderar: bool = False
    parcelas: Optional[int] = Field(default=None, ge=1)


class TransacoesResponse(BaseModel):
    total: int
    items: list[TransacaoResponse]


class CategoriasResponse(BaseModel):
    despesa: list[str]
    receita: list[str]
    investimento: list[str]


class InsightsRequest(BaseModel):
    pergunta: Optional[str] = None


class InsightsResponse(BaseModel):
    resumo: str
    insights: list[str]

