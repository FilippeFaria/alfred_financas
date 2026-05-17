"""Parser e heuristicas de SMS Android para transacoes."""

from __future__ import annotations

import re
from datetime import datetime

from src.ingestion.sms.normalizer import SmsNormalizado, inferir_banco_por_sender


_BANCO_CONTA_MAP = {
    "nubank": "Nubank",
    "itau": "Itaú CC",
    "inter": "Inter",
    "c6": "C6Invest",
    "mercado_pago": "99Pay",
    "picpay": "99Pay",
}


def montar_texto_sms(sms: SmsNormalizado) -> str:
    partes = [
        "Origem: SMS Android",
        f"Remetente: {sms.sender}",
        f"Texto: {sms.text}",
    ]
    if sms.received_at:
        partes.append(f"Horario: {sms.received_at}")
    return " | ".join(partes)


def inferir_tipo_por_texto(texto: str) -> str | None:
    base = (texto or "").lower()
    if "pix recebido" in base or "recebido" in base:
        return "Receita"
    if "pagamento de fatura" in base or "fatura" in base:
        return "Pagamento de Cartão"
    if "transfer" in base and ("enviado" in base or "enviad" in base):
        return "Transferência"
    if "compra" in base or ("pagamento" in base and "receb" not in base):
        return "Despesa"
    return None


def extrair_valor(texto: str) -> float | None:
    def _parse_numero_monetario(bruto: str) -> float | None:
        token = (bruto or "").strip().replace(" ", "")
        if not token:
            return None

        if "," in token:
            normalizado = token.replace(".", "").replace(",", ".")
        else:
            qtd_pontos = token.count(".")
            if qtd_pontos == 0:
                normalizado = token
            elif qtd_pontos == 1:
                inteiro, frac = token.split(".")
                if len(frac) == 2:
                    normalizado = f"{inteiro}.{frac}"
                elif len(frac) == 3:
                    normalizado = f"{inteiro}{frac}"
                else:
                    normalizado = token.replace(".", "")
            else:
                partes = token.split(".")
                if len(partes[-1]) == 2:
                    normalizado = f"{''.join(partes[:-1])}.{partes[-1]}"
                else:
                    normalizado = "".join(partes)

        try:
            valor = float(normalizado)
            return valor if valor > 0 else None
        except ValueError:
            return None

    padroes = [
        r"r\$\s*([0-9\.\,]+)",
        r"valor\s*de\s*([0-9\.\,]+)",
    ]
    texto_lower = (texto or "").lower()
    for padrao in padroes:
        match = re.search(padrao, texto_lower, flags=re.IGNORECASE)
        if not match:
            continue
        valor = _parse_numero_monetario(match.group(1))
        if valor is not None:
            return valor
    return None


def inferir_nome_estabelecimento(texto: str) -> str | None:
    padroes = [
        r"\bem\s+([a-z0-9\-\_\s\.]{3,})",
        r"\bno\s+([a-z0-9\-\_\s\.]{3,})",
        r"\bpara\s+([a-z0-9\-\_\s\.]{3,})",
    ]
    texto_limpo = (texto or "").strip()
    for padrao in padroes:
        match = re.search(padrao, texto_limpo, flags=re.IGNORECASE)
        if not match:
            continue
        nome = match.group(1).strip(" .,-")
        nome = re.split(r"(cartao final|cartao|ref:|id:)", nome, flags=re.IGNORECASE)[0].strip()
        if nome:
            return nome.upper()
    if texto_limpo:
        return f"Lancamento {texto_limpo[:40]}".strip()
    return None


def inferir_conta(sender: str, *, cartao_por_ultimos4: dict[str, str], texto: str) -> str | None:
    ultimos4 = extrair_ultimos4_cartao(texto)
    if ultimos4:
        cartao = resolver_cartao_por_ultimos4(ultimos4, cartao_por_ultimos4=cartao_por_ultimos4)
        if cartao:
            return cartao
    banco = inferir_banco_por_sender(sender)
    if banco and banco in _BANCO_CONTA_MAP:
        return _BANCO_CONTA_MAP[banco]
    return None


def extrair_ultimos4_cartao(texto: str) -> str | None:
    base = (texto or "").lower()
    patterns = (
        r"final\s+(\d{4})",
        r"cart[aã]o\s+\*+(\d{4})",
        r"cart[aã]o\s+(\d{4})",
        r"\b(\d{4})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, base, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def resolver_cartao_por_ultimos4(ultimos4: str, *, cartao_por_ultimos4: dict[str, str]) -> str | None:
    alvo = (ultimos4 or "").strip()
    if not alvo:
        return None
    for cartao, sufixo in cartao_por_ultimos4.items():
        if str(sufixo).strip() == alvo:
            return str(cartao).strip() or None
    return None


def parse_received_at_iso(received_at: str) -> str | None:
    raw = (received_at or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).isoformat()
    except ValueError:
        return None
