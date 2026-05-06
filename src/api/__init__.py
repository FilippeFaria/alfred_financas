"""Camada de API do projeto Alfred Financas."""

from src.api.client import (
    AlfredApiClient,
    ApiClientError,
    carregar_dataframe_transacoes,
    criar_transacao,
    excluir_transacao,
    gerar_insights,
    obter_resumo_analise,
    listar_categorias,
    listar_transacoes,
    obter_client_api,
    obter_saldo,
    transacoes_para_dataframe,
)

__all__ = [
    "AlfredApiClient",
    "ApiClientError",
    "obter_client_api",
    "obter_saldo",
    "listar_transacoes",
    "criar_transacao",
    "excluir_transacao",
    "listar_categorias",
    "gerar_insights",
    "obter_resumo_analise",
    "transacoes_para_dataframe",
    "carregar_dataframe_transacoes",
]
