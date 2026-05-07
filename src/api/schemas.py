"""Schemas da API FastAPI."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SaldoContaResponse(BaseModel):
    conta: str
    saldo: float


class SaldoResponse(SaldoContaResponse):
    """Contrato padrao de saldo por conta."""


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
    pagina: int
    limite: int
    total_paginas: int
    items: list[TransacaoResponse]


class ExcluirTransacaoResponse(BaseModel):
    id: int
    removidos: int
    mensagem: str


class CategoriasResponse(BaseModel):
    despesa: list[str]
    receita: list[str]
    investimento: list[str]


class CategoriaResponse(CategoriasResponse):
    """Contrato padrao de categorias."""


class InsightsRequest(BaseModel):
    pergunta: Optional[str] = None


class InsightsResponse(BaseModel):
    resumo: str
    insights: list[str]


class InsightResponse(InsightsResponse):
    """Contrato padrao de insights."""


class StatusResponse(BaseModel):
    status: str


class ErrorBodyResponse(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorBodyResponse


class AnaliseResumoRequest(BaseModel):
    desconsiderar: bool = True
    va: bool = False
    vr: bool = False
    bianca: bool = False
    filippe: bool = False
    day_to_date: bool = False
    anome_referencia: Optional[int] = None


class AnaliseMetricasResponse(BaseModel):
    gasto_atual: float
    gasto_anterior: float
    gasto_3m_media: float
    delta_anterior: Optional[float] = None
    delta_atual: Optional[float] = None
    delta_3m: Optional[float] = None
    label_prev: str
    label_curr: str
    label_3m: str


class AnaliseResumoResponse(BaseModel):
    anome_referencia: int
    anomes_disponiveis: list[int]
    metricas: AnaliseMetricasResponse
    items: list[TransacaoResponse]
