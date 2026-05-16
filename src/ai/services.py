from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Lock

from src.ingestion.notification.deduplicator import NotificationDeduplicator
from src.ingestion.notification.normalizer import eh_notificacao_financeira, normalizar_notificacao
from src.services.pending_transaction_service import (
    buscar_pendencia_pendente_por_notification_key,
    criar_transacao_pendente,
)

from .parsers.audio_parser import extrair_transacao_por_audio
from .parsers.notification_parser import (
    extrair_valor,
    inferir_conta,
    inferir_nome_estabelecimento,
    inferir_tipo_por_texto,
    montar_texto_notificacao,
    parse_posted_at_iso,
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


def criar_pendencia_por_notificacao(payload: dict) -> NotificacaoTransacaoResultado:
    notificacao = normalizar_notificacao(payload)
    deduplicador = NotificationDeduplicator()
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
    if sugestao_payload.get("valor") in (None, "", 0):
        sugestao_payload["valor"] = valor_heuristico

    # Em capturas por notificacao, a transacao usa o horario de criacao da pendencia.
    sugestao_payload["data"] = data_criacao_pendencia_iso

    valor_final = sugestao_payload.get("valor")
    nome_final = str(sugestao_payload.get("nome") or nome_heuristico or "").strip()

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

    with _NOTIFICATION_CREATION_LOCK:
        pendencia_existente = buscar_pendencia_pendente_por_notification_key(
            notification_key=notificacao.notification_key,
        )
        if pendencia_existente is not None and not ignorar_duplicata:
            return NotificacaoTransacaoResultado(
                created=False,
                duplicate=True,
                pending_transaction_id=pendencia_existente.id,
                confidence=pendencia_existente.confidence,
                message="Notificacao ja possui pendencia aguardando revisao.",
                duplicate_reason="Pendencia existente para a mesma notification_key.",
                transacao_sugerida=pendencia_existente.suggested_payload,
            )

        duplicate_check = deduplicador.check_duplicate(
            notification_key=notificacao.notification_key,
            package_name=notificacao.package_name,
            valor=float(valor_final),
            nome_estabelecimento=nome_final,
            posted_at_iso=data_postada_iso,
        )
        if duplicate_check.is_duplicate and not ignorar_duplicata:
            return NotificacaoTransacaoResultado(
                created=False,
                duplicate=True,
                message=duplicate_check.reason or "Notificacao duplicada ignorada.",
                duplicate_reason=duplicate_check.reason,
                transacao_sugerida=sugestao_payload,
            )

        pendencia = criar_transacao_pendente(
            source="android_notification",
            raw_text=notificacao.text,
            transcription=None,
            suggested_payload=sugestao_payload,
            confidence=float(sugestao_payload.get("confianca") or resultado.confianca),
        )

        deduplicador.mark_processed(
            notification_key=notificacao.notification_key,
            package_name=notificacao.package_name,
            valor=float(valor_final),
            nome_estabelecimento=nome_final,
            posted_at_iso=data_postada_iso,
        )

    return NotificacaoTransacaoResultado(
        created=True,
        duplicate=False,
        pending_transaction_id=pendencia.id,
        confidence=float(resultado.confianca),
        message=(
            "Transacao pendente criada com sucesso"
            if not duplicate_check.is_duplicate
            else "Transacao pendente criada mesmo com alerta de duplicidade."
        ),
        duplicate_reason=duplicate_check.reason if duplicate_check.is_duplicate else None,
        transacao_sugerida=sugestao_payload,
    )
