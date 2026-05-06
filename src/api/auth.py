"""Camada de autenticacao opcional para preparar JWT futuro."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, Request


@dataclass
class UserContext:
    is_authenticated: bool
    auth_scheme: str | None = None
    token_preview: str | None = None
    user_id: str | None = None


def parse_authorization_header(authorization: str | None) -> UserContext:
    if not authorization:
        return UserContext(is_authenticated=False)

    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2:
        return UserContext(is_authenticated=False, auth_scheme="invalid")

    scheme, token = parts[0], parts[1].strip()
    if not token:
        return UserContext(is_authenticated=False, auth_scheme=scheme.lower())

    preview = f"{token[:8]}..." if len(token) > 8 else token
    return UserContext(
        is_authenticated=True,
        auth_scheme=scheme.lower(),
        token_preview=preview,
        user_id=None,  # reservado para claims de JWT futuro
    )


async def auth_context_middleware(request: Request, call_next):
    authorization = request.headers.get("Authorization")
    request.state.user_context = parse_authorization_header(authorization)
    response = await call_next(request)
    return response


def get_current_user_optional(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> UserContext:
    # Header injetado para deixar contrato explicito e documentado no OpenAPI.
    if hasattr(request.state, "user_context"):
        return request.state.user_context
    return parse_authorization_header(authorization)
