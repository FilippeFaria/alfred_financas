from __future__ import annotations

from src.config import CATEGORIAS_DESPESA, CATEGORIAS_INVESTIMENTO, CATEGORIAS_RECEITA, CONTAS, CONTAS_INVEST

from .schemas import TransacaoSugerida


TIPOS_VALIDOS = {"Despesa", "Receita", "Transferência", "Pagamento de Cartão", "Investimento"}


def validar_transacao_sugerida(sugestao: TransacaoSugerida) -> tuple[list[str], list[str]]:
    avisos: list[str] = []
    campos_incertos = set(sugestao.campos_incertos)

    obrigatorios = ["nome", "tipo", "valor", "categoria", "conta", "data"]
    for campo in obrigatorios:
        if getattr(sugestao, campo) is None:
            campos_incertos.add(campo)

    if sugestao.tipo and sugestao.tipo not in TIPOS_VALIDOS:
        avisos.append(f"Tipo nao reconhecido: {sugestao.tipo}")
        campos_incertos.add("tipo")

    if sugestao.tipo == "Despesa" and sugestao.categoria and sugestao.categoria not in CATEGORIAS_DESPESA:
        avisos.append(f"Categoria '{sugestao.categoria}' fora da lista de despesas")
        campos_incertos.add("categoria")

    if sugestao.tipo == "Receita" and sugestao.categoria and sugestao.categoria not in CATEGORIAS_RECEITA:
        avisos.append(f"Categoria '{sugestao.categoria}' fora da lista de receitas")
        campos_incertos.add("categoria")

    if sugestao.tipo == "Investimento" and sugestao.categoria and sugestao.categoria not in CATEGORIAS_INVESTIMENTO:
        avisos.append(f"Categoria '{sugestao.categoria}' fora da lista de investimentos")
        campos_incertos.add("categoria")

    contas_validas = set(CONTAS + CONTAS_INVEST)
    if sugestao.conta and sugestao.conta not in contas_validas:
        avisos.append(f"Conta '{sugestao.conta}' nao cadastrada")
        campos_incertos.add("conta")

    if sugestao.tipo in {"Transferência", "Pagamento de Cartão", "Investimento"} and not sugestao.conta_destino:
        campos_incertos.add("conta_destino")

    if sugestao.valor is not None and float(sugestao.valor) == 0:
        avisos.append("Valor zero detectado")
        campos_incertos.add("valor")

    return avisos, sorted(campos_incertos)
