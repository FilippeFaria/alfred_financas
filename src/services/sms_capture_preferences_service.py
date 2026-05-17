"""Servico de preferencias de captura automatica por SMS."""

from __future__ import annotations

import re

from src.api.errors import ApiServiceError
from src.config import CARTOES_PAGAMENTO, CARTOES_PAGAMENTO_DESPESA, CARTOES_PAGAMENTO_TRANSFERENCIA
from src.database.connection import SessionLocal
from src.database.repositories import SmsCapturePreferenceRepository, UserRepository


SMS_BANCOS_CATALOGO = [
    {"id": "nubank", "nome": "Nubank"},
    {"id": "itau", "nome": "Itaú"},
    {"id": "inter", "nome": "Inter"},
    {"id": "c6", "nome": "C6"},
    {"id": "mercado_pago", "nome": "Mercado Pago"},
    {"id": "picpay", "nome": "PicPay"},
]
SMS_BANCOS_IDS_VALIDOS = {item["id"] for item in SMS_BANCOS_CATALOGO}
_ULTIMOS4_PATTERN = re.compile(r"^\d{4}$")


def _catalogo_cartoes() -> list[str]:
    itens = {
        *(item.strip() for item in CARTOES_PAGAMENTO if item and item.strip()),
        *(item.strip() for item in CARTOES_PAGAMENTO_TRANSFERENCIA if item and item.strip()),
        *(item.strip() for item in CARTOES_PAGAMENTO_DESPESA if item and item.strip()),
    }
    return sorted(itens)


def _serializar_resposta(*, sms_enabled: bool, bancos_selecionados: list[str], mapeamento_cartao_ultimos4: dict[str, str]) -> dict:
    return {
        "sms_enabled": bool(sms_enabled),
        "bancos_selecionados": list(bancos_selecionados),
        "mapeamento_cartao_ultimos4": dict(mapeamento_cartao_ultimos4),
        "catalogo_bancos": SMS_BANCOS_CATALOGO,
        "catalogo_cartoes": _catalogo_cartoes(),
    }


def obter_preferencias_sms() -> dict:
    with SessionLocal() as db:
        user = UserRepository(db).get_or_create_default()
        repo = SmsCapturePreferenceRepository(db)
        item = repo.get_or_create_default(user_id=user.id)
        db.commit()
        return _serializar_resposta(
            sms_enabled=bool(item.sms_enabled),
            bancos_selecionados=[str(v) for v in (item.bancos_selecionados or []) if str(v).strip()],
            mapeamento_cartao_ultimos4={str(k): str(v) for k, v in (item.mapeamento_cartao_ultimos4 or {}).items()},
        )


def salvar_preferencias_sms(
    *,
    sms_enabled: bool,
    bancos_selecionados: list[str],
    mapeamento_cartao_ultimos4: dict[str, str],
) -> dict:
    cartoes_validos = set(_catalogo_cartoes())
    bancos_norm = []
    for banco in bancos_selecionados:
        valor = str(banco or "").strip()
        if not valor:
            continue
        if valor not in SMS_BANCOS_IDS_VALIDOS:
            raise ApiServiceError(
                code="DADOS_INVALIDOS",
                message=f"Banco invalido para captura SMS: {valor}.",
                status_code=400,
            )
        bancos_norm.append(valor)
    bancos_norm = sorted(set(bancos_norm))

    mapeamento_norm: dict[str, str] = {}
    ultimos4_usados: set[str] = set()
    for cartao, ultimos4 in mapeamento_cartao_ultimos4.items():
        cartao_norm = str(cartao or "").strip()
        ultimos4_norm = str(ultimos4 or "").strip()
        if not cartao_norm:
            continue
        if cartao_norm not in cartoes_validos:
            raise ApiServiceError(
                code="DADOS_INVALIDOS",
                message=f"Cartao invalido no mapeamento SMS: {cartao_norm}.",
                status_code=400,
            )
        if not ultimos4_norm:
            continue
        if not _ULTIMOS4_PATTERN.match(ultimos4_norm):
            raise ApiServiceError(
                code="DADOS_INVALIDOS",
                message=f"Ultimos 4 digitos invalidos para {cartao_norm}.",
                status_code=400,
            )
        if ultimos4_norm in ultimos4_usados:
            raise ApiServiceError(
                code="DADOS_INVALIDOS",
                message=f"O sufixo {ultimos4_norm} nao pode ser usado em mais de um cartao.",
                status_code=400,
            )
        ultimos4_usados.add(ultimos4_norm)
        mapeamento_norm[cartao_norm] = ultimos4_norm

    with SessionLocal() as db:
        user = UserRepository(db).get_or_create_default()
        repo = SmsCapturePreferenceRepository(db)
        item = repo.get_or_create_default(user_id=user.id)
        atualizado = repo.update_preferences(
            item=item,
            sms_enabled=bool(sms_enabled),
            bancos_selecionados=bancos_norm,
            mapeamento_cartao_ultimos4=mapeamento_norm,
        )
        db.commit()
        return _serializar_resposta(
            sms_enabled=bool(atualizado.sms_enabled),
            bancos_selecionados=[str(v) for v in (atualizado.bancos_selecionados or []) if str(v).strip()],
            mapeamento_cartao_ultimos4={
                str(k): str(v) for k, v in (atualizado.mapeamento_cartao_ultimos4 or {}).items()
            },
        )
