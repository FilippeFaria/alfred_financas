from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, ValidationError


class AIClientError(Exception):
    """Erro padronizado para falhas de integracao com OpenAI."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = 503,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _request_timeout_seconds() -> float:
    raw = _env("OPENAI_REQUEST_TIMEOUT_SECONDS", "30")
    try:
        timeout = float(raw)
        if timeout <= 0:
            raise ValueError
        return timeout
    except ValueError as exc:
        raise AIClientError(
            code="OPENAI_CONFIG_INVALIDA",
            message="Configuracao de timeout da OpenAI invalida.",
            status_code=500,
            details={"env": "OPENAI_REQUEST_TIMEOUT_SECONDS"},
        ) from exc


def _text_model_default() -> str:
    return _env("OPENAI_TEXT_MODEL", "gpt-5.5")


def _transcription_model_default() -> str:
    return _env("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-transcribe")


@lru_cache(maxsize=1)
def get_openai_client():
    from openai import OpenAI

    api_key = _env("OPENAI_API_KEY")
    if not api_key:
        raise AIClientError(
            code="OPENAI_API_KEY_AUSENTE",
            message="Integracao de IA nao configurada. Defina OPENAI_API_KEY no ambiente.",
            status_code=503,
        )

    return OpenAI(api_key=api_key, timeout=_request_timeout_seconds())


def _safe_openai_error(exc: Exception) -> AIClientError:
    return AIClientError(
        code="OPENAI_SERVICO_INDISPONIVEL",
        message="Falha ao processar requisicao com servico de IA.",
        status_code=503,
        details={"error_type": type(exc).__name__},
    )


def gerar_json_estruturado(
    *,
    system_prompt: str,
    user_input: str,
    schema: type[BaseModel] | None = None,
    model: str | None = None,
) -> dict:
    """Gera JSON estruturado com validacao opcional por schema Pydantic."""
    try:
        client = get_openai_client()
        model_name = model or _text_model_default()
        if hasattr(client, "responses"):
            resposta = client.responses.create(
                model=model_name,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                response_format={"type": "json_object"},
            )
            output_text = (getattr(resposta, "output_text", "") or "").strip()
        else:
            # Compatibilidade com ambientes em que `responses` nao esta disponivel.
            resposta = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                response_format={"type": "json_object"},
            )
            output_text = (
                resposta.choices[0].message.content
                if getattr(resposta, "choices", None)
                else ""
            ) or ""
            output_text = output_text.strip()
    except AIClientError:
        raise
    except Exception as exc:
        raise _safe_openai_error(exc) from exc

    if not output_text:
        raise AIClientError(
            code="OPENAI_RESPOSTA_VAZIA",
            message="Servico de IA retornou resposta vazia.",
            status_code=502,
        )

    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise AIClientError(
            code="OPENAI_JSON_INVALIDO",
            message="Servico de IA retornou conteudo nao estruturado.",
            status_code=502,
        ) from exc

    if schema is not None:
        try:
            validado = schema.model_validate(payload)
            return validado.model_dump(mode="json")
        except ValidationError as exc:
            raise AIClientError(
                code="OPENAI_SCHEMA_INVALIDO",
                message="Servico de IA retornou payload fora do schema esperado.",
                status_code=502,
                details={"errors": exc.errors()},
            ) from exc

    return payload


def transcrever_audio(
    *,
    file_path: str,
    language: str = "pt",
    model: str | None = None,
) -> str:
    """Transcreve audio para texto usando modelo configurado por ambiente."""
    try:
        client = get_openai_client()
        with open(file_path, "rb") as arquivo:
            transcricao = client.audio.transcriptions.create(
                model=model or _transcription_model_default(),
                file=arquivo,
                language=language,
            )
    except AIClientError:
        raise
    except Exception as exc:
        raise _safe_openai_error(exc) from exc

    texto = (getattr(transcricao, "text", "") or "").strip()
    if not texto:
        raise AIClientError(
            code="OPENAI_TRANSCRICAO_VAZIA",
            message="Nao foi possivel transcrever o audio informado.",
            status_code=502,
        )
    return texto


def interpretar_transacao_texto(prompt_sistema: str, texto_usuario: str, *, model: str | None = None) -> dict:
    """Compatibilidade com implementacao anterior."""
    return gerar_json_estruturado(
        system_prompt=prompt_sistema,
        user_input=texto_usuario,
        schema=None,
        model=model,
    )


def escolher_valor_categorico_com_llm(
    *,
    campo: str,
    valor_bruto: str,
    opcoes: list[str],
    model: str | None = None,
) -> str | None:
    """Usa LLM para desempatar opcao categorica quando matching local for incerto."""
    if not valor_bruto.strip() or not opcoes:
        return None

    from pydantic import BaseModel

    class EscolhaCampoSchema(BaseModel):
        escolha: str | None = None

    opcoes_texto = "\n".join(f"- {opcao}" for opcao in opcoes[:30])
    prompt = (
        "Escolha exatamente uma opcao da lista para o campo informado. "
        "Se nenhuma opcao servir, retorne escolha=null. "
        "Nao invente valores fora da lista.\n\n"
        f"Campo: {campo}\n"
        f"Valor bruto: {valor_bruto}\n"
        f"Opcoes:\n{opcoes_texto}"
    )

    try:
        payload = gerar_json_estruturado(
            system_prompt="Voce normaliza dados categoricos financeiros.",
            user_input=prompt,
            schema=EscolhaCampoSchema,
            model=model,
        )
    except AIClientError:
        return None

    escolha = payload.get("escolha")
    if isinstance(escolha, str) and escolha in opcoes:
        return escolha
    return None
