import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from .handlers import start, help_command, echo, saldo, despesas

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
    from ..config import TELEGRAM_BOT_TOKEN

    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'SEU_TOKEN_AQUI':
        raise RuntimeError(
            'Telegram token não configurado. Use a variável de ambiente TELEGRAM_BOT_TOKEN ou atualize src/config.py.'
        )

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Adicionar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("saldo", saldo))
    application.add_handler(CommandHandler("despesas", despesas))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))
    application.add_error_handler(error_handler)

    # Iniciar polling
    application.run_polling()

if __name__ == '__main__':
    main()
