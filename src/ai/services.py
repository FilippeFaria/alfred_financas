from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Lock

from src.ai.capture_deduplication import detectar_duplicidade_captura
from src.database.connection import SessionLocal
from src.database.repositories import PendingTransactionRepository, UserRepository
from src.ingestion.notification.normalizer import eh_notificacao_financeira, normalizar_notificacao
from src.ingestion.sms.normalizer import eh_sms_financeiro, normalizar_sms
from src.services.pending_transaction_service import criar_transacao_pendente
from src.services.sms_capture_preferences_service import obter_preferencias_sms

from .parsers.audio_parser import extrair_transacao_por_audio
from .parsers.notification_parser import (
    extrair_valor,
    inferir_conta,
    inferir_nome_estabelecimento,
    inferir_tipo_por_texto,
    montar_texto_notificacao,
    parse_posted_at_iso,
)
from .parsers.sms_parser import (
    extrair_ultimos4_cartao,
    extrair_valor as extrair_valor_sms,
    inferir_conta as inferir_conta_sms,
    inferir_nome_estabelecimento as inferir_nome_sms,
    inferir_tipo_por_texto as inferir_tipo_sms,
    montar_texto_sms,
    parse_received_at_iso,
)
from .parsers.text_parser import extrair_transacao_por_texto
from .schemas import EntradaAudio, EntradaTexto, SugestaoTransacaoResultado
from .validators import validar_transacao_sugerida


@dataclass
class NotificacaoTransacaoResultado:
    created: bool
    duplicate: bool
    pending_transaction_id: str | None = None
    confidence: float | None = None
    message: str = ""
    duplicate_reason: str | None = None
    transacao_sugerida: dict | None = None


_NOTIFICATION_CREATION_LOCK = Lock()


def sugerir_transacao_por_texto(texto: str, *, data_referencia: datetime | None = None) -> SugestaoTransacaoResultado:
    entrada = EntradaTexto(texto=texto, data_referencia=data_referencia)
    sugestao = extrair_transacao_por_texto(entrada)
    avisos, campos_incertos = validar_transacao_sugerida(sugestao)
    return SugestaoTransacaoResultado(
        sugestao=sugestao,
        confianca=sugestao.confianca,
        pendencias=campos_incertos,
        avisos_validacao=avisos,
        origem="texto",
    )


def sugerir_transacao_por_audio(caminho_arquivo: str, *, data_referencia: datetime | None = None) -> SugestaoTransacaoResultado:
    entrada = EntradaAudio(caminho_arquivo=caminho_arquivo, data_referencia=data_referencia)
    sugestao = extrair_transacao_por_audio(entrada)
    avisos, campos_incertos = validar_transacao_sugerida(sugestao)
    return SugestaoTransacaoResultado(
        sugestao=sugestao,
        confianca=sugestao.confianca,
        pendencias=campos_incertos,
        avisos_validacao=avisos,
        origem="audio",
        texto_transcrito=sugestao.transcricao,
    )


def criar_pendencia_por_texto(texto: str, *, data_referencia: datetime | None = None):
    resultado = sugerir_transacao_por_texto(texto, data_referencia=data_referencia)
    payload = resultado.sugestao.model_dump(mode="json")
    return criar_transacao_pendente(
        source="texto",
        raw_text=resultado.sugestao.descricao_original,
        transcription=None,
        suggested_payload=payload,
        confidence=resultado.confianca,
    )


def criar_pendencia_por_audio(caminho_arquivo: str, *, data_referencia: datetime | None = None):
    resultado = sugerir_transacao_por_audio(caminho_arquivo, data_referencia=data_referencia)
    payload = resultado.sugestao.model_dump(mode="json")
    return criar_transacao_pendente(
        source="audio",
        raw_text=resultado.sugestao.descricao_original,
        transcription=resultado.sugestao.transcricao,
        suggested_payload=payload,
        confidence=resultado.confianca,
    )


def _criar_pendencia_com_deduplicacao_captura(
    *,
    source: str,
    raw_text: str,
    sugestao_payload: dict,
    confidence: float,
    event_key: str | None,
    occurred_at_iso: str | None,
    ignorar_duplicata: bool,
) -> NotificacaoTransacaoResultado:
    event_key_norm = (event_key or "").strip()
    with _NOTIFICATION_CREATION_LOCK:
        with SessionLocal() as db:
            user = UserRepository(db).get_or_create_default()
            pending_repo = PendingTransactionRepository(db)
            duplicate_check = detectar_duplicidade_captura(
                pending_repo=pending_repo,
                user_id=user.id,
                source=source,
                event_key=event_key_norm,
                sugestao_payload=sugestao_payload,
                occurred_at_iso=occurred_at_iso,
            )

        sugestao_payload["capture_metadata"] = {
            "channel": source,
            "event_key": event_key_norm or None,
            "occurred_at": occurred_at_iso,
            "fingerprint": duplicate_check.fingerprint,
        }
        if duplicate_check.is_duplicate and not ignorar_duplicata:
            return NotificacaoTransacaoResultado(
                created=False,
                duplicate=True,
                message=duplicate_check.reason or "Captura automatica duplicada ignorada.",
                duplicate_reason=duplicate_check.reason,
                transacao_sugerida=sugestao_payload,
            )

        pendencia = criar_transacao_pendente(
            source=source,
            raw_text=raw_text,
            transcription=None,
            suggested_payload=sugestao_payload,
            confidence=float(sugestao_payload.get("confianca") or confidence),
        )

    return NotificacaoTransacaoResultado(
        created=True,
        duplicate=False,
        pending_transaction_id=pendencia.id,
        confidence=float(confidence),
        message="Transacao pendente criada com sucesso.",
        transacao_sugerida=sugestao_payload,
    )


def criar_pendencia_por_notificacao(payload: dict) -> NotificacaoTransacaoResultado:
    notificacao = normalizar_notificacao(payload)
    ignorar_duplicata = bool(payload.get("ignorar_duplicata", False))
    data_criacao_pendencia_iso = datetime.now().isoformat(timespec="seconds")

    if not eh_notificacao_financeira(notificacao):
        return NotificacaoTransacaoResultado(
            created=False,
            duplicate=False,
            message="Notificacao ignorada por nao conter indicio financeiro.",
        )

    tipo_heuristico = inferir_tipo_por_texto(notificacao)
    conta_heuristica = inferir_conta(notificacao)
    valor_heuristico = extrair_valor(notificacao.text)
    nome_heuristico = inferir_nome_estabelecimento(notificacao.text)
    data_postada_iso = parse_posted_at_iso(notificacao.posted_at)

    texto_para_ia = montar_texto_notificacao(notificacao)
    resultado = sugerir_transacao_por_texto(texto_para_ia)
    sugestao_payload = resultado.sugestao.model_dump(mode="json")

    if not sugestao_payload.get("tipo") and tipo_heuristico:
        sugestao_payload["tipo"] = tipo_heuristico
    if not sugestao_payload.get("conta") and conta_heuristica:
        sugestao_payload["conta"] = conta_heuristica
    if not sugestao_payload.get("nome") and nome_heuristico:
        sugestao_payload["nome"] = nome_heuristico
    if not sugestao_payload.get("data") and data_postada_iso:
        sugestao_payload["data"] = data_postada_iso
    if valor_heuristico not in (None, "", 0):
        sugestao_payload["valor"] = valor_heuristico
    elif sugestao_payload.get("valor") in (None, "", 0):
        sugestao_payload["valor"] = valor_heuristico

    # Em capturas por notificacao, a transacao usa o horario de criacao da pendencia.
    sugestao_payload["data"] = data_criacao_pendencia_iso

    if sugestao_payload.get("valor") in (None, "", 0):
        return NotificacaoTransacaoResultado(
            created=False,
            duplicate=False,
            message="Notificacao ignorada por nao conter valor identificavel.",
        )

    sugestao_payload["source"] = "android_notification"
    sugestao_payload["raw_text"] = notificacao.text
    sugestao_payload["notificacao"] = {
        "source": notificacao.source,
        "package_name": notificacao.package_name,
        "app_name": notificacao.app_name,
        "title": notificacao.title or None,
        "text": notificacao.text,
        "sub_text": notificacao.sub_text,
        "posted_at": notificacao.posted_at or None,
        "notification_key": notificacao.notification_key or None,
    }
    return _criar_pendencia_com_deduplicacao_captura(
        source="android_notification",
        raw_text=notificacao.text,
        sugestao_payload=sugestao_payload,
        confidence=float(resultado.confianca),
        event_key=notificacao.notification_key,
        occurred_at_iso=data_postada_iso,
        ignorar_duplicata=ignorar_duplicata,
    )


def criar_pendencia_por_sms(payload: dict) -> NotificacaoTransacaoResultado:
    sms = normalizar_sms(payload)
    ignorar_duplicata = bool(payload.get("ignorar_duplicata", False))
    data_criacao_pendencia_iso = datetime.now().isoformat(timespec="seconds")
    preferencias = obter_preferencias_sms()

    if not bool(preferencias.get("sms_enabled", False)):
        return NotificacaoTransacaoResultado(
            created=False,
            duplicate=False,
            message="Captura por SMS desativada nas preferencias.",
        )

    bancos_habilitados = [str(item) for item in preferencias.get("bancos_selecionados", [])]
    if not eh_sms_financeiro(sms, bancos_habilitados=bancos_habilitados):
        return NotificacaoTransacaoResultado(
            created=False,
            duplicate=False,
            message="SMS ignorado por nao corresponder aos filtros financeiros configurados.",
        )

    cartao_por_ultimos4 = {
        str(cartao): str(ultimos4)
        for cartao, ultimos4 in dict(preferencias.get("mapeamento_cartao_ultimos4", {})).items()
    }
    tipo_heuristico = inferir_tipo_sms(sms.text)
    valor_heuristico = extrair_valor_sms(sms.text)
    nome_heuristico = inferir_nome_sms(sms.text)
    conta_heuristica = inferir_conta_sms(
        sms.sender,
        cartao_por_ultimos4=cartao_por_ultimos4,
        texto=sms.text,
    )
    ultimos4_detectado = extrair_ultimos4_cartao(sms.text)
    data_recebimento_iso = parse_received_at_iso(sms.received_at)

    texto_para_ia = montar_texto_sms(sms)
    resultado = sugerir_transacao_por_texto(texto_para_ia)
    sugestao_payload = resultado.sugestao.model_dump(mode="json")
    if not sugestao_payload.get("tipo") and tipo_heuristico:
        sugestao_payload["tipo"] = tipo_heuristico
    if not sugestao_payload.get("conta") and conta_heuristica:
        sugestao_payload["conta"] = conta_heuristica
    if not sugestao_payload.get("nome") and nome_heuristico:
        sugestao_payload["nome"] = nome_heuristico
    if not sugestao_payload.get("data") and data_recebimento_iso:
        sugestao_payload["data"] = data_recebimento_iso
    if valor_heuristico not in (None, "", 0):
        sugestao_payload["valor"] = valor_heuristico
    elif sugestao_payload.get("valor") in (None, "", 0):
        sugestao_payload["valor"] = valor_heuristico

    sugestao_payload["data"] = data_criacao_pendencia_iso
    if sugestao_payload.get("valor") in (None, "", 0):
        return NotificacaoTransacaoResultado(
            created=False,
            duplicate=False,
            message="SMS ignorado por nao conter valor identificavel.",
        )

    sugestao_payload["source"] = "android_sms"
    sugestao_payload["raw_text"] = sms.text
    sugestao_payload["sms"] = {
        "source": sms.source,
        "sender": sms.sender,
        "text": sms.text,
        "received_at": sms.received_at,
        "sms_message_id": sms.sms_message_id,
        "ultimos4_detectado": ultimos4_detectado,
    }

    return _criar_pendencia_com_deduplicacao_captura(
        source="android_sms",
        raw_text=sms.text,
        sugestao_payload=sugestao_payload,
        confidence=float(resultado.confianca),
        event_key=sms.sms_message_id,
        occurred_at_iso=data_recebimento_iso,
        ignorar_duplicata=ignorar_duplicata,
    )
