from __future__ import annotations

from datetime import datetime

import pandas as pd

from src.analytics.calculations import (
    calcular_comparativo_categorias_ate_dia_mes,
    calcular_comparativo_despesas_ate_dia_mes,
    calcular_saldo,
)
from src.config import (
    ALERTA_PERCENTUAL_CATEGORIA_DESEJADA,
    GRANDES_TRANSACOES,
    TELEGRAM_DAILY_REPORT_TOP_CATEGORIAS,
)


DIAS_SEMANA = {
    0: "Segunda",
    1: "Terca",
    2: "Quarta",
    3: "Quinta",
    4: "Sexta",
    5: "Sabado",
    6: "Domingo",
}

MESES_ABREV = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}

CATEGORIA_ICONS = {
    "Casa": "🏠",
    "Compras": "🛍️",
    "Restaurante": "🍔",
    "Supermercado": "🛒",
    "Transporte": "🚗",
    "Viagem": "✈️",
    "Saude": "🩺",
    "Lazer": "🎉",
    "Educacao": "📚",
    "Assinaturas": "📺",
    "Presentes": "🎁",
}


def format_real_curto(value: float) -> str:
    return "R$ " + f"{round(value):,}".replace(",", ".")


def format_percentual_inteiro(value: float) -> str:
    return f"{round(value * 100):.0f}%"


def formatar_cabecalho_data(referencia: datetime) -> str:
    dia_semana = DIAS_SEMANA[referencia.weekday()]
    mes = MESES_ABREV[referencia.month]
    return f"📅 {dia_semana}, {referencia.strftime('%d')} {mes}"


def formatar_label_dia_mes(referencia: datetime) -> str:
    mes = MESES_ABREV[referencia.month].lower()
    return f"{referencia.strftime('%d')}/{mes}"


def formatar_variacao_percentual(delta_percentual: float | None, label_referencia: str) -> str:
    if delta_percentual is None:
        return f"(vs {label_referencia})"

    if delta_percentual > 0:
        return f"(↑ +{round(delta_percentual * 100):.0f}% vs {label_referencia})"
    if delta_percentual < 0:
        return f"(↓ {round(delta_percentual * 100):.0f}% vs {label_referencia})"
    return f"(→ 0% vs {label_referencia})"


def _montar_linhas_orcamento(
    comparativo_categorias: pd.DataFrame,
    valores_desejados: dict[str, float],
) -> list[str]:
    if comparativo_categorias.empty or not valores_desejados:
        return []

    comparativo = comparativo_categorias.copy()
    comparativo["orcamento"] = comparativo["Categoria"].map(valores_desejados).fillna(0.0)
    comparativo["percentual_usado"] = comparativo.apply(
        lambda linha: (linha["valor_atual"] / linha["orcamento"]) if linha["orcamento"] else 0.0,
        axis=1,
    )

    linhas: list[str] = []

    estouradas = comparativo[comparativo["valor_atual"] > comparativo["orcamento"]]
    estouradas = estouradas.sort_values("valor_atual", ascending=False)
    for _, linha in estouradas.head(3).iterrows():
        excesso = float(linha["valor_atual"] - linha["orcamento"])
        linhas.append(f"🚨 {linha['Categoria']}: {format_real_curto(excesso)} acima do orcamento")

    proximas = comparativo[
        (comparativo["orcamento"] > 0) &
        (comparativo["percentual_usado"] >= ALERTA_PERCENTUAL_CATEGORIA_DESEJADA) &
        (comparativo["percentual_usado"] < 1)
    ].sort_values("percentual_usado", ascending=False)
    categorias_ja_listadas = {linha.split(":")[0].replace("🚨 ", "") for linha in linhas}

    for _, linha in proximas.head(3).iterrows():
        categoria = str(linha["Categoria"])
        if categoria in categorias_ja_listadas:
            continue
        percentual = float(linha["percentual_usado"])
        linhas.append(f"⚠️ {categoria}: {round(percentual * 100):.0f}% do orcamento consumido")

    return linhas


def _montar_linhas_maiores_aumentos(
    comparativo_categorias: pd.DataFrame,
) -> list[str]:
    if comparativo_categorias.empty:
        return []

    aumentos = comparativo_categorias[comparativo_categorias["delta_valor"] > 0]
    aumentos = aumentos.sort_values("delta_valor", ascending=False).head(TELEGRAM_DAILY_REPORT_TOP_CATEGORIAS)
    linhas: list[str] = []
    for _, linha in aumentos.iterrows():
        categoria = str(linha["Categoria"])
        icone = CATEGORIA_ICONS.get(categoria, "•")
        prefixo = "•" if icone != "•" else "•"
        icone_texto = f" {icone}" if icone != "•" else ""
        linhas.append(
            f"{prefixo}{icone_texto} {categoria}: +{format_real_curto(float(linha['delta_valor']))}"
        )
    return linhas


def montar_informe_diario(
    df: pd.DataFrame,
    valores_desejados: dict[str, float],
    referencia: datetime,
) -> str:
    saldo_total = float(calcular_saldo(df).sum())
    comparativo_despesas = calcular_comparativo_despesas_ate_dia_mes(df, referencia)
    comparativo_categorias = calcular_comparativo_categorias_ate_dia_mes(df, referencia)
    comparativo_orcamento = calcular_comparativo_despesas_ate_dia_mes(df, referencia)

    inicio_mes_anterior = comparativo_despesas["inicio_mes_anterior"]
    dia_referencia_anterior = min(
        int(comparativo_despesas["data_corte"]),
        int(inicio_mes_anterior.days_in_month),
    )
    data_referencia_anterior = inicio_mes_anterior + pd.DateOffset(days=dia_referencia_anterior - 1)
    label_referencia = formatar_label_dia_mes(data_referencia_anterior)

    linhas = [
        formatar_cabecalho_data(referencia),
        "",
        (
            f"📉 Gasto no mes: {format_real_curto(float(comparativo_despesas['gasto_atual']))} "
            f"{formatar_variacao_percentual(comparativo_despesas['delta_percentual'], label_referencia)}"
        ),
    ]

    total_orcamento = float(sum(valores_desejados.values()))
    if total_orcamento > 0:
        percentual_atual = float(comparativo_orcamento["gasto_atual"]) / total_orcamento
        percentual_anterior = float(comparativo_orcamento["gasto_anterior"]) / total_orcamento
        linhas.append(
            f"🎯 Orcamento usado: {format_percentual_inteiro(percentual_atual)} "
            f"(Vs {format_percentual_inteiro(percentual_anterior)} {label_referencia})"
        )

    linhas.append("")
    linhas_orcamento = _montar_linhas_orcamento(comparativo_categorias, valores_desejados)
    if linhas_orcamento:
        linhas.extend(linhas_orcamento)
        linhas.append("")

    linhas_aumentos = _montar_linhas_maiores_aumentos(comparativo_categorias)
    if linhas_aumentos:
        linhas.append(f"📈 Maiores aumentos vs {label_referencia}:")
        linhas.extend(linhas_aumentos)

    return "\n".join(linhas).strip()
