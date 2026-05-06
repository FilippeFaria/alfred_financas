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
        _log_error("postgres_read_error", error_type=type(exc).__name__)
        if not FALLBACK_ENABLED:
            raise ApiServiceError(code="FALHA_POSTGRES", message="Falha ao ler dados no PostgreSQL.", status_code=503) from exc

    df = carregar_transacoes_df_sheets()
    if df.empty:
        return []
    df = df.copy()
    df["_data_ord"] = pd.to_datetime(df["Data"], format=DATE_FORMAT, errors="coerce")
    df = df.sort_values("_data_ord", ascending=False, na_position="last").drop(columns=["_data_ord"])
    if limite:
        df = df.head(limite)
    return [mapear_linha_para_transacao(row) for row in df.to_dict(orient="records")]


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
