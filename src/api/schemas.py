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


class AtualizarTransacaoRequest(BaseModel):
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


class AtualizarTransacaoFlagsRequest(BaseModel):
    desconsiderar: Optional[bool] = None
    grande_transacao: Optional[bool] = None


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


class SerieMensalResponse(BaseModel):
    anome: int
    valor: float


class CategoriaDestaqueResponse(BaseModel):
    nome: str
    valor: float
    percentual_orcamento: Optional[float] = None


class UltimoLancamentoResponse(BaseModel):
    nome: str
    categoria: str
    valor: float
    data: str


class DashboardSnapshotResponse(BaseModel):
    status: str
    anome_referencia: int
    anomes_disponiveis: list[int]
    metricas: AnaliseMetricasResponse
    saldo_total: float
    saldos: list[SaldoContaResponse]
    gasto_mes: float
    orcamento_usado_percentual: float
    orcamento_usado_label: str
    categorias_destaque: list[CategoriaDestaqueResponse]
    ultimos_lancamentos: list[UltimoLancamentoResponse]
    serie_mensal: list[SerieMensalResponse]
    serie_categoria: list[SerieMensalResponse]


class OrcamentoCategoriaItem(BaseModel):
    categoria: str
    valor: float


class OrcamentoValoresResponse(BaseModel):
    data: Optional[str] = None
    items: list[OrcamentoCategoriaItem]


class SalvarOrcamentoRequest(BaseModel):
    items: list[OrcamentoCategoriaItem]


class CriarPendenciaTextoRequest(BaseModel):
    texto: str = Field(min_length=1)


class CriarPendenciaAudioRequest(BaseModel):
    caminho_arquivo: str = Field(min_length=1)


class PendingTransactionResponse(BaseModel):
    id: str
    user_id: str
    source: str
    raw_text: str
    transcription: Optional[str] = None
    suggested_payload: dict
    confidence: float = Field(ge=0.0, le=1.0)
    status: str
    created_at: datetime
    updated_at: datetime


class ConfirmarPendenciaRequest(BaseModel):
    payload_confirmado: Optional[dict] = None
    auto_confirmed: bool = False


class ConfirmarPendenciaResponse(BaseModel):
    pendencia: PendingTransactionResponse
    transacao: TransacaoResponse


class TransacaoSugeridaResponse(BaseModel):
    data: str | None = None
    tipo: str | None = None
    categoria: str | None = None
    conta: str | None = None
    conta_destino: str | None = None
    nome: str | None = None
    valor: float | None = None
    origem: str
    descricao_original: str
    transcricao: str | None = None
    confianca: float = Field(ge=0.0, le=1.0)
    campos_incertos: list[str] = Field(default_factory=list)
    justificativa: str | None = None


class TextoParaTransacaoResponse(BaseModel):
    pending_transaction_id: str
    transacao_sugerida: TransacaoSugeridaResponse


class AudioParaTransacaoResponse(BaseModel):
    pending_transaction_id: str
    transcricao: str
    transacao_sugerida: TransacaoSugeridaResponse


class ConfirmarTransacaoPendenteRequest(BaseModel):
    data: datetime | None = None
    tipo: str | None = None
    categoria: str | None = None
    conta: str | None = None
    nome: str | None = None
    valor: float | None = None
    obs: str | None = None
    tag: str | None = None
    desconsiderar: bool | None = None
    parcelas: int | None = Field(default=None, ge=1)
