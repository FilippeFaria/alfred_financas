"""Erros padronizados e handlers globais da API."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


LOGGER = logging.getLogger("alfred.api")


@dataclass
class ApiServiceError(Exception):
    code: str
    message: str
    status_code: int = 500
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def _log_event(level: str, event: str, **fields: Any) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event,
        **fields,
    }
    text = json.dumps(payload, ensure_ascii=False, default=str)
    if level == "error":
        LOGGER.error(text)
    elif level == "warning":
        LOGGER.warning(text)
    else:
        LOGGER.info(text)


def _error_response(
    *,
    code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiServiceError)
    async def handle_api_service_error(request: Request, exc: ApiServiceError) -> JSONResponse:
        _log_event(
            "error",
            "api_service_error",
            path=str(request.url.path),
            method=request.method,
            code=exc.code,
            status_code=exc.status_code,
            details=exc.details or {},
        )
        return _error_response(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        _log_event(
            "warning",
            "request_validation_error",
            path=str(request.url.path),
            method=request.method,
            errors=exc.errors(),
        )
        return _error_response(
            code="DADOS_INVALIDOS",
            message="Os dados enviados sao invalidos.",
            status_code=422,
            details={"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        _log_event(
            "error",
            "unexpected_error",
            path=str(request.url.path),
            method=request.method,
            error_type=type(exc).__name__,
        )
        return _error_response(
            code="ERRO_INTERNO",
            message="Erro interno ao processar a requisicao.",
            status_code=500,
        )
