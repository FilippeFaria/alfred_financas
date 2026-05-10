from __future__ import annotations

from src.config import CATEGORIAS_DESPESA, CATEGORIAS_INVESTIMENTO, CATEGORIAS_RECEITA, CONTAS

from .schemas import CampoPendente, ExtracaoIA, SugestaoTransacao


def validar_extracao(extracao: ExtracaoIA) -> tuple[list[str], list[CampoPendente]]:
    avisos: list[str] = []
    pendentes = set(extracao.campos_pendentes)

    if not extracao.nome:
        pendentes.add(CampoPendente.NOME)

    if not extracao.tipo:
        pendentes.add(CampoPendente.TIPO)
    elif extracao.tipo not in {"Despesa", "Receita", "Investimento", "Transferencia", "Transferência", "Pagamento de Cartao", "Pagamento de Cartão"}:
        avisos.append(f"Tipo nao reconhecido: {extracao.tipo}")

    if extracao.valor is None:
        pendentes.add(CampoPendente.VALOR)

    if not extracao.categoria:
        pendentes.add(CampoPendente.CATEGORIA)
    elif extracao.tipo == "Despesa" and extracao.categoria not in CATEGORIAS_DESPESA:
        avisos.append(f"Categoria '{extracao.categoria}' fora da lista de despesas")
    elif extracao.tipo == "Receita" and extracao.categoria not in CATEGORIAS_RECEITA:
        avisos.append(f"Categoria '{extracao.categoria}' fora da lista de receitas")
    elif extracao.tipo == "Investimento" and extracao.categoria not in CATEGORIAS_INVESTIMENTO:
        avisos.append(f"Categoria '{extracao.categoria}' fora da lista de investimentos")

    if not extracao.conta:
        pendentes.add(CampoPendente.CONTA)
    elif extracao.conta not in CONTAS:
        avisos.append(f"Conta '{extracao.conta}' nao cadastrada")

    if extracao.data is None:
        pendentes.add(CampoPendente.DATA)

    if extracao.tipo == "Despesa" and extracao.valor is not None and extracao.valor > 0:
        avisos.append("Despesa normalmente deve ser negativa")
    if extracao.tipo in {"Receita", "Investimento"} and extracao.valor is not None and extracao.valor < 0:
        avisos.append(f"{extracao.tipo} normalmente deve ser positiva")

    return avisos, sorted(pendentes, key=lambda campo: campo.value)


def normalizar_para_sugestao(extracao: ExtracaoIA) -> SugestaoTransacao:
    return SugestaoTransacao(
        nome=extracao.nome,
        tipo=extracao.tipo,
        valor=extracao.valor,
        categoria=extracao.categoria,
        conta=extracao.conta,
        data=extracao.data,
        obs=extracao.obs or "",
        tag=extracao.tag,
        desconsiderar=extracao.desconsiderar,
    )
