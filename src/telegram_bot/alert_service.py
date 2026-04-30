from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram.ext import Application, CallbackContext

from src.config import (
    ALERT_STATE_FILE,
    TELEGRAM_ALERT_CHAT_IDS,
    TELEGRAM_ALERT_SCHEDULES,
    TELEGRAM_ALERT_TEST_MESSAGE,
    TELEGRAM_ALERT_TEST_MODE,
    TELEGRAM_ALERT_TIMEZONE,
)
from src.telegram_bot.alerts import Alerta, ContextoAlertas, construir_alertas
from src.telegram_bot.data_provider import carregar_dados_financeiros


LOGGER = logging.getLogger(__name__)


def parse_horario(horario: str) -> time:
    hora, minuto = horario.split(":")
    return time(hour=int(hora), minute=int(minuto), tzinfo=ZoneInfo(TELEGRAM_ALERT_TIMEZONE))


def registrar_rotina_alertas(application: Application) -> None:
    if application.job_queue is None:
        LOGGER.warning(
            "JobQueue indisponivel; alertas automaticos nao foram registrados. "
            "Instale a dependencia com suporte a agendamento: pip install \"python-telegram-bot[job-queue]\"."
        )
        return

    for horario in TELEGRAM_ALERT_SCHEDULES:
        application.job_queue.run_daily(
            callback=executar_alertas_agendados,
            time=parse_horario(horario),
            name=f"alertas_{horario.replace(':', '')}",
        )

    LOGGER.info("Rotina de alertas registrada para os horarios: %s", TELEGRAM_ALERT_SCHEDULES)


async def executar_alertas_agendados(context: CallbackContext) -> None:
    await executar_ciclo_alertas(context.application)


async def executar_ciclo_alertas(application: Application) -> list[Alerta]:
    if not TELEGRAM_ALERT_CHAT_IDS:
        LOGGER.info("Nenhum chat configurado para receber alertas automaticos.")
        return []

    referencia = datetime.now(ZoneInfo(TELEGRAM_ALERT_TIMEZONE))
    if TELEGRAM_ALERT_TEST_MODE:
        mensagem_teste = (
            f"Alertas Alfred\nReferencia: {referencia.strftime('%d/%m/%Y %H:%M')}\n\n"
            f"{TELEGRAM_ALERT_TEST_MESSAGE}"
        )
        for chat_id in TELEGRAM_ALERT_CHAT_IDS:
            await application.bot.send_message(chat_id=chat_id, text=mensagem_teste)

        LOGGER.info("Mensagem de teste enviada para %s chats.", len(TELEGRAM_ALERT_CHAT_IDS))
        return []

    df = carregar_dados_financeiros()
    alertas = construir_alertas(ContextoAlertas(df=df, referencia=referencia))
    alertas_novos = filtrar_alertas_nao_enviados(alertas, referencia)

    if not alertas_novos:
        LOGGER.info("Nenhum alerta novo para envio em %s.", referencia.isoformat())
        return []

    mensagem = montar_mensagem_alertas(alertas_novos, referencia)
    for chat_id in TELEGRAM_ALERT_CHAT_IDS:
        await application.bot.send_message(chat_id=chat_id, text=mensagem)

    persistir_alertas_enviados(alertas_novos, referencia)
    LOGGER.info("Alertas enviados para %s chats.", len(TELEGRAM_ALERT_CHAT_IDS))
    return alertas_novos


def montar_mensagem_alertas(alertas: list[Alerta], referencia: datetime) -> str:
    cabecalho = f"Alertas Alfred\nReferencia: {referencia.strftime('%d/%m/%Y %H:%M')}"
    linhas = [cabecalho, ""]
    for alerta in alertas:
        if alerta.mensagem_formatada:
            linhas.append(alerta.mensagem)
            continue
        linhas.append(f"- {alerta.titulo}: {alerta.mensagem}")
    return "\n".join(linhas)


def carregar_estado_alertas() -> dict:
    arquivo = Path(ALERT_STATE_FILE)
    if not arquivo.exists():
        return {"alertas_enviados": {}}

    try:
        return json.loads(arquivo.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        LOGGER.warning("Arquivo de estado dos alertas invalido. Reiniciando controle local.")
        return {"alertas_enviados": {}}


def filtrar_alertas_nao_enviados(alertas: list[Alerta], referencia: datetime) -> list[Alerta]:
    estado = carregar_estado_alertas().get("alertas_enviados", {})
    periodo = referencia.strftime("%Y-%m-%d")
    return [alerta for alerta in alertas if estado.get(alerta.chave) != periodo]


def persistir_alertas_enviados(alertas: list[Alerta], referencia: datetime) -> None:
    arquivo = Path(ALERT_STATE_FILE)
    arquivo.parent.mkdir(parents=True, exist_ok=True)

    estado = carregar_estado_alertas()
    enviados = estado.setdefault("alertas_enviados", {})
    periodo = referencia.strftime("%Y-%m-%d")

    for alerta in alertas:
        enviados[alerta.chave] = periodo

    estado["ultima_execucao"] = referencia.isoformat()
    estado["ultimo_lote"] = [asdict(alerta) for alerta in alertas]
    arquivo.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
