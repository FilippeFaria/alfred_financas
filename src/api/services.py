"""Servicos da camada de API (sem dependencia de Streamlit)."""

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from src.analytics.calculations import calcular_saldo
from src.config import CATEGORIAS_DESPESA, CATEGORIAS_INVESTIMENTO, CATEGORIAS_RECEITA
from src.services.google_sheets import get_sheet, read_sheet, write_sheet


ROOT_PATH = Path(__file__).resolve().parents[2]
DATE_FORMAT = "%d/%m/%Y %H:%M"


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
    df = read_sheet(str(ROOT_PATH))
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

    sheet = get_sheet(str(ROOT_PATH))
    write_sheet(sheet, df_final)

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


def listar_categorias() -> dict[str, list[str]]:
    return {
        "despesa": CATEGORIAS_DESPESA,
        "receita": CATEGORIAS_RECEITA,
        "investimento": CATEGORIAS_INVESTIMENTO,
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

