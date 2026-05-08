"""Aplicacao FastAPI para o backend do Alfred Financas."""

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import UserContext, auth_context_middleware, get_current_user_optional
from src.api.errors import register_exception_handlers
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
    listar_transacoes_paginado,
    obter_resumo_analise,
    obter_saldo_por_conta,
)


app = FastAPI(
    title="Alfred Financas API",
    description="Backend FastAPI para operacoes financeiras do projeto Alfred Financas.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)
app.middleware("http")(auth_context_middleware)


@app.get("/", response_model=StatusResponse)
async def root(user_context: UserContext = Depends(get_current_user_optional)) -> StatusResponse:
    return StatusResponse(status="online")


@app.get("/health", response_model=StatusResponse)
def healthcheck(user_context: UserContext = Depends(get_current_user_optional)) -> StatusResponse:
    return StatusResponse(status="ok")


@app.get("/saldo", response_model=list[SaldoResponse])
def get_saldo(user_context: UserContext = Depends(get_current_user_optional)) -> list[SaldoResponse]:
    return obter_saldo_por_conta()


@app.get("/transacoes", response_model=TransacoesResponse)
def get_transacoes(
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=50, ge=1, le=500),
    data_inicio: str | None = Query(default=None),
    data_fim: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    conta: str | None = Query(default=None),
    tipo: str | None = Query(default=None),
    user_context: UserContext = Depends(get_current_user_optional),
) -> TransacoesResponse:
    payload = listar_transacoes_paginado(
        pagina=pagina,
        limite=limite,
        data_inicio=data_inicio,
        data_fim=data_fim,
        categoria=categoria,
        conta=conta,
        tipo=tipo,
    )
    return TransacoesResponse(**payload)


@app.post("/transacoes", response_model=TransacaoResponse)
def post_transacoes(
    payload: CriarTransacaoRequest,
    user_context: UserContext = Depends(get_current_user_optional),
) -> TransacaoResponse:
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


@app.delete("/transacoes/{transacao_id}", response_model=ExcluirTransacaoResponse)
def delete_transacao(
    transacao_id: int,
    user_context: UserContext = Depends(get_current_user_optional),
) -> ExcluirTransacaoResponse:
    return excluir_transacao_por_id(transacao_id)


@app.get("/categorias", response_model=CategoriaResponse)
def get_categorias(user_context: UserContext = Depends(get_current_user_optional)) -> CategoriaResponse:
    return listar_categorias()


@app.post("/insights", response_model=InsightResponse)
def post_insights(
    payload: InsightsRequest,
    user_context: UserContext = Depends(get_current_user_optional),
) -> InsightResponse:
    return gerar_insights_basicos(payload.pergunta)


@app.post("/analise/resumo", response_model=AnaliseResumoResponse)
def post_analise_resumo(
    payload: AnaliseResumoRequest,
    user_context: UserContext = Depends(get_current_user_optional),
) -> AnaliseResumoResponse:
    return obter_resumo_analise(
        desconsiderar=payload.desconsiderar,
        va=payload.va,
        vr=payload.vr,
        bianca=payload.bianca,
        filippe=payload.filippe,
        day_to_date=payload.day_to_date,
        anome_referencia=payload.anome_referencia,
    )
