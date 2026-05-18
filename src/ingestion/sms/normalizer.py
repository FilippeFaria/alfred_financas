"""Normalizacao e filtros iniciais para SMS Android."""

from __future__ import annotations

from dataclasses import dataclass
import unicodedata


FINANCIAL_HINTS = (
    "r$",
    "compra",
    "pagamento",
    "pix",
    "transfer",
    "recebido",
    "deb",
    "credito",
    "debito",
    "cartao",
    "fatura",
)
DECLINED_TRANSACTION_HINTS = (
    "compra nao aprovada",
    "compra recusada",
    "compra negada",
    "transacao nao aprovada",
    "transacao recusada",
    "transacao negada",
    "pagamento recusado",
    "pagamento negado",
    "cartao bloqueado por tentativa",
)

SMS_BANCO_SENDER_HINTS: dict[str, tuple[str, ...]] = {
    "nubank": ("nubank", "nu pagamentos", "nu"),
    "itau": ("itau", "itaucard", "person", "personalite", "personnalite"),
    "inter": ("bancointer", "inter"),
    "c6": ("c6", "c6bank"),
    "mercado_pago": ("mercadopago", "mercado pago", "mp"),
    "picpay": ("picpay",),
}


@dataclass
class SmsNormalizado:
    source: str
    sender: str
    text: str
    received_at: str
    sms_message_id: str


def _limpar_texto(value: str | None, *, max_chars: int) -> str:
    return (value or "").strip()[:max_chars]


def _normalizar_busca(value: str) -> str:
    base = unicodedata.normalize("NFKD", value or "").lower()
    return "".join(ch for ch in base if not unicodedata.combining(ch))


def normalizar_sms(payload: dict) -> SmsNormalizado:
    source = _limpar_texto(str(payload.get("source") or "android_sms"), max_chars=64) or "android_sms"
    sender = _limpar_texto(payload.get("sender"), max_chars=120)
    text = _limpar_texto(payload.get("text"), max_chars=2000)
    received_at = _limpar_texto(payload.get("received_at"), max_chars=64)
    sms_message_id = _limpar_texto(payload.get("sms_message_id"), max_chars=200)
    return SmsNormalizado(
        source=source,
        sender=sender,
        text=text,
        received_at=received_at,
        sms_message_id=sms_message_id,
    )


def inferir_banco_por_sender(sender: str) -> str | None:
    base = _normalizar_busca(sender or "")
    if not base:
        return None
    for banco_id, aliases in SMS_BANCO_SENDER_HINTS.items():
        if any(_normalizar_busca(alias) in base for alias in aliases):
            return banco_id
    return None


def inferir_banco_por_texto(texto: str) -> str | None:
    base = _normalizar_busca(texto or "")
    if not base:
        return None
    for banco_id, aliases in SMS_BANCO_SENDER_HINTS.items():
        if any(_normalizar_busca(alias) in base for alias in aliases):
            return banco_id
    return None


def eh_sms_financeiro(sms: SmsNormalizado, *, bancos_habilitados: list[str]) -> bool:
    if not sms.text:
        return False
    banco = inferir_banco_por_sender(sms.sender) or inferir_banco_por_texto(sms.text)
    if banco is None or banco not in set(bancos_habilitados):
        return False
    texto = _normalizar_busca(sms.text)
    if any(hint in texto for hint in DECLINED_TRANSACTION_HINTS):
        return False
    return any(hint in texto for hint in FINANCIAL_HINTS)
