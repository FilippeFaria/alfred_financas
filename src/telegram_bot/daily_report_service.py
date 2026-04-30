from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram.ext import Application, CallbackContext

from src.config import (
    DAILY_REPORT_STATE_FILE,
    TELEGRAM_DAILY_REPORT_CHAT_IDS,
    TELEGRAM_DAILY_REPORT_SCHEDULE,
    TELEGRAM_DAILY_REPORT_TEST_MODE,
    TELEGRAM_ALERT_TIMEZONE,
)
from src.telegram_bot.alert_service import parse_horario
from src.telegram_bot.daily_report import montar_informe_diario
from src.telegram_bot.data_provider import carregar_dados_financeiros, carregar_valores_desejados


LOGGER = logging.getLogger(__name__)


def registrar_rotina_informe_diario(application: Application) -> None:
    if application.job_queue is None:
        LOGGER.warning("JobQueue indisponivel; informe diario nao foi registrado.")
        return

    application.job_queue.run_daily(
        callback=executar_informe_diario_agendado,
        time=parse_horario(TELEGRAM_DAILY_REPORT_SCHEDULE),
        name="informe_diario",
    )
    LOGGER.info("Informe diario registrado para %s.", TELEGRAM_DAILY_REPORT_SCHEDULE)


async def executar_informe_diario_agendado(context: CallbackContext) -> None:
    await executar_envio_informe_diario(context.application)


def gerar_mensagem_informe_diario(referencia: datetime | None = None) -> str:
    referencia = referencia or datetime.now(ZoneInfo(TELEGRAM_ALERT_TIMEZONE))
    df = carregar_dados_financeiros()
    valores_desejados = carregar_valores_desejados()
    return montar_informe_diario(df, valores_desejados, referencia)


async def executar_envio_informe_diario(application: Application) -> bool:
    if not TELEGRAM_DAILY_REPORT_CHAT_IDS:
        LOGGER.info("Nenhum chat configurado para receber o informe diario.")
        return False

    referencia = datetime.now(ZoneInfo(TELEGRAM_ALERT_TIMEZONE))
    if not TELEGRAM_DAILY_REPORT_TEST_MODE and informe_diario_ja_enviado(referencia):
        LOGGER.info("Informe diario ja enviado em %s.", referencia.strftime("%Y-%m-%d"))
        return False
    if TELEGRAM_DAILY_REPORT_TEST_MODE:
        LOGGER.info(
            "TELEGRAM_DAILY_REPORT_TEST_MODE ativo; a trava diaria do informe sera ignorada em %s.",
            referencia.strftime("%Y-%m-%d"),
        )

    mensagem = gerar_mensagem_informe_diario(referencia)
    for chat_id in TELEGRAM_DAILY_REPORT_CHAT_IDS:
        await application.bot.send_message(chat_id=chat_id, text=mensagem)

    persistir_envio_informe_diario(referencia)
    LOGGER.info("Informe diario enviado para %s chats.", len(TELEGRAM_DAILY_REPORT_CHAT_IDS))
    return True


def carregar_estado_informe_diario() -> dict:
    arquivo = Path(DAILY_REPORT_STATE_FILE)
    if not arquivo.exists():
        return {"ultima_data_enviada": None}

    try:
        return json.loads(arquivo.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        LOGGER.warning("Arquivo de estado do informe diario invalido. Reiniciando controle local.")
        return {"ultima_data_enviada": None}


def informe_diario_ja_enviado(referencia: datetime) -> bool:
    estado = carregar_estado_informe_diario()
    return estado.get("ultima_data_enviada") == referencia.strftime("%Y-%m-%d")


def persistir_envio_informe_diario(referencia: datetime) -> None:
    arquivo = Path(DAILY_REPORT_STATE_FILE)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    estado = {
        "ultima_data_enviada": referencia.strftime("%Y-%m-%d"),
        "ultima_execucao": referencia.isoformat(),
    }
    arquivo.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
