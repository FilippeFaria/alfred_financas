from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

import pandas as pd

from src.analytics.calculations import adicionar_anomes, calcular_despesa_total, calcular_saldo
from src.config import (
    ALERTA_PERCENTUAL_CATEGORIA_DESEJADA,
    ALERTA_MULTIPLICADOR_DESPESA_CATEGORIA,
    ALERTA_PERCENTUAL_GASTO_MENSAL,
    ALERTA_SALDO_MINIMO_PADRAO,
    BASE_PATH,
)
from src.services.google_sheets import read_valores_desejados


@dataclass(frozen=True)
class Alerta:
    chave: str
    titulo: str
    mensagem: str
    severidade: str = "info"
    mensagem_formatada: bool = False


@dataclass(frozen=True)
class ContextoAlertas:
    df: pd.DataFrame
    referencia: datetime
    chat_id: int | None = None
    nome_usuario: str | None = None
    contas_usuario: list[str] | None = None


RegraAlerta = Callable[[ContextoAlertas], list[Alerta]]


def format_real(value: float) -> str:
    text = f"{value:,.2f}"
    return "R$ " + text.replace(",", "X").replace(".", ",").replace("X", ".")


def construir_alertas(contexto: ContextoAlertas) -> list[Alerta]:
    regras: list[RegraAlerta] = [
        regra_lembrete_sem_cadastro,
        regra_categoria_acima_do_orcamento,
        regra_gasto_categoria_proximo_do_limite,
        regra_categoria_com_disparo_relevante,
    ]

    alertas: list[Alerta] = []
    for regra in regras:
        alertas.extend(regra(contexto))
    return alertas


def regra_lembrete_sem_cadastro(contexto: ContextoAlertas) -> list[Alerta]:
    if not contexto.contas_usuario:
        return []

    df = contexto.df.copy()
    if "Conta" not in df.columns or "Data Criacao" not in df.columns:
        return []

    df = df[df["Conta"].isin(contexto.contas_usuario)].copy()
    if df.empty:
        return []

    datas_criacao = pd.to_datetime(df["Data Criacao"], format="mixed", dayfirst=True, errors="coerce")
    ultima_data_criacao = datas_criacao.max()
    if pd.isna(ultima_data_criacao):
        return []

    diferenca = contexto.referencia - ultima_data_criacao.to_pydatetime().replace(tzinfo=contexto.referencia.tzinfo)
    dias_sem_cadastro = int(diferenca.total_seconds() // 86400)

    if dias_sem_cadastro <= 2:
        return []

    nome_usuario = contexto.nome_usuario or "Usuário"
    return [
        Alerta(
            chave=f"lembrete_sem_cadastro:{contexto.chat_id or 'desconhecido'}",
            titulo="Lembrete de cadastro",
            mensagem=(
                f"{nome_usuario} você realmente ficou sem gastar por {dias_sem_cadastro} dia(s) "
                "ou só esqueceu de preencher? Preenche lá por favor"
            ),
            severidade="info",
        )
    ]


def regra_saldo_baixo_por_conta(contexto: ContextoAlertas) -> list[Alerta]:
    saldo_s = calcular_saldo(contexto.df)
    alertas: list[Alerta] = []

    for conta, saldo in saldo_s.items():
        if float(saldo) < ALERTA_SALDO_MINIMO_PADRAO:
            alertas.append(
                Alerta(
                    chave=f"saldo_baixo:{conta}",
                    titulo="Saldo baixo",
                    mensagem=(
                        f"A conta {conta} esta com saldo em {format_real(float(saldo))}, "
                        f"abaixo do limite configurado de {format_real(ALERTA_SALDO_MINIMO_PADRAO)}."
                    ),
                    severidade="warning",
                )
            )

    return alertas


def regra_gasto_categoria_proximo_do_limite(contexto: ContextoAlertas) -> list[Alerta]:
    df = contexto.df.copy()
    df = df[(df["desconsiderar"] == False) & (df["Tipo"] == "Despesa")]
    if df.empty:
        return []

    try:
        df_valores = read_valores_desejados(str(BASE_PATH))
    except Exception:
        return []

    if df_valores.empty or "Categoria" not in df_valores.columns or "Valor" not in df_valores.columns:
        return []

    df_valores = df_valores.copy()
    df_valores["Valor"] = pd.to_numeric(df_valores["Valor"], errors="coerce")
    df_valores = df_valores.dropna(subset=["Categoria", "Valor"])
    df_valores = df_valores[df_valores["Valor"] > 0]
    if df_valores.empty:
        return []

    df = adicionar_anomes(df)
    anome_atual = contexto.referencia.strftime("%Y%m")
    df_mes = df[df["anomes"] == anome_atual].copy()
    if df_mes.empty:
        return []

    gastos_categoria = df_mes.groupby("Categoria")["Valor"].sum().abs()
    categorias_em_alerta: list[tuple[float, str]] = []

    for _, linha in df_valores.iterrows():
        categoria = str(linha["Categoria"]).strip()
        valor_desejado = float(linha["Valor"])
        valor_atual = float(gastos_categoria.get(categoria, 0.0))
        percentual = valor_atual / valor_desejado if valor_desejado else 0.0

        if percentual < ALERTA_PERCENTUAL_CATEGORIA_DESEJADA or percentual >= 1:
            continue

        categorias_em_alerta.append(
            (
                percentual,
                f"{categoria}: {format_real(valor_atual)}/ {format_real(valor_desejado)} ({percentual * 100:.0f}%)",
            )
        )

    if not categorias_em_alerta:
        return []

    categorias_em_alerta.sort(key=lambda item: item[0], reverse=True)
    mensagem = "\n".join(
        [
            "Cuidado! As seguintes categorias ja estao estourando em gastos",
            *(linha for _, linha in categorias_em_alerta),
        ]
    )
    return [
        Alerta(
            chave=f"gasto_categorias:{anome_atual}",
            titulo="Gastos por categoria",
            mensagem=mensagem,
            severidade="warning",
            mensagem_formatada=True,
        )
    ]


def regra_categoria_acima_do_orcamento(contexto: ContextoAlertas) -> list[Alerta]:
    df = contexto.df.copy()
    df = df[(df["desconsiderar"] == False) & (df["Tipo"] == "Despesa")]
    if df.empty:
        return []

    try:
        df_valores = read_valores_desejados(str(BASE_PATH))
    except Exception:
        return []

    if df_valores.empty or "Categoria" not in df_valores.columns or "Valor" not in df_valores.columns:
        return []

    df_valores = df_valores.copy()
    df_valores["Valor"] = pd.to_numeric(df_valores["Valor"], errors="coerce")
    df_valores = df_valores.dropna(subset=["Categoria", "Valor"])
    df_valores = df_valores[df_valores["Valor"] > 0]
    if df_valores.empty:
        return []

    df = adicionar_anomes(df)
    anome_atual = contexto.referencia.strftime("%Y%m")
    df_mes = df[df["anomes"] == anome_atual].copy()
    if df_mes.empty:
        return []

    gastos_categoria = df_mes.groupby("Categoria")["Valor"].sum().abs()
    alertas: list[Alerta] = []

    for _, linha in df_valores.iterrows():
        categoria = str(linha["Categoria"]).strip()
        valor_desejado = float(linha["Valor"])
        valor_atual = float(gastos_categoria.get(categoria, 0.0))
        if valor_atual <= valor_desejado:
            continue

        percentual_ultrapassado = ((valor_atual - valor_desejado) / valor_desejado) * 100
        alertas.append(
            Alerta(
                chave=f"categoria_orcamento_estourado:{anome_atual}:{categoria}",
                titulo="Orcamento por categoria estourado",
                mensagem=(
                    f"Voce ja ultrapassou o orcamento de {categoria} em "
                    f"{percentual_ultrapassado:.0f}%. Quer ajustar o limite ou revisar os gastos?"
                ),
                severidade="warning",
            )
        )

    return alertas


def regra_despesa_mensal_acima_da_media(contexto: ContextoAlertas) -> list[Alerta]:
    df_despesas = contexto.df.copy()
    df_despesas = df_despesas[
        (df_despesas["desconsiderar"] == False) & (df_despesas["Tipo"] == "Despesa")
    ]
    anome = int(contexto.referencia.strftime("%Y%m"))
    metricas = calcular_despesa_total(df_despesas, anome)

    gasto_atual = metricas["gasto_atual"]
    media_3m = metricas["gasto_3m_media"]
    if media_3m <= 0:
        return []

    excesso = (gasto_atual - media_3m) / media_3m
    if excesso < ALERTA_PERCENTUAL_GASTO_MENSAL:
        return []

    return [
        Alerta(
            chave="despesa_mensal_acima_media",
            titulo="Despesas acima do ritmo",
            mensagem=(
                f"As despesas de {metricas['label_curr']} estao em {format_real(gasto_atual)}, "
                f"{excesso * 100:.1f}% acima da media dos ultimos 3 meses "
                f"({format_real(media_3m)})."
            ),
            severidade="warning",
        )
    ]


def regra_categoria_com_disparo_relevante(contexto: ContextoAlertas) -> list[Alerta]:
    df = contexto.df.copy()
    df = df[(df["desconsiderar"] == False) & (df["Tipo"] == "Despesa")]
    if df.empty:
        return []

    df = adicionar_anomes(df)
    anome_atual = contexto.referencia.strftime("%Y%m")
    anome_anterior = (
        pd.Timestamp(contexto.referencia.year, contexto.referencia.month, 1)
        - pd.DateOffset(months=1)
    ).strftime("%Y%m")

    despesas_categoria = (
        df.groupby(["anomes", "Categoria"])["Valor"].sum().abs().reset_index()
    )
    atual = despesas_categoria[despesas_categoria["anomes"] == anome_atual]
    anterior = (
        despesas_categoria[despesas_categoria["anomes"] == anome_anterior]
        .rename(columns={"Valor": "Valor_anterior"})
        [["Categoria", "Valor_anterior"]]
    )
    comparativo = atual.merge(anterior, on="Categoria", how="left").fillna(0)

    alertas: list[Alerta] = []
    for _, linha in comparativo.iterrows():
        valor_atual = float(linha["Valor"])
        valor_anterior = float(linha["Valor_anterior"])
        if valor_atual <= 0 or valor_anterior <= 0:
            continue
        if valor_atual < valor_anterior * ALERTA_MULTIPLICADOR_DESPESA_CATEGORIA:
            continue

        aumento = ((valor_atual - valor_anterior) / valor_anterior) * 100
        categoria = linha["Categoria"]
        alertas.append(
            Alerta(
                chave=f"categoria_em_alta:{categoria}",
                titulo="Categoria em alta",
                mensagem=(
                    f"A categoria {categoria} subiu para {format_real(valor_atual)} em {anome_atual}, "
                    f"um aumento de {aumento:.1f}% sobre o mes anterior."
                ),
                severidade="warning",
            )
        )

    return alertas
