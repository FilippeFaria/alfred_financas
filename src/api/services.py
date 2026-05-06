"""Servicos da camada de API (sem dependencia de Streamlit)."""

from datetime import date, datetime
import json
import logging
from pathlib import Path

import pandas as pd

from src.api.errors import ApiServiceError
from src.analytics.calculations import adicionar_anomes, calcular_despesa_total, calcular_saldo
from src.config import CATEGORIAS_DESPESA, CATEGORIAS_INVESTIMENTO, CATEGORIAS_RECEITA
from src.services.google_sheets import get_sheet, read_sheet, write_sheet


ROOT_PATH = Path(__file__).resolve().parents[2]
DATE_FORMAT = "%d/%m/%Y %H:%M"
LOGGER = logging.getLogger("alfred.api.services")


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


def carregar_transacoes_df() -> pd.DataFrame:
    try:
        df = read_sheet(str(ROOT_PATH))
    except TimeoutError as exc:
        _log_error("google_sheets_timeout", operation="read_sheet")
        raise ApiServiceError(
            code="TIMEOUT",
            message="Tempo limite excedido ao acessar Google Sheets.",
            status_code=504,
        ) from exc
    except PermissionError as exc:
        _log_error("google_sheets_auth_error", operation="read_sheet")
        raise ApiServiceError(
            code="NAO_AUTORIZADO",
            message="Falha de autenticacao ao acessar a base de dados.",
            status_code=401,
        ) from exc
    except Exception as exc:
        _log_error("google_sheets_read_error", operation="read_sheet", error_type=type(exc).__name__)
        raise ApiServiceError(
            code="FALHA_GOOGLE_SHEETS",
            message="Falha ao ler dados financeiros.",
            status_code=503,
        ) from exc

    if df.empty:
        return df

    if "Valor" in df.columns:
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0.0)

    if "desconsiderar" in df.columns:
        df["desconsiderar"] = (
            df["desconsiderar"].replace("TRUE", True).replace("FALSE", False).fillna(False)
        )
        df["desconsiderar"] = df["desconsiderar"].astype(bool)

    if "Categoria" in df.columns:
        df["Categoria"] = df["Categoria"].astype(str).str.replace(
            "TV.Internet.Telefone", "Assinaturas", regex=False
        )

    return _normalizar_datas(df)


def obter_saldo_por_conta() -> list[dict]:
    df = carregar_transacoes_df()
    if df.empty:
        return []

    saldo_series = calcular_saldo(df)
    return [
        {"conta": str(conta), "saldo": float(valor)}
        for conta, valor in saldo_series.sort_index().items()
    ]


def _proximo_id(df: pd.DataFrame) -> int:
    if df.empty or "id" not in df.columns:
        return 1
    ids = pd.to_numeric(df["id"], errors="coerce").dropna()
    if ids.empty:
        return 1
    return int(ids.max()) + 1


def _montar_registro_transacao(
    *,
    transacao_id: int,
    nome: str,
    tipo: str,
    valor: float,
    categoria: str,
    conta: str,
    data: datetime,
    obs: str,
    tag: str | None,
    desconsiderar: bool,
    parcela: int | None,
    data_origem: datetime | None,
    data_criacao: str,
) -> dict:
    return {
        "id": transacao_id,
        "Nome": nome,
        "Tipo": tipo,
        "Valor": valor,
        "Categoria": categoria,
        "Conta": conta,
        "Data": data.strftime("%Y-%m-%d %H:%M:%S"),
        "Obs": obs,
        "TAG": tag,
        "desconsiderar": desconsiderar,
        "Parcela": parcela,
        "Data origem": data_origem.strftime("%Y-%m-%d %H:%M:%S") if data_origem else "",
        "Data Criacao": data_criacao,
    }


def criar_transacao(
    *,
    nome: str,
    tipo: str,
    valor: float,
    categoria: str,
    conta: str,
    data: datetime,
    obs: str = "",
    tag: str | None = None,
    desconsiderar: bool = False,
    parcelas: int | None = None,
) -> dict:
    _validar_categoria_por_tipo(tipo, categoria)
    if tipo == "Despesa" and valor > 0:
        raise ApiServiceError(
            code="DADOS_INVALIDOS",
            message="Despesa deve possuir valor negativo.",
            status_code=400,
        )
    if tipo in {"Receita", "Investimento"} and valor < 0:
        raise ApiServiceError(
            code="DADOS_INVALIDOS",
            message=f"{tipo} deve possuir valor positivo.",
            status_code=400,
        )

    df = carregar_transacoes_df()
    transacao_id = _proximo_id(df)
    data_criacao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    novos_registros: list[dict] = []
    if parcelas and parcelas > 1:
        for i in range(parcelas):
            data_parcela = data + pd.DateOffset(months=i)
            novos_registros.append(
                _montar_registro_transacao(
                    transacao_id=transacao_id,
                    nome=nome,
                    tipo=tipo,
                    valor=valor,
                    categoria=categoria,
                    conta=conta,
                    data=data_parcela.to_pydatetime(),
                    obs=obs,
                    tag=tag,
                    desconsiderar=desconsiderar,
                    parcela=i + 1,
                    data_origem=data,
                    data_criacao=data_criacao,
                )
            )
    else:
        novos_registros.append(
            _montar_registro_transacao(
                transacao_id=transacao_id,
                nome=nome,
                tipo=tipo,
                valor=valor,
                categoria=categoria,
                conta=conta,
                data=data,
                obs=obs,
                tag=tag,
                desconsiderar=desconsiderar,
                parcela=None,
                data_origem=None,
                data_criacao=data_criacao,
            )
        )

    df_novos = pd.DataFrame(novos_registros)
    df_final = pd.concat([df, df_novos], ignore_index=True) if not df.empty else df_novos
    df_final = _normalizar_datas(df_final)

    try:
        sheet = get_sheet(str(ROOT_PATH))
        write_sheet(sheet, df_final)
    except TimeoutError as exc:
        _log_error("google_sheets_timeout", operation="write_sheet")
        raise ApiServiceError(
            code="TIMEOUT",
            message="Tempo limite excedido ao salvar transacao.",
            status_code=504,
        ) from exc
    except PermissionError as exc:
        _log_error("google_sheets_auth_error", operation="write_sheet")
        raise ApiServiceError(
            code="NAO_AUTORIZADO",
            message="Falha de autenticacao ao salvar transacao.",
            status_code=401,
        ) from exc
    except Exception as exc:
        _log_error("google_sheets_write_error", operation="write_sheet", error_type=type(exc).__name__)
        raise ApiServiceError(
            code="FALHA_GOOGLE_SHEETS",
            message="Falha ao persistir transacao.",
            status_code=503,
        ) from exc

    return mapear_linha_para_transacao(df_novos.iloc[0].to_dict())


def mapear_linha_para_transacao(linha: dict) -> dict:
    data_valor = linha.get("Data")
    if pd.notna(data_valor):
        data_normalizada = pd.to_datetime(data_valor, format="mixed", dayfirst=True, errors="coerce")
        data_formatada = data_normalizada.strftime(DATE_FORMAT) if pd.notna(data_normalizada) else ""
    else:
        data_formatada = ""

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
        "data_criacao": (
            str(linha.get("Data Criacao"))
            if pd.notna(linha.get("Data Criacao")) and str(linha.get("Data Criacao")).strip()
            else None
        ),
        "parcela": (
            int(linha.get("Parcela"))
            if pd.notna(linha.get("Parcela")) and str(linha.get("Parcela")).strip()
            else None
        ),
        "data_origem": (
            str(linha.get("Data origem"))
            if pd.notna(linha.get("Data origem")) and str(linha.get("Data origem")).strip()
            else None
        ),
    }


def listar_transacoes(limite: int | None = None) -> list[dict]:
    df = carregar_transacoes_df()
    if df.empty:
        return []

    df = df.copy()
    df["_data_ord"] = pd.to_datetime(df["Data"], format=DATE_FORMAT, errors="coerce")
    df = df.sort_values("_data_ord", ascending=False, na_position="last").drop(columns=["_data_ord"])

    if limite is not None and limite > 0:
        df = df.head(limite)

    return [mapear_linha_para_transacao(row) for row in df.to_dict(orient="records")]


def excluir_transacao_por_id(transacao_id: int) -> dict:
    df = carregar_transacoes_df()
    if df.empty:
        return {
            "id": transacao_id,
            "removidos": 0,
            "mensagem": "Nenhuma transacao encontrada para exclusao.",
        }

    if "id" not in df.columns:
        return {
            "id": transacao_id,
            "removidos": 0,
            "mensagem": "Coluna id nao encontrada na base.",
        }

    ids = pd.to_numeric(df["id"], errors="coerce")
    mascara_manter = ids != transacao_id
    removidos = int((~mascara_manter).sum())
    if removidos == 0:
        return {
            "id": transacao_id,
            "removidos": 0,
            "mensagem": f"Nenhuma transacao encontrada com id {transacao_id}.",
        }

    df_filtrado = df[mascara_manter].copy()
    try:
        sheet = get_sheet(str(ROOT_PATH))
        write_sheet(sheet, df_filtrado)
    except TimeoutError as exc:
        _log_error("google_sheets_timeout", operation="delete_write_sheet")
        raise ApiServiceError(
            code="TIMEOUT",
            message="Tempo limite excedido ao excluir transacao.",
            status_code=504,
        ) from exc
    except PermissionError as exc:
        _log_error("google_sheets_auth_error", operation="delete_write_sheet")
        raise ApiServiceError(
            code="NAO_AUTORIZADO",
            message="Falha de autenticacao ao excluir transacao.",
            status_code=401,
        ) from exc
    except Exception as exc:
        _log_error("google_sheets_delete_error", operation="delete_write_sheet", error_type=type(exc).__name__)
        raise ApiServiceError(
            code="FALHA_GOOGLE_SHEETS",
            message="Falha ao excluir transacao.",
            status_code=503,
        ) from exc

    return {
        "id": transacao_id,
        "removidos": removidos,
        "mensagem": f"{removidos} registro(s) removido(s) para o id {transacao_id}.",
    }


def listar_categorias() -> dict[str, list[str]]:
    return {
        "despesa": CATEGORIAS_DESPESA,
        "receita": CATEGORIAS_RECEITA,
        "investimento": CATEGORIAS_INVESTIMENTO,
    }


def _validar_categoria_por_tipo(tipo: str, categoria: str) -> None:
    mapa = {
        "Despesa": CATEGORIAS_DESPESA,
        "Receita": CATEGORIAS_RECEITA,
        "Investimento": CATEGORIAS_INVESTIMENTO,
        "Transferência": ["Transferência"],
        "Transferencia": ["Transferência", "Transferencia"],
    }
    if tipo not in mapa:
        raise ApiServiceError(
            code="DADOS_INVALIDOS",
            message=f"Tipo de transacao invalido: {tipo}",
            status_code=400,
        )
    if categoria not in mapa[tipo]:
        raise ApiServiceError(
            code="DADOS_INVALIDOS",
            message=f"Categoria '{categoria}' invalida para tipo '{tipo}'.",
            status_code=400,
        )


def _aplicar_filtros_analise(
    df: pd.DataFrame,
    *,
    desconsiderar: bool,
    va: bool,
    vr: bool,
    bianca: bool,
    filippe: bool,
) -> pd.DataFrame:
    from src.config import GRANDES_TRANSACOES

    df_temp = df.copy()
    if desconsiderar and "id" in df_temp.columns:
        df_temp = df_temp[~df_temp["id"].isin(GRANDES_TRANSACOES)]

    if va:
        df_temp = df_temp[df_temp["Conta"] != "VA"]
    if vr:
        df_temp = df_temp[df_temp["Conta"] != "VR"]

    if bianca:
        contas_filtradas = ["Cartão Bianca", "Inter", "Itaú CC", "Cartão Nath", "VA", "VR"]
        df_temp = df_temp[df_temp["Conta"].isin(contas_filtradas)].copy()
        df_temp.loc[df_temp["Conta"].isin(["Itaú CC", "Cartão Nath", "VA", "VR"]), "Valor"] *= 0.3
    elif filippe:
        contas_filtradas = ["Cartão Filippe", "Nubank", "Itaú CC", "Cartão Nath", "VA", "VR"]
        df_temp = df_temp[df_temp["Conta"].isin(contas_filtradas)].copy()
        df_temp.loc[df_temp["Conta"].isin(["Itaú CC", "Cartão Nath", "VA", "VR"]), "Valor"] *= 0.7

    return df_temp


def obter_resumo_analise(
    *,
    desconsiderar: bool = True,
    va: bool = False,
    vr: bool = False,
    bianca: bool = False,
    filippe: bool = False,
    day_to_date: bool = False,
    anome_referencia: int | None = None,
) -> dict:
    df = carregar_transacoes_df()
    if df.empty:
        return {
            "anome_referencia": int(datetime.now().strftime("%Y%m")),
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
            "items": [],
        }

    df_temp = _aplicar_filtros_analise(
        df,
        desconsiderar=desconsiderar,
        va=va,
        vr=vr,
        bianca=bianca,
        filippe=filippe,
    )
    df_temp = adicionar_anomes(df_temp)

    anomes_disponiveis = sorted(
        [int(v) for v in df_temp["anomes"].dropna().astype(str).unique() if str(v).isdigit()]
    )
    anome_base = anome_referencia or (anomes_disponiveis[-1] if anomes_disponiveis else int(datetime.now().strftime("%Y%m")))

    if day_to_date and not df_temp.empty:
        data_max = df_temp[(df_temp["anomes"] == str(anome_base)) & (df_temp["Parcela"].isna())]["Data"].dt.day.max()
        if pd.notna(data_max):
            df_temp = df_temp[df_temp["Data"].dt.day <= int(data_max)]

    df_despesa = df_temp[(df_temp["desconsiderar"] == False) & (df_temp["Tipo"] == "Despesa")]
    metricas = calcular_despesa_total(df_despesa, int(anome_base))
    items = [mapear_linha_para_transacao(row) for row in df_temp.to_dict(orient="records")]

    return {
        "anome_referencia": int(anome_base),
        "anomes_disponiveis": anomes_disponiveis,
        "metricas": {
            "gasto_atual": float(metricas["gasto_atual"]),
            "gasto_anterior": float(metricas["gasto_anterior"]),
            "gasto_3m_media": float(metricas["gasto_3m_media"]),
            "delta_anterior": metricas["delta_anterior"],
            "delta_atual": metricas["delta_atual"],
            "delta_3m": metricas["delta_3m"],
            "label_prev": metricas["label_prev"],
            "label_curr": metricas["label_curr"],
            "label_3m": metricas["label_3m"],
        },
        "items": items,
    }


def gerar_insights_basicos(pergunta: str | None) -> dict:
    df = carregar_transacoes_df()
    if df.empty:
        return {
            "resumo": "Nenhuma transacao encontrada.",
            "insights": ["Base vazia. Cadastre transacoes para gerar insights."],
        }

    saldo = obter_saldo_por_conta()
    saldo_total = round(sum(item["saldo"] for item in saldo), 2)

    df_trabalho = df.copy()
    df_trabalho["Data"] = pd.to_datetime(df_trabalho["Data"], format=DATE_FORMAT, errors="coerce")
    inicio_mes = pd.Timestamp(date.today().replace(day=1))
    fim_mes = inicio_mes + pd.DateOffset(months=1)

    despesas_mes = df_trabalho[
        (df_trabalho["Tipo"] == "Despesa")
        & (df_trabalho["Data"] >= inicio_mes)
        & (df_trabalho["Data"] < fim_mes)
    ]

    top_categoria = "Sem despesas no mes"
    total_top_categoria = 0.0
    if not despesas_mes.empty:
        categoria_serie = despesas_mes.groupby("Categoria")["Valor"].sum().abs().sort_values(ascending=False)
        top_categoria = str(categoria_serie.index[0])
        total_top_categoria = float(round(categoria_serie.iloc[0], 2))

    texto_pergunta = pergunta.strip() if pergunta else "Sem pergunta especifica."
    return {
        "resumo": f"Saldo total atual: R$ {saldo_total:.2f}.",
        "insights": [
            f"Maior categoria de despesa no mes: {top_categoria} (R$ {total_top_categoria:.2f}).",
            f"Total de contas com saldo calculado: {len(saldo)}.",
            f"Contexto da solicitacao: {texto_pergunta}",
        ],
    }
