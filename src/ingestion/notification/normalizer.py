"""Normalizacao e filtros iniciais para notificacoes Android."""

from __future__ import annotations

from dataclasses import dataclass


ALLOWED_NOTIFICATION_PACKAGES = {
    "com.nu.production",
    "com.itau",
    "br.com.intermedium",
    "com.c6bank.app",
    "com.mercadopago.wallet",
    "com.picpay",
    "com.xp.wintrade",
    "com.google.android.apps.walletnfcrel",
    "com.samsung.android.spay",
}
ALLOWED_NOTIFICATION_PACKAGE_PREFIXES = (
    "com.itau.",
    "com.itau",
)

FINANCIAL_HINTS = (
    "r$",
    "compra",
    "pagamento",
    "pix",
    "transfer",
    "recebido",
    "deb",
)


@dataclass
class NotificacaoNormalizada:
    source: str
    package_name: str
    app_name: str
    title: str
    text: str
    sub_text: str | None
    posted_at: str
    notification_key: str


def _limpar_texto(value: str | None, *, max_chars: int) -> str:
    return (value or "").strip()[:max_chars]


def normalizar_notificacao(payload: dict) -> NotificacaoNormalizada:
    source = _limpar_texto(str(payload.get("source") or "android_notification"), max_chars=64) or "android_notification"
    package_name = _limpar_texto(payload.get("package_name"), max_chars=120)
    app_name = _limpar_texto(payload.get("app_name"), max_chars=80)
    title = _limpar_texto(payload.get("title"), max_chars=240)
    text = _limpar_texto(payload.get("text"), max_chars=1000)
    sub_text = _limpar_texto(payload.get("sub_text"), max_chars=240) or None
    posted_at = _limpar_texto(payload.get("posted_at"), max_chars=64)
    notification_key = _limpar_texto(payload.get("notification_key"), max_chars=200)

    return NotificacaoNormalizada(
        source=source,
        package_name=package_name,
        app_name=app_name,
        title=title,
        text=text,
        sub_text=sub_text,
        posted_at=posted_at,
        notification_key=notification_key,
    )


def eh_notificacao_financeira(notificacao: NotificacaoNormalizada) -> bool:
    if not notificacao.text:
        return False
    package_allowed = (
        notificacao.package_name in ALLOWED_NOTIFICATION_PACKAGES
        or any(notificacao.package_name.startswith(prefix) for prefix in ALLOWED_NOTIFICATION_PACKAGE_PREFIXES)
    )
    if not package_allowed:
        return False

    texto_base = f"{notificacao.title} {notificacao.text} {notificacao.sub_text or ''}".lower()
    return any(hint in texto_base for hint in FINANCIAL_HINTS)
