"""Aplicacao FastAPI para o backend do Alfred Financas."""

from fastapi import FastAPI, Query

from src.api.schemas import (
    CategoriasResponse,
    CriarTransacaoRequest,
    InsightsRequest,
    InsightsResponse,
    SaldoContaResponse,
    TransacaoResponse,
    TransacoesResponse,
)
from src.api.services import (
    criar_transacao,
    gerar_insights_basicos,
    listar_categorias,
    listar_transacoes,
    obter_saldo_por_conta,
)


app = FastAPI(
    title="Alfred Financas API",
    description="Backend FastAPI para operacoes financeiras do projeto Alfred Financas.",
    version="0.1.0",
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "online"}


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/saldo", response_model=list[SaldoContaResponse])
def get_saldo() -> list[SaldoContaResponse]:
    return obter_saldo_por_conta()


@app.get("/transacoes", response_model=TransacoesResponse)
def get_transacoes(
    limite: int | None = Query(default=None, ge=1, le=5000),
) -> TransacoesResponse:
    items = listar_transacoes(limite=limite)
    return TransacoesResponse(total=len(items), items=items)


@app.post("/transacoes", response_model=TransacaoResponse)
def post_transacoes(payload: CriarTransacaoRequest) -> TransacaoResponse:
    return criar_transacao(
        nome=payload.nome,
        tipo=payload.tipo,
        valor=payload.valor,
        categoria=payload.categoria,
        conta=payload.conta,
        data=payload.data,
        obs=payload.obs,
        tag=payload.tag,
        desconsiderar=payload.desconsiderar,
        parcelas=payload.parcelas,
    )


@app.get("/categorias", response_model=CategoriasResponse)
def get_categorias() -> CategoriasResponse:
    return listar_categorias()


@app.post("/insights", response_model=InsightsResponse)
def post_insights(payload: InsightsRequest) -> InsightsResponse:
    return gerar_insights_basicos(payload.pergunta)
