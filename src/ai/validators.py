from __future__ import annotations

from src.config import CATEGORIAS_DESPESA, CATEGORIAS_RECEITA, CONTAS

from .schemas import TransacaoSugerida


TIPOS_VALIDOS = {"Despesa", "Receita", "Transferência", "Pagamento de Cartão"}


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

    if sugestao.conta and sugestao.conta not in CONTAS:
        avisos.append(f"Conta '{sugestao.conta}' nao cadastrada")
        campos_incertos.add("conta")

    if sugestao.tipo == "Despesa" and sugestao.valor is not None and sugestao.valor > 0:
        avisos.append("Despesa normalmente deve ser negativa")
        campos_incertos.add("valor")

    if sugestao.tipo == "Receita" and sugestao.valor is not None and sugestao.valor < 0:
        avisos.append("Receita normalmente deve ser positiva")
        campos_incertos.add("valor")

    return avisos, sorted(campos_incertos)
