"""Aplicacao FastAPI para o backend do Alfred Financas."""

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import UserContext, auth_context_middleware, get_current_user_optional
from src.api.errors import ApiServiceError, register_exception_handlers
from src.api.schemas import (
    AtualizarTransacaoFlagsRequest,
    AtualizarTransacaoRequest,
    CategoriaResponse,
    ConfirmarPendenciaRequest,
    ConfirmarPendenciaResponse,
    CriarPendenciaAudioRequest,
    CriarPendenciaTextoRequest,
    CriarTransacaoRequest,
    PendingTransactionResponse,
    ExcluirTransacaoResponse,
    AnaliseResumoRequest,
    AnaliseResumoResponse,
    InsightsRequest,
    InsightResponse,
    SaldoResponse,
    StatusResponse,
    DashboardSnapshotResponse,
    OrcamentoValoresResponse,
    SalvarOrcamentoRequest,
    TransacaoResponse,
    TransacoesResponse,
)
from src.api.services import (
    atualizar_flags_transacao_por_id,
    atualizar_transacao_por_id,
    criar_transacao,
    excluir_transacao_por_id,
    gerar_insights_basicos,
    listar_categorias,
    listar_transacoes_paginado,
    obter_resumo_analise,
    obter_saldo_por_conta,
    obter_dashboard_snapshot_mobile,
    obter_orcamento_valores,
    salvar_orcamento_valores,
)
from src.ai.services import criar_pendencia_por_audio, criar_pendencia_por_texto
from src.database.connection import init_db
from src.services.pending_transaction_service import (
    confirmar_transacao_pendente,
    ignorar_transacao_pendente,
    listar_transacoes_pendentes,
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


@app.on_event("startup")
def startup_db() -> None:
    init_db()


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


@app.put("/transacoes/{transacao_id}", response_model=TransacaoResponse)
def put_transacao(
    transacao_id: int,
    payload: AtualizarTransacaoRequest,
    user_context: UserContext = Depends(get_current_user_optional),
) -> TransacaoResponse:
    return atualizar_transacao_por_id(
        transacao_id,
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


@app.patch("/transacoes/{transacao_id}/flags", response_model=ExcluirTransacaoResponse)
def patch_transacao_flags(
    transacao_id: int,
    payload: AtualizarTransacaoFlagsRequest,
    user_context: UserContext = Depends(get_current_user_optional),
) -> ExcluirTransacaoResponse:
    return atualizar_flags_transacao_por_id(
        transacao_id,
        desconsiderar=payload.desconsiderar,
        grande_transacao=payload.grande_transacao,
    )


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


@app.get("/mobile/dashboard_snapshot", response_model=DashboardSnapshotResponse)
def get_mobile_dashboard_snapshot(
    desconsiderar: bool = Query(default=True),
    va: bool = Query(default=False),
    vr: bool = Query(default=False),
    bianca: bool = Query(default=False),
    filippe: bool = Query(default=False),
    day_to_date: bool = Query(default=True),
    anome_referencia: int | None = Query(default=None),
    categoria: str | None = Query(default=None),
    meses_historico: int = Query(default=6, ge=3, le=12),
    user_context: UserContext = Depends(get_current_user_optional),
) -> DashboardSnapshotResponse:
    payload = obter_dashboard_snapshot_mobile(
        desconsiderar=desconsiderar,
        va=va,
        vr=vr,
        bianca=bianca,
        filippe=filippe,
        day_to_date=day_to_date,
        anome_referencia=anome_referencia,
        categoria=categoria,
        meses_historico=meses_historico,
    )
    return DashboardSnapshotResponse(**payload)


@app.get("/orcamento/valores", response_model=OrcamentoValoresResponse)
def get_orcamento_valores(
    user_context: UserContext = Depends(get_current_user_optional),
) -> OrcamentoValoresResponse:
    return OrcamentoValoresResponse(**obter_orcamento_valores())


@app.post("/orcamento/valores", response_model=OrcamentoValoresResponse)
def post_orcamento_valores(
    payload: SalvarOrcamentoRequest,
    user_context: UserContext = Depends(get_current_user_optional),
) -> OrcamentoValoresResponse:
    return OrcamentoValoresResponse(**salvar_orcamento_valores(items=[item.model_dump() for item in payload.items]))


@app.post("/ia/pendencias/texto", response_model=PendingTransactionResponse)
def post_ia_pendencia_texto(
    payload: CriarPendenciaTextoRequest,
    user_context: UserContext = Depends(get_current_user_optional),
) -> PendingTransactionResponse:
    try:
        pendencia = criar_pendencia_por_texto(payload.texto)
        return PendingTransactionResponse(**pendencia.__dict__)
    except ValueError as exc:
        raise ApiServiceError(code="DADOS_INVALIDOS", message=str(exc), status_code=400) from exc


@app.post("/ia/pendencias/audio", response_model=PendingTransactionResponse)
def post_ia_pendencia_audio(
    payload: CriarPendenciaAudioRequest,
    user_context: UserContext = Depends(get_current_user_optional),
) -> PendingTransactionResponse:
    try:
        pendencia = criar_pendencia_por_audio(payload.caminho_arquivo)
        return PendingTransactionResponse(**pendencia.__dict__)
    except ValueError as exc:
        raise ApiServiceError(code="DADOS_INVALIDOS", message=str(exc), status_code=400) from exc


@app.get("/ia/pendencias", response_model=list[PendingTransactionResponse])
def get_ia_pendencias(
    status: str | None = Query(default="pending"),
    user_context: UserContext = Depends(get_current_user_optional),
) -> list[PendingTransactionResponse]:
    try:
        pendencias = listar_transacoes_pendentes(status=status)
        return [PendingTransactionResponse(**item.__dict__) for item in pendencias]
    except ValueError as exc:
        raise ApiServiceError(code="DADOS_INVALIDOS", message=str(exc), status_code=400) from exc


@app.post("/ia/pendencias/{pending_id}/confirmar", response_model=ConfirmarPendenciaResponse)
def post_ia_confirmar_pendencia(
    pending_id: str,
    payload: ConfirmarPendenciaRequest,
    user_context: UserContext = Depends(get_current_user_optional),
) -> ConfirmarPendenciaResponse:
    try:
        pendencia, transacao = confirmar_transacao_pendente(
            pending_id=pending_id,
            payload_confirmado=payload.payload_confirmado,
            auto_confirmed=payload.auto_confirmed,
        )
        return ConfirmarPendenciaResponse(
            pendencia=PendingTransactionResponse(**pendencia.__dict__),
            transacao=TransacaoResponse(**transacao),
        )
    except ValueError as exc:
        raise ApiServiceError(code="DADOS_INVALIDOS", message=str(exc), status_code=400) from exc


@app.post("/ia/pendencias/{pending_id}/ignorar", response_model=PendingTransactionResponse)
def post_ia_ignorar_pendencia(
    pending_id: str,
    user_context: UserContext = Depends(get_current_user_optional),
) -> PendingTransactionResponse:
    try:
        pendencia = ignorar_transacao_pendente(pending_id=pending_id)
        return PendingTransactionResponse(**pendencia.__dict__)
    except ValueError as exc:
        raise ApiServiceError(code="DADOS_INVALIDOS", message=str(exc), status_code=400) from exc
