"""Servicos da camada de API com PostgreSQL como fonte principal."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import json
import logging
import os
from pathlib import Path

import pandas as pd

from src.api.errors import ApiServiceError
from src.analytics.calculations import adicionar_anomes, calcular_despesa_total, calcular_saldo
from src.config import CATEGORIAS_DESPESA, CATEGORIAS_INVESTIMENTO, CATEGORIAS_RECEITA
from src.database.connection import SessionLocal
from src.database.repositories import (
    AccountRepository,
    CategoryRepository,
    TransactionRepository,
    UserRepository,
)
from src.services.google_sheets import get_sheet, read_sheet, write_sheet


ROOT_PATH = Path(__file__).resolve().parents[2]
DATE_FORMAT = "%d/%m/%Y %H:%M"
LOGGER = logging.getLogger("alfred.api.services")
FALLBACK_ENABLED = os.getenv("ALFRED_SHEETS_FALLBACK_ENABLED", "true").strip().lower() in {"1", "true", "yes"}
DUAL_WRITE_ENABLED = os.getenv("ALFRED_DUAL_WRITE_ENABLED", "false").strip().lower() in {"1", "true", "yes"}


def _log_error(event: str, **fields) -> None:
    LOGGER.error(json.dumps({"event": event, **fields}, ensure_ascii=False, default=str))


def _normalizar_datas(df: pd.DataFrame, colunas: list[str] | None = None) -> pd.DataFrame:
    if colunas is None:
        colunas = ["Data", "Data origem", "Data Criacao"]
    df = df.copy()
    for col in colunas:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="mixed", dayfirst=True, errors="coerce")
            df[col] = df[col].dt.strftime(DATE_FORMAT)
    return df


def _uuid_to_legacy_int(value) -> int:
    return int(value.int % 2_000_000_000)


def _map_tx_to_api_dict(tx) -> dict:
    legacy_id = tx.legacy_id if tx.legacy_id is not None else _uuid_to_legacy_int(tx.id)
    return {
        "id": int(legacy_id),
        "nome": tx.nome,
        "tipo": tx.tipo,
        "valor": float(tx.valor),
        "categoria": tx.category.nome if tx.category else "",
        "conta": tx.account.nome if tx.account else "",
        "data": tx.data.strftime(DATE_FORMAT) if tx.data else "",
        "obs": tx.observacao or "",
        "tag": tx.tag,
        "desconsiderar": bool(tx.desconsiderar),
        "data_criacao": tx.created_at.strftime(DATE_FORMAT) if tx.created_at else None,
        "parcela": tx.parcela,
        "data_origem": tx.data_origem.strftime(DATE_FORMAT) if tx.data_origem else None,
    }


def carregar_transacoes_df_sheets() -> pd.DataFrame:
    df = read_sheet(str(ROOT_PATH))
    if df.empty:
        return df
    if "Valor" in df.columns:
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0.0)
    if "desconsiderar" in df.columns:
        df["desconsiderar"] = df["desconsiderar"].replace("TRUE", True).replace("FALSE", False).fillna(False).astype(bool)
    if "Categoria" in df.columns:
        df["Categoria"] = df["Categoria"].astype(str).str.replace("TV.Internet.Telefone", "Assinaturas", regex=False)
    return _normalizar_datas(df)


def listar_transacoes(limite: int | None = None) -> list[dict]:
    try:
        with SessionLocal() as db:
            user = UserRepository(db).get_or_create_default()
            items = TransactionRepository(db).list_all(user_id=user.id, limit=limite)
            return [_map_tx_to_api_dict(item) for item in items]
    except Exception as exc:
        LOGGER.exception("Falha na leitura PostgreSQL em listar_transacoes")
        _log_error("postgres_read_error", error_type=type(exc).__name__, error=str(exc))
        if not FALLBACK_ENABLED:
            raise ApiServiceError(
                code="FALHA_POSTGRES",
                message="Falha ao ler dados no PostgreSQL.",
                status_code=503,
                details={"error_type": type(exc).__name__, "error": str(exc)},
            ) from exc

    df = carregar_transacoes_df_sheets()
    if df.empty:
        return []
    df = df.copy()
    df["_data_ord"] = pd.to_datetime(df["Data"], format=DATE_FORMAT, errors="coerce")
    df = df.sort_values("_data_ord", ascending=False, na_position="last").drop(columns=["_data_ord"])
    if limite:
        df = df.head(limite)
    return [mapear_linha_para_transacao(row) for row in df.to_dict(orient="records")]


def listar_transacoes_paginado(
    *,
    pagina: int = 1,
    limite: int = 50,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    categoria: str | None = None,
    conta: str | None = None,
    tipo: str | None = None,
) -> dict:
    pagina = max(1, int(pagina))
    limite = max(1, min(int(limite), 500))
    offset = (pagina - 1) * limite
    data_inicio_obj = pd.to_datetime(data_inicio, errors="coerce").date() if data_inicio else None
    data_fim_obj = pd.to_datetime(data_fim, errors="coerce").date() if data_fim else None

    try:
        with SessionLocal() as db:
            user = UserRepository(db).get_or_create_default()
            tx_repo = TransactionRepository(db)
            total = tx_repo.count_filtered(
                user_id=user.id,
                data_inicio=data_inicio_obj,
                data_fim=data_fim_obj,
                categoria=categoria,
                conta=conta,
                tipo=tipo,
            )
            items = tx_repo.list_filtered(
                user_id=user.id,
                offset=offset,
                limit=limite,
                data_inicio=data_inicio_obj,
                data_fim=data_fim_obj,
                categoria=categoria,
                conta=conta,
                tipo=tipo,
            )
            payload = [_map_tx_to_api_dict(item) for item in items]
            total_paginas = max(1, (total + limite - 1) // limite) if total > 0 else 1
            return {
                "total": total,
                "pagina": pagina,
                "limite": limite,
                "total_paginas": total_paginas,
                "items": payload,
            }
    except Exception as exc:
        LOGGER.exception("Falha na leitura PostgreSQL em listar_transacoes_paginado")
        _log_error("postgres_read_error", error_type=type(exc).__name__, error=str(exc))
        if not FALLBACK_ENABLED:
            raise ApiServiceError(
                code="FALHA_POSTGRES",
                message="Falha ao ler dados no PostgreSQL.",
                status_code=503,
                details={"error_type": type(exc).__name__, "error": str(exc)},
            ) from exc

    df = carregar_transacoes_df_sheets()
    if df.empty:
        return {"total": 0, "pagina": pagina, "limite": limite, "total_paginas": 1, "items": []}

    df = df.copy()
    df["_data_ord"] = pd.to_datetime(df["Data"], format=DATE_FORMAT, errors="coerce")
    df = df.sort_values("_data_ord", ascending=False, na_position="last")

    if data_inicio_obj is not None:
        df = df[df["_data_ord"] >= pd.Timestamp(data_inicio_obj)]
    if data_fim_obj is not None:
        df = df[df["_data_ord"] <= pd.Timestamp(data_fim_obj) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]
    if categoria:
        df = df[df["Categoria"] == categoria]
    if conta:
        df = df[df["Conta"] == conta]
    if tipo:
        df = df[df["Tipo"] == tipo]

    total = len(df)
    inicio = offset
    fim = offset + limite
    page_df = df.iloc[inicio:fim].drop(columns=["_data_ord"], errors="ignore")
    total_paginas = max(1, (total + limite - 1) // limite) if total > 0 else 1

    return {
        "total": total,
        "pagina": pagina,
        "limite": limite,
        "total_paginas": total_paginas,
        "items": [mapear_linha_para_transacao(row) for row in page_df.to_dict(orient="records")],
    }


def obter_saldo_por_conta() -> list[dict]:
    transacoes = listar_transacoes()
    if not transacoes:
        return []
    df = pd.DataFrame(
        [{"Conta": t["conta"], "Valor": t["valor"]} for t in transacoes]
    )
    saldo_series = df.groupby("Conta")["Valor"].sum()
    return [{"conta": str(c), "saldo": float(v)} for c, v in saldo_series.sort_index().items()]


def mapear_linha_para_transacao(linha: dict) -> dict:
    data_valor = linha.get("Data")
    data_normalizada = pd.to_datetime(data_valor, format="mixed", dayfirst=True, errors="coerce")
    data_formatada = data_normalizada.strftime(DATE_FORMAT) if pd.notna(data_normalizada) else ""
    return {
        "id": int(linha.get("id", 0)),
        "nome": str(linha.get("Nome", "")),
        "tipo": str(linha.get("Tipo", "")),
        "valor": float(linha.get("Valor", 0.0)),
        "categoria": str(linha.get("Categoria", "")),
        "conta": str(linha.get("Conta", "")),
        "data": data_formatada,
        "obs": str(linha.get("Obs", "")),
        "tag": linha.get("TAG"),
        "desconsiderar": bool(linha.get("desconsiderar", False)),
        "data_criacao": str(linha.get("Data Criacao")) if pd.notna(linha.get("Data Criacao")) and str(linha.get("Data Criacao")).strip() else None,
        "parcela": int(linha.get("Parcela")) if pd.notna(linha.get("Parcela")) and str(linha.get("Parcela")).strip() else None,
        "data_origem": str(linha.get("Data origem")) if pd.notna(linha.get("Data origem")) and str(linha.get("Data origem")).strip() else None,
    }


def listar_categorias() -> dict[str, list[str]]:
    return {"despesa": CATEGORIAS_DESPESA, "receita": CATEGORIAS_RECEITA, "investimento": CATEGORIAS_INVESTIMENTO}


def _validar_categoria_por_tipo(tipo: str, categoria: str) -> None:
    mapa = {
        "Despesa": CATEGORIAS_DESPESA,
        "Receita": CATEGORIAS_RECEITA,
        "Investimento": CATEGORIAS_INVESTIMENTO,
        "Transferência": ["Transferência"],
        "Transferencia": ["Transferência", "Transferencia"],
    }
    if tipo not in mapa or categoria not in mapa[tipo]:
        raise ApiServiceError(code="DADOS_INVALIDOS", message=f"Categoria '{categoria}' invalida para tipo '{tipo}'.", status_code=400)


def criar_transacao(*, nome: str, tipo: str, valor: float, categoria: str, conta: str, data: datetime, obs: str = "", tag: str | None = None, desconsiderar: bool = False, parcelas: int | None = None) -> dict:
    _validar_categoria_por_tipo(tipo, categoria)
    if tipo == "Despesa" and valor > 0:
        raise ApiServiceError(code="DADOS_INVALIDOS", message="Despesa deve possuir valor negativo.", status_code=400)
    if tipo in {"Receita", "Investimento"} and valor < 0:
        raise ApiServiceError(code="DADOS_INVALIDOS", message=f"{tipo} deve possuir valor positivo.", status_code=400)

    try:
        with SessionLocal() as db:
            user_repo = UserRepository(db)
            account_repo = AccountRepository(db)
            category_repo = CategoryRepository(db)
            tx_repo = TransactionRepository(db)

            user = user_repo.get_or_create_default()
            account = account_repo.get_or_create(user_id=user.id, nome=conta)
            cat = category_repo.get_or_create(user_id=user.id, nome=categoria, tipo=tipo)
            legacy_id = tx_repo.get_next_legacy_id(user_id=user.id)
            total_parcelas = int(parcelas) if parcelas and parcelas > 1 else 1
            item = None
            for i in range(total_parcelas):
                data_item = (pd.Timestamp(data) + pd.DateOffset(months=i)).to_pydatetime()
                parcela_item = (i + 1) if total_parcelas > 1 else None
                data_origem_item = data if total_parcelas > 1 else None
                item = tx_repo.create(
                    user_id=user.id,
                    account_id=account.id,
                    category_id=cat.id,
                    legacy_id=legacy_id,
                    nome=nome,
                    tipo=tipo,
                    valor=Decimal(str(valor)),
                    data=data_item,
                    observacao=obs or None,
                    tag=tag,
                    desconsiderar=desconsiderar,
                    parcela=parcela_item,
                    data_origem=data_origem_item,
                )
            db.commit()
            if item is None:
                raise ApiServiceError(code="DADOS_INVALIDOS", message="Nenhuma transacao criada.", status_code=400)
            db.refresh(item)
            resultado = _map_tx_to_api_dict(item)
    except Exception as exc:
        LOGGER.exception("Falha ao persistir transacao no PostgreSQL")
        _log_error("postgres_write_error", error_type=type(exc).__name__, error=str(exc))
        raise ApiServiceError(
            code="FALHA_POSTGRES",
            message="Falha ao persistir transacao no PostgreSQL.",
            status_code=503,
            details={"error_type": type(exc).__name__, "error": str(exc)},
        ) from exc

    if DUAL_WRITE_ENABLED:
        try:
            df = carregar_transacoes_df_sheets()
            novo = pd.DataFrame([{
                "id": resultado["id"],
                "Nome": resultado["nome"],
                "Tipo": resultado["tipo"],
                "Valor": resultado["valor"],
                "Categoria": resultado["categoria"],
                "Conta": resultado["conta"],
                "Data": resultado["data"],
                "Obs": resultado["obs"],
                "TAG": resultado["tag"],
                "desconsiderar": resultado["desconsiderar"],
                "Parcela": resultado["parcela"],
                "Data origem": resultado["data_origem"] or "",
                "Data Criacao": resultado["data_criacao"] or "",
            }])
            df_final = pd.concat([df, novo], ignore_index=True) if not df.empty else novo
            sheet = get_sheet(str(ROOT_PATH))
            write_sheet(sheet, _normalizar_datas(df_final))
        except Exception as exc:
            _log_error("dual_write_warning", error_type=type(exc).__name__)
    return resultado


def excluir_transacao_por_id(transacao_id: int) -> dict:
    try:
        with SessionLocal() as db:
            user = UserRepository(db).get_or_create_default()
            removidos = TransactionRepository(db).delete_by_legacy_id(user_id=user.id, legacy_id=transacao_id)
            db.commit()
            return {"id": transacao_id, "removidos": removidos, "mensagem": f"{removidos} registro(s) removido(s) para o id {transacao_id}."}
    except Exception as exc:
        _log_error("postgres_delete_error", error_type=type(exc).__name__)
        raise ApiServiceError(code="FALHA_POSTGRES", message="Falha ao excluir transacao.", status_code=503) from exc


def _aplicar_filtros_analise(df: pd.DataFrame, *, desconsiderar: bool, va: bool, vr: bool, bianca: bool, filippe: bool) -> pd.DataFrame:
    from src.config import GRANDES_TRANSACOES
    df_temp = df.copy()
    if desconsiderar and "id" in df_temp.columns:
        df_temp = df_temp[~df_temp["id"].isin(GRANDES_TRANSACOES)]
    if va:
        df_temp = df_temp[df_temp["Conta"] != "VA"]
    if vr:
        df_temp = df_temp[df_temp["Conta"] != "VR"]
    if bianca:
        contas = ["Cartão Bianca", "Inter", "Itaú CC", "Cartão Nath", "VA", "VR"]
        df_temp = df_temp[df_temp["Conta"].isin(contas)].copy()
        df_temp.loc[df_temp["Conta"].isin(["Itaú CC", "Cartão Nath", "VA", "VR"]), "Valor"] *= 0.3
    elif filippe:
        contas = ["Cartão Filippe", "Nubank", "Itaú CC", "Cartão Nath", "VA", "VR"]
        df_temp = df_temp[df_temp["Conta"].isin(contas)].copy()
        df_temp.loc[df_temp["Conta"].isin(["Itaú CC", "Cartão Nath", "VA", "VR"]), "Valor"] *= 0.7
    return df_temp


def obter_resumo_analise(*, desconsiderar: bool = True, va: bool = False, vr: bool = False, bianca: bool = False, filippe: bool = False, day_to_date: bool = False, anome_referencia: int | None = None) -> dict:
    items = listar_transacoes()
    if not items:
        return {"anome_referencia": int(datetime.now().strftime("%Y%m")), "anomes_disponiveis": [], "metricas": {"gasto_atual": 0.0, "gasto_anterior": 0.0, "gasto_3m_media": 0.0, "delta_anterior": None, "delta_atual": None, "delta_3m": None, "label_prev": "", "label_curr": "", "label_3m": ""}, "items": []}
    df = pd.DataFrame([{"id": i["id"], "Nome": i["nome"], "Tipo": i["tipo"], "Valor": i["valor"], "Categoria": i["categoria"], "Conta": i["conta"], "Data": i["data"], "Obs": i["obs"], "TAG": i["tag"], "desconsiderar": i["desconsiderar"], "Parcela": i["parcela"], "Data origem": i["data_origem"], "Data Criacao": i["data_criacao"]} for i in items])
    df = _normalizar_datas(df)
    df_temp = _aplicar_filtros_analise(df, desconsiderar=desconsiderar, va=va, vr=vr, bianca=bianca, filippe=filippe)
    df_temp = adicionar_anomes(df_temp)
    anomes_disponiveis = sorted([int(v) for v in df_temp["anomes"].dropna().astype(str).unique() if str(v).isdigit()])
    anome_base = anome_referencia or (anomes_disponiveis[-1] if anomes_disponiveis else int(datetime.now().strftime("%Y%m")))
    if day_to_date and not df_temp.empty:
        data_max = df_temp[(df_temp["anomes"] == str(anome_base)) & (df_temp["Parcela"].isna())]["Data"].dt.day.max()
        if pd.notna(data_max):
            df_temp = df_temp[df_temp["Data"].dt.day <= int(data_max)]
    df_despesa = df_temp[(df_temp["desconsiderar"] == False) & (df_temp["Tipo"] == "Despesa")]
    metricas = calcular_despesa_total(df_despesa, int(anome_base))
    return {"anome_referencia": int(anome_base), "anomes_disponiveis": anomes_disponiveis, "metricas": {"gasto_atual": float(metricas["gasto_atual"]), "gasto_anterior": float(metricas["gasto_anterior"]), "gasto_3m_media": float(metricas["gasto_3m_media"]), "delta_anterior": metricas["delta_anterior"], "delta_atual": metricas["delta_atual"], "delta_3m": metricas["delta_3m"], "label_prev": metricas["label_prev"], "label_curr": metricas["label_curr"], "label_3m": metricas["label_3m"]}, "items": [mapear_linha_para_transacao(row) for row in df_temp.to_dict(orient="records")]}


def gerar_insights_basicos(pergunta: str | None) -> dict:
    items = listar_transacoes()
    if not items:
        return {"resumo": "Nenhuma transacao encontrada.", "insights": ["Base vazia. Cadastre transacoes para gerar insights."]}
    saldo = obter_saldo_por_conta()
    saldo_total = round(sum(item["saldo"] for item in saldo), 2)
    df = pd.DataFrame([{"Tipo": i["tipo"], "Data": i["data"], "Categoria": i["categoria"], "Valor": i["valor"]} for i in items])
    df["Data"] = pd.to_datetime(df["Data"], format=DATE_FORMAT, errors="coerce")
    inicio_mes = pd.Timestamp(date.today().replace(day=1))
    fim_mes = inicio_mes + pd.DateOffset(months=1)
    despesas_mes = df[(df["Tipo"] == "Despesa") & (df["Data"] >= inicio_mes) & (df["Data"] < fim_mes)]
    top_categoria = "Sem despesas no mes"
    total_top_categoria = 0.0
    if not despesas_mes.empty:
        categoria_serie = despesas_mes.groupby("Categoria")["Valor"].sum().abs().sort_values(ascending=False)
        top_categoria = str(categoria_serie.index[0])
        total_top_categoria = float(round(categoria_serie.iloc[0], 2))
    texto_pergunta = pergunta.strip() if pergunta else "Sem pergunta especifica."
    return {"resumo": f"Saldo total atual: R$ {saldo_total:.2f}.", "insights": [f"Maior categoria de despesa no mes: {top_categoria} (R$ {total_top_categoria:.2f}).", f"Total de contas com saldo calculado: {len(saldo)}.", f"Contexto da solicitacao: {texto_pergunta}"]}


def _serie_totais_despesa(df: pd.DataFrame, anomes: list[int]) -> list[dict]:
    serie: list[dict] = []
    for anome in anomes:
        total = df[(df["Tipo"] == "Despesa") & (df["anomes"] == str(anome))]["Valor"].abs().sum()
        serie.append({"anome": int(anome), "valor": float(total)})
    return serie


def _serie_categoria_despesa(df: pd.DataFrame, anomes: list[int], categoria: str | None) -> list[dict]:
    if not categoria:
        return []
    serie: list[dict] = []
    categoria_limpa = categoria.strip()
    for anome in anomes:
        filtro = (
            (df["Tipo"] == "Despesa")
            & (df["anomes"] == str(anome))
            & (df["Categoria"].fillna("Sem categoria").replace("", "Sem categoria") == categoria_limpa)
        )
        total = df[filtro]["Valor"].abs().sum()
        serie.append({"anome": int(anome), "valor": float(total)})
    return serie


def obter_dashboard_snapshot_mobile(
    *,
    desconsiderar: bool = True,
    va: bool = False,
    vr: bool = False,
    bianca: bool = False,
    filippe: bool = False,
    day_to_date: bool = False,
    anome_referencia: int | None = None,
    categoria: str | None = None,
    meses_historico: int = 6,
) -> dict:
    status = "ok"
    items = listar_transacoes()
    if not items:
        anome_atual = int(datetime.now().strftime("%Y%m"))
        return {
            "status": status,
            "anome_referencia": anome_atual,
            "anomes_disponiveis": [],
            "metricas": {
                "gasto_atual": 0.0,
                "gasto_anterior": 0.0,
                "gasto_3m_media": 0.0,
                "delta_anterior": None,
                "delta_atual": None,
                "delta_3m": None,
                "label_prev": "",
                "label_curr": "",
                "label_3m": "",
            },
            "saldo_total": 0.0,
            "saldos": [],
            "gasto_mes": 0.0,
            "orcamento_usado_percentual": 0.0,
            "orcamento_usado_label": "Base media 3 meses: R$ 1.00",
            "categorias_destaque": [],
            "ultimos_lancamentos": [],
            "serie_mensal": [],
            "serie_categoria": [],
        }

    df = pd.DataFrame(
        [
            {
                "id": i["id"],
                "Nome": i["nome"],
                "Tipo": i["tipo"],
                "Valor": i["valor"],
                "Categoria": i["categoria"],
                "Conta": i["conta"],
                "Data": i["data"],
                "Obs": i["obs"],
                "TAG": i["tag"],
                "desconsiderar": i["desconsiderar"],
                "Parcela": i["parcela"],
                "Data origem": i["data_origem"],
                "Data Criacao": i["data_criacao"],
            }
            for i in items
        ]
    )
    df = _normalizar_datas(df)
    df = adicionar_anomes(df)

    saldos_serie = df.groupby("Conta")["Valor"].sum().sort_index()
    saldos = [{"conta": str(conta), "saldo": float(valor)} for conta, valor in saldos_serie.items()]
    saldo_total = float(saldos_serie.sum()) if not saldos_serie.empty else 0.0

    df_temp = _aplicar_filtros_analise(df, desconsiderar=desconsiderar, va=va, vr=vr, bianca=bianca, filippe=filippe)
    anomes_disponiveis = sorted([int(v) for v in df_temp["anomes"].dropna().astype(str).unique() if str(v).isdigit()])
    anome_base = anome_referencia or (anomes_disponiveis[-1] if anomes_disponiveis else int(datetime.now().strftime("%Y%m")))

    if day_to_date and not df_temp.empty:
        data_max = df_temp[(df_temp["anomes"] == str(anome_base)) & (df_temp["Parcela"].isna())]["Data"].dt.day.max()
        if pd.notna(data_max):
            df_temp = df_temp[df_temp["Data"].dt.day <= int(data_max)]

    df_despesa = df_temp[(df_temp["desconsiderar"] == False) & (df_temp["Tipo"] == "Despesa")]
    metricas = calcular_despesa_total(df_despesa, int(anome_base))
    gasto_mes = float(metricas["gasto_atual"])
    referencia_orcamento = float(metricas["gasto_3m_media"]) if float(metricas["gasto_3m_media"]) > 0 else 1.0
    orcamento_usado_percentual = float((gasto_mes / referencia_orcamento) * 100)

    # Visoes do dashboard devem refletir explicitamente o mes selecionado.
    df_mes = df_temp[df_temp["anomes"] == str(anome_base)].copy()
    df_despesa_mes = df_mes[(df_mes["desconsiderar"] == False) & (df_mes["Tipo"] == "Despesa")].copy()

    categorias_serie = (
        df_despesa_mes.assign(_categoria=df_despesa_mes["Categoria"].fillna("Sem categoria").replace("", "Sem categoria"))
        .groupby("_categoria")["Valor"]
        .sum()
        .abs()
        .sort_values(ascending=False)
    )
    categorias_destaque = [
        {"nome": str(nome), "valor": float(valor)} for nome, valor in categorias_serie.head(6).items()
    ]

    ultimos_df = df_mes.copy()
    ultimos_df["_data_ord"] = pd.to_datetime(ultimos_df["Data"], format=DATE_FORMAT, errors="coerce")
    ultimos_df = ultimos_df.sort_values("_data_ord", ascending=False, na_position="last")
    ultimos_lancamentos = [
        {
            "nome": str(row.get("Nome", "")),
            "categoria": str(row.get("Categoria", "")),
            "valor": float(row.get("Valor", 0.0)),
            "data": row["_data_ord"].strftime(DATE_FORMAT) if pd.notna(row["_data_ord"]) else "",
        }
        for _, row in ultimos_df.head(5).iterrows()
    ]

    limite_historico = max(3, min(int(meses_historico or 6), 12))
    meses_visiveis = sorted([m for m in anomes_disponiveis if m <= int(anome_base)])
    if not meses_visiveis:
        meses_visiveis = [int(anome_base)]
    if len(meses_visiveis) > limite_historico:
        meses_visiveis = meses_visiveis[-limite_historico:]

    serie_mensal = _serie_totais_despesa(df_temp, meses_visiveis)
    serie_categoria = _serie_categoria_despesa(df_temp, meses_visiveis, categoria)

    return {
        "status": status,
        "anome_referencia": int(anome_base),
        "anomes_disponiveis": anomes_disponiveis,
        "metricas": {
            "gasto_atual": gasto_mes,
            "gasto_anterior": float(metricas["gasto_anterior"]),
            "gasto_3m_media": float(metricas["gasto_3m_media"]),
            "delta_anterior": metricas["delta_anterior"],
            "delta_atual": metricas["delta_atual"],
            "delta_3m": metricas["delta_3m"],
            "label_prev": metricas["label_prev"],
            "label_curr": metricas["label_curr"],
            "label_3m": metricas["label_3m"],
        },
        "saldo_total": saldo_total,
        "saldos": saldos,
        "gasto_mes": gasto_mes,
        "orcamento_usado_percentual": orcamento_usado_percentual,
        "orcamento_usado_label": f"Base media 3 meses: R$ {referencia_orcamento:.2f}",
        "categorias_destaque": categorias_destaque,
        "ultimos_lancamentos": ultimos_lancamentos,
        "serie_mensal": serie_mensal,
        "serie_categoria": serie_categoria,
    }
