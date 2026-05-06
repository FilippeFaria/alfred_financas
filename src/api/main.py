"""Aplicacao FastAPI para o backend do Alfred Financas."""

from fastapi import FastAPI, HTTPException, Query

from src.api.schemas import (
    CategoriaResponse,
    CriarTransacaoRequest,
    ExcluirTransacaoResponse,
    AnaliseResumoRequest,
    AnaliseResumoResponse,
    InsightsRequest,
    InsightResponse,
    SaldoResponse,
    StatusResponse,
    TransacaoResponse,
    TransacoesResponse,
)
from src.api.services import (
    criar_transacao,
    excluir_transacao_por_id,
    gerar_insights_basicos,
    listar_categorias,
    listar_transacoes,
    obter_resumo_analise,
    obter_saldo_por_conta,
)


app = FastAPI(
    title="Alfred Financas API",
    description="Backend FastAPI para operacoes financeiras do projeto Alfred Financas.",
    version="0.1.0",
)


@app.get("/", response_model=StatusResponse)
async def root() -> StatusResponse:
    return StatusResponse(status="online")


@app.get("/health", response_model=StatusResponse)
def healthcheck() -> StatusResponse:
    return StatusResponse(status="ok")


@app.get("/saldo", response_model=list[SaldoResponse])
def get_saldo() -> list[SaldoResponse]:
    return obter_saldo_por_conta()


@app.get("/transacoes", response_model=TransacoesResponse)
def get_transacoes(
    limite: int | None = Query(default=None, ge=1, le=5000),
) -> TransacoesResponse:
    items = listar_transacoes(limite=limite)
    return TransacoesResponse(total=len(items), items=items)


@app.post("/transacoes", response_model=TransacaoResponse)
def post_transacoes(payload: CriarTransacaoRequest) -> TransacaoResponse:
    try:
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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/transacoes/{transacao_id}", response_model=ExcluirTransacaoResponse)
def delete_transacao(transacao_id: int) -> ExcluirTransacaoResponse:
    return excluir_transacao_por_id(transacao_id)


@app.get("/categorias", response_model=CategoriaResponse)
def get_categorias() -> CategoriaResponse:
    return listar_categorias()


@app.post("/insights", response_model=InsightResponse)
def post_insights(payload: InsightsRequest) -> InsightResponse:
    return gerar_insights_basicos(payload.pergunta)


@app.post("/analise/resumo", response_model=AnaliseResumoResponse)
def post_analise_resumo(payload: AnaliseResumoRequest) -> AnaliseResumoResponse:
    return obter_resumo_analise(
        desconsiderar=payload.desconsiderar,
        va=payload.va,
        vr=payload.vr,
        bianca=payload.bianca,
        filippe=payload.filippe,
        day_to_date=payload.day_to_date,
        anome_referencia=payload.anome_referencia,
    )
