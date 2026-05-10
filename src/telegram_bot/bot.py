import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, CommandHandler, MessageHandler, filters
from .alert_service import registrar_rotina_alertas
from .daily_report_service import registrar_rotina_informe_diario
from .handlers import (
    alertas,
    callback_pendencia,
    categorias_despesas,
    chat_id,
    despesas,
    echo,
    help_command,
    informe_diario,
    receber_audio_transacao,
    saldo,
    start,
)

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error('Ocorreu um erro no handler do Telegram', exc_info=context.error)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            'Desculpe, ocorreu um erro interno. Tente novamente em alguns instantes.'
        )


def main():
    # Obter token do config (futuramente de st.secrets ou env)
    from ..config import (
        TELEGRAM_ALERT_CHAT_IDS,
        TELEGRAM_BOT_MODE,
        TELEGRAM_BOT_TOKEN,
        TELEGRAM_DAILY_REPORT_CHAT_IDS,
        TELEGRAM_WEBHOOK_PATH,
        TELEGRAM_WEBHOOK_URL,
    )

    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'SEU_TOKEN_AQUI':
        raise RuntimeError(
            'Telegram token não configurado. Use a variável de ambiente TELEGRAM_BOT_TOKEN ou atualize src/config.py.'
        )

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    logging.info(
        "Bot inicializado. mode=%s alert_chats=%s report_chats=%s",
        TELEGRAM_BOT_MODE,
        len(TELEGRAM_ALERT_CHAT_IDS),
        len(TELEGRAM_DAILY_REPORT_CHAT_IDS),
    )

    # Adicionar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("saldo", saldo))
    application.add_handler(CommandHandler("despesas", despesas))
    application.add_handler(CommandHandler("categorias_despesas", categorias_despesas))
    application.add_handler(CommandHandler("informe_diario", informe_diario))
    application.add_handler(CommandHandler("chat_id", chat_id))
    application.add_handler(CommandHandler("alertas", alertas))
    application.add_handler(CallbackQueryHandler(callback_pendencia, pattern=r"^pendencia:"))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO | filters.Document.AUDIO, receber_audio_transacao))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))
    application.add_error_handler(error_handler)

    if application.job_queue is None:
        logging.warning(
            'JobQueue nao disponivel nesta instalacao do python-telegram-bot. '
            'Os alertas por horario nao vao funcionar ate instalar a extra "job-queue".'
        )
    else:
        logging.info('JobQueue disponivel. Alertas agendados serao registrados normalmente.')

    registrar_rotina_alertas(application)
    registrar_rotina_informe_diario(application)

    modo_execucao = TELEGRAM_BOT_MODE if TELEGRAM_BOT_MODE in {"polling", "webhook"} else "polling"
    if modo_execucao == "webhook":
        if not TELEGRAM_WEBHOOK_URL:
            raise RuntimeError(
                "Modo webhook ativo, mas TELEGRAM_WEBHOOK_URL nao foi configurada."
            )

        webhook_path = TELEGRAM_WEBHOOK_PATH.lstrip("/")
        if not webhook_path:
            raise RuntimeError(
                "TELEGRAM_WEBHOOK_PATH invalido. Use um caminho como /telegram/webhook."
            )

        webhook_url = f"{TELEGRAM_WEBHOOK_URL.rstrip('/')}/{webhook_path}"
        porta = int(os.getenv("PORT", "10000"))
        logging.info(
            "Iniciando bot em modo webhook. porta=%s path=/%s webhook_url=%s",
            porta,
            webhook_path,
            webhook_url,
        )
        application.run_webhook(
            listen="0.0.0.0",
            port=porta,
            url_path=webhook_path,
            webhook_url=webhook_url,
            drop_pending_updates=True,
        )
        return

    logging.info("Iniciando bot em modo polling.")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
