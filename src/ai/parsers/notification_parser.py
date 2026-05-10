"""Parser e heuristicas de notificacao Android para transacoes."""

from __future__ import annotations

import re
from datetime import datetime

from src.ingestion.notification.normalizer import NotificacaoNormalizada


_PACKAGE_CONTA_MAP = {
    "com.nu.production": "Nubank",
    "com.itau": "Itaú CC",
    "br.com.intermedium": "Inter",
    "com.c6bank.app": "C6Invest",
    "com.mercadopago.wallet": "99Pay",
    "com.picpay": "99Pay",
}


def montar_texto_notificacao(notificacao: NotificacaoNormalizada) -> str:
    partes = [
        "Origem: notificacao Android",
        f"App: {notificacao.app_name or notificacao.package_name}",
    ]
    if notificacao.title:
        partes.append(f"Titulo: {notificacao.title}")
    partes.append(f"Texto: {notificacao.text}")
    if notificacao.sub_text:
        partes.append(f"Subtexto: {notificacao.sub_text}")
    if notificacao.posted_at:
        partes.append(f"Horario: {notificacao.posted_at}")
    return " | ".join(partes)


def inferir_tipo_por_texto(notificacao: NotificacaoNormalizada) -> str | None:
    texto = f"{notificacao.title} {notificacao.text} {notificacao.sub_text or ''}".lower()
    if "pix recebido" in texto or "recebido" in texto:
        return "Receita"
    if "pagamento de fatura" in texto or "fatura" in texto:
        return "Pagamento de Cartão"
    if "transfer" in texto and ("enviad" in texto or "enviado" in texto):
        return "Transferência"
    if "compra aprovada" in texto or "compra" in texto:
        return "Despesa"
    if "pagamento" in texto and "receb" not in texto:
        return "Despesa"
    return None


def extrair_valor(texto: str) -> float | None:
    padroes = [
        r"r\$\s*([0-9\.\,]+)",
        r"valor\s*de\s*([0-9\.\,]+)",
    ]
    texto_lower = texto.lower()
    for padrao in padroes:
        match = re.search(padrao, texto_lower, flags=re.IGNORECASE)
        if not match:
            continue
        bruto = match.group(1).replace(".", "").replace(",", ".").strip()
        try:
            valor = float(bruto)
            if valor > 0:
                return valor
        except ValueError:
            continue
    return None


def inferir_conta(notificacao: NotificacaoNormalizada) -> str | None:
    package_name = notificacao.package_name or ""
    if package_name in _PACKAGE_CONTA_MAP:
        return _PACKAGE_CONTA_MAP[package_name]
    if package_name.startswith("com.itau"):
        return "Itaú CC"
    app = (notificacao.app_name or "").lower()
    if "nubank" in app:
        return "Nubank"
    if "itau" in app or "itaú" in app:
        return "Itaú CC"
    if "inter" in app:
        return "Inter"
    return None


def inferir_nome_estabelecimento(texto: str) -> str | None:
    padroes = [
        r"\bem\s+([a-z0-9\-\_\s\.]{3,})",
        r"\bno\s+([a-z0-9\-\_\s\.]{3,})",
        r"\bpara\s+([a-z0-9\-\_\s\.]{3,})",
    ]
    texto_limpo = texto.strip()
    for padrao in padroes:
        match = re.search(padrao, texto_limpo, flags=re.IGNORECASE)
        if not match:
            continue
        nome = match.group(1).strip(" .,-")
        nome = re.split(r"(com cartao|cartao final|ref:|id:)", nome, flags=re.IGNORECASE)[0].strip()
        if nome:
            return nome.upper()
    if texto_limpo:
        return f"Lancamento {texto_limpo[:40]}".strip()
    return None


def parse_posted_at_iso(posted_at: str) -> str | None:
    raw = (posted_at or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).isoformat()
    except ValueError:
        return None
