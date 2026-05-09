"""Client HTTP interno para consumir a API FastAPI do Alfred Financas."""

from __future__ import annotations

from datetime import datetime
import os
from typing import Any

import pandas as pd
import requests

from src.analytics.calculations import adicionar_anomes
from src.config import API_AUTH_TOKEN, API_BASE_URL, API_TIMEOUT_SECONDS


class ApiClientError(RuntimeError):
    """Erro padronizado para falhas de comunicacao com a API."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AlfredApiClient:
    """Client HTTP com timeout e tratamento de erros centralizado."""

    def __init__(
        self,
        *,
        base_url: str = API_BASE_URL,
        timeout_seconds: float = API_TIMEOUT_SECONDS,
        auth_token: str | None = API_AUTH_TOKEN,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.auth_token = auth_token.strip() if auth_token else ""
        self.session = session or requests.Session()

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json_payload: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            resposta = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_payload,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise ApiClientError(
                f"Timeout ao chamar {method.upper()} {url} (timeout={self.timeout_seconds}s)."
            ) from exc
        except requests.ConnectionError as exc:
            raise ApiClientError(
                f"Falha de conexao com a API em {url}. Verifique se o backend esta ativo."
            ) from exc
        except requests.RequestException as exc:
            raise ApiClientError(f"Erro de comunicacao com a API em {url}: {exc}") from exc

        if not resposta.ok:
            mensagem = f"Erro {resposta.status_code} ao chamar {method.upper()} {url}."
            try:
                detalhe = resposta.json()
            except ValueError:
                detalhe = resposta.text

            if detalhe:
                mensagem = f"{mensagem} Detalhe: {detalhe}"
            raise ApiClientError(mensagem, status_code=resposta.status_code)

        if resposta.status_code == 204:
            return None

        try:
            return resposta.json()
        except ValueError as exc:
            raise ApiClientError(
                f"Resposta invalida da API em {method.upper()} {url}: JSON nao parseavel."
            ) from exc

    def obter_saldo(self) -> list[dict[str, Any]]:
        return self._request("GET", "/saldo")

    def listar_transacoes(self, limite: int | None = None) -> dict[str, Any]:
        params = {"limite": limite} if limite else None
        return self._request("GET", "/transacoes", params=params)

    def criar_transacao(
        self,
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
    ) -> dict[str, Any]:
        payload = {
            "nome": nome,
            "tipo": tipo,
            "valor": valor,
            "categoria": categoria,
            "conta": conta,
            "data": data.isoformat(),
            "obs": obs,
            "tag": tag,
            "desconsiderar": desconsiderar,
            "parcelas": parcelas,
        }
        return self._request("POST", "/transacoes", json_payload=payload)

    def listar_categorias(self) -> dict[str, list[str]]:
        return self._request("GET", "/categorias")

    def gerar_insights(self, pergunta: str | None = None) -> dict[str, Any]:
        return self._request("POST", "/insights", json_payload={"pergunta": pergunta})

    def excluir_transacao(self, transacao_id: int) -> dict[str, Any]:
        return self._request("DELETE", f"/transacoes/{transacao_id}")

    def obter_resumo_analise(
        self,
        *,
        desconsiderar: bool = True,
        va: bool = False,
        vr: bool = False,
        bianca: bool = False,
        filippe: bool = False,
        day_to_date: bool = False,
        anome_referencia: int | None = None,
    ) -> dict[str, Any]:
        payload = {
            "desconsiderar": desconsiderar,
            "va": va,
            "vr": vr,
            "bianca": bianca,
            "filippe": filippe,
            "day_to_date": day_to_date,
            "anome_referencia": anome_referencia,
        }
        return self._request("POST", "/analise/resumo", json_payload=payload)

    def obter_orcamento_valores(self) -> dict[str, Any]:
        return self._request("GET", "/orcamento/valores")

    def salvar_orcamento_valores(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        return self._request("POST", "/orcamento/valores", json_payload={"items": items})


_client_padrao: AlfredApiClient | None = None


def obter_client_api() -> AlfredApiClient:
    """Retorna instancia singleton do client para reutilizacao interna."""
    global _client_padrao
    if _client_padrao is None:
        _client_padrao = AlfredApiClient()
    return _client_padrao


def obter_saldo() -> list[dict[str, Any]]:
    return obter_client_api().obter_saldo()


def listar_transacoes(limite: int | None = None) -> dict[str, Any]:
    return obter_client_api().listar_transacoes(limite=limite)


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
) -> dict[str, Any]:
    return obter_client_api().criar_transacao(
        nome=nome,
        tipo=tipo,
        valor=valor,
        categoria=categoria,
        conta=conta,
        data=data,
        obs=obs,
        tag=tag,
        desconsiderar=desconsiderar,
        parcelas=parcelas,
    )


def listar_categorias() -> dict[str, list[str]]:
    return obter_client_api().listar_categorias()


def gerar_insights(pergunta: str | None = None) -> dict[str, Any]:
    return obter_client_api().gerar_insights(pergunta=pergunta)


def excluir_transacao(transacao_id: int) -> dict[str, Any]:
    return obter_client_api().excluir_transacao(transacao_id)


def obter_resumo_analise(
    *,
    desconsiderar: bool = True,
    va: bool = False,
    vr: bool = False,
    bianca: bool = False,
    filippe: bool = False,
    day_to_date: bool = False,
    anome_referencia: int | None = None,
) -> dict[str, Any]:
    return obter_client_api().obter_resumo_analise(
        desconsiderar=desconsiderar,
        va=va,
        vr=vr,
        bianca=bianca,
        filippe=filippe,
        day_to_date=day_to_date,
        anome_referencia=anome_referencia,
    )


def obter_orcamento_valores() -> dict[str, Any]:
    return obter_client_api().obter_orcamento_valores()


def salvar_orcamento_valores(items: list[dict[str, Any]]) -> dict[str, Any]:
    return obter_client_api().salvar_orcamento_valores(items)


def transacoes_para_dataframe(payload: dict[str, Any]) -> pd.DataFrame:
    """Converte o payload de /transacoes para o formato legado usado no Streamlit."""
    items = payload.get("items", []) if isinstance(payload, dict) else []
    if not items:
        return pd.DataFrame(
            columns=[
                "id",
                "Nome",
                "Tipo",
                "Valor",
                "Categoria",
                "Conta",
                "Data",
                "Obs",
                "TAG",
                "desconsiderar",
                "Parcela",
                "Data origem",
                "Data Criacao",
            ]
        )

    linhas: list[dict[str, Any]] = []
    for item in items:
        linhas.append(
            {
                "id": item.get("id"),
                "Nome": item.get("nome", ""),
                "Tipo": item.get("tipo", ""),
                "Valor": float(item.get("valor", 0.0)),
                "Categoria": item.get("categoria", ""),
                "Conta": item.get("conta", ""),
                "Data": item.get("data", ""),
                "Obs": item.get("obs", ""),
                "TAG": item.get("tag"),
                "desconsiderar": bool(item.get("desconsiderar", False)),
                "Parcela": item.get("parcela"),
                "Data origem": item.get("data_origem"),
                "Data Criacao": item.get("data_criacao"),
            }
        )

    df = pd.DataFrame(linhas)
    if "id" in df.columns:
        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)

    for coluna in ("Parcela",):
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    if "Data" in df.columns:
        datas = pd.to_datetime(df["Data"], format="%d/%m/%Y %H:%M", errors="coerce")
        df = df.assign(_data_ord=datas).sort_values("_data_ord", ascending=True).drop(columns="_data_ord")

    df = df.reset_index(drop=True)

    # Garantia definitiva para o frontend: toda carga vinda da API sai com 'anomes'.
    if not df.empty and "Data" in df.columns and "anomes" not in df.columns:
        df = adicionar_anomes(df)

    return df


def carregar_dataframe_transacoes(limite: int | None = None) -> pd.DataFrame:
    if limite is None:
        limite_default = os.getenv("ALFRED_TRANSACOES_LIMIT_DEFAULT", "").strip()
        if limite_default.isdigit():
            limite = int(limite_default)
    return transacoes_para_dataframe(listar_transacoes(limite=limite))
