from datetime import date
from io import BytesIO
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from src.analytics.calculations import adicionar_anomes, calcular_saldo, calcular_despesa_total
from src.analytics.charts import montar_grafico_categorias_despesas
from src.config import TELEGRAM_CHAT_NOMES
from src.telegram_bot.alert_service import executar_ciclo_alertas
from src.telegram_bot.daily_report_service import gerar_mensagem_informe_diario
from src.telegram_bot.data_provider import carregar_dados_financeiros

ROOT_PATH = Path(__file__).resolve().parents[2]


def format_real(value: float) -> str:
    text = f"{value:,.2f}"
    return "R$ " + text.replace(",", "X").replace(".", ",").replace("X", ".")


def obter_nome_conversa(update: Update) -> str | None:
    if not update.effective_chat:
        return None

    return TELEGRAM_CHAT_NOMES.get(update.effective_chat.id)


def montar_saudacao(update: Update) -> str:
    nome_conversa = obter_nome_conversa(update)
    return f"Ola, {nome_conversa}!" if nome_conversa else "Ola!"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id if update.effective_chat else "indisponivel"
    print(f"[Alfred Bot] Chat ID capturado no /start: {chat_id}")
    await update.message.reply_text(
        f"{montar_saudacao(update)} Eu sou o Alfred Bot.\n"
        "Use /saldo para ver seus saldos atuais e /despesas para ver seu gasto mensal.\n"
        "Envie /help para mais comandos.\n\n"
        f"Seu chat ID e: {chat_id}"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"{montar_saudacao(update)}\n"
        "Comandos disponiveis:\n"
        "/saldo - Ver saldo por conta e total\n"
        "/despesas - Ver despesas do mes atual e comparacao com o mes anterior\n"
        "/categorias_despesas - Ver grafico de categorias de despesas do mes atual\n"
        "/informe_diario - Gerar o resumo diario do fluxo\n"
        "/chat_id - Mostrar o ID desta conversa\n"
        "/alertas - Executar uma checagem manual de alertas\n"
        "/help - Mostrar esta mensagem"
    )


async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id_atual = update.effective_chat.id if update.effective_chat else "indisponivel"
    print(f"[Alfred Bot] Chat ID solicitado manualmente: {chat_id_atual}")
    nome_conversa = obter_nome_conversa(update)
    complemento = f"\nNome configurado: {nome_conversa}" if nome_conversa else ""
    await update.message.reply_text(f"Chat ID desta conversa: {chat_id_atual}{complemento}")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"{montar_saudacao(update)} Voce disse: {update.message.text}")


async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        df = carregar_dados_financeiros()
        saldo_s = calcular_saldo(df)
        total = float(saldo_s.sum()) if not saldo_s.empty else 0.0
        lines = [f"{conta}: {format_real(valor)}" for conta, valor in saldo_s.items()]
        texto = f"*Saldo total:* {format_real(total)}\n\n" + "\n".join(lines)
        await update.message.reply_text(texto)
    except Exception as exc:
        await update.message.reply_text(
            "Erro ao carregar dados financeiros. Verifique credentials.json, o CSV local ou as configuracoes do bot.\n"
            f"Erro: {exc}"
        )


async def despesas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        df = carregar_dados_financeiros()
        df = df[(df["desconsiderar"] == False) & (df["Tipo"] == "Despesa")]
        anome = int(date.today().strftime("%Y%m"))
        metricas = calcular_despesa_total(df, anome)

        texto = (
            f"*Despesas {metricas['label_curr']}:* {format_real(metricas['gasto_atual'])}\n"
            f"*Mes anterior ({metricas['label_prev']}):* {format_real(metricas['gasto_anterior'])}\n"
            f"*Media ultimos 3 meses:* {format_real(metricas['gasto_3m_media'])}\n"
        )
        if metricas["delta_atual"] is not None:
            texto += f"Variacao vs mes anterior: {metricas['delta_atual'] * 100:.1f}%\n"
        if metricas["delta_3m"] is not None:
            texto += f"Variacao vs trimestre anterior: {metricas['delta_3m'] * 100:.1f}%"

        await update.message.reply_text(texto)
    except Exception as exc:
        await update.message.reply_text(
            "Erro ao calcular despesas. Verifique se os dados estao disponiveis e tente novamente.\n"
            f"Erro: {exc}"
        )


async def categorias_despesas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        df = carregar_dados_financeiros()
        df = adicionar_anomes(df)
        anome = int(date.today().strftime("%Y%m"))
        fig, metricas = montar_grafico_categorias_despesas(df, anome, str(ROOT_PATH))

        caption = (
            f"Categorias de despesas {anome}\n"
            f"Total real: {format_real(metricas['total_real'])}\n"
            f"Total desejado: {format_real(metricas['total_desejado'])}\n"
            f"Diferenca: {format_real(metricas['diferenca'])}"
        )

        try:
            imagem = fig.to_image(format="png", width=1400, height=900, scale=2)
            await update.message.reply_photo(photo=BytesIO(imagem), caption=caption)
            return
        except Exception:
            html = fig.to_html(full_html=True, include_plotlyjs="cdn").encode("utf-8")
            arquivo = BytesIO(html)
            arquivo.name = f"categorias_despesas_{anome}.html"
            await update.message.reply_document(document=arquivo, caption=caption)
    except Exception as exc:
        await update.message.reply_text(
            "Erro ao gerar o grafico de categorias de despesas.\n"
            f"Erro: {exc}"
        )


async def alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        alertas_enviados = await executar_ciclo_alertas(context.application)
        if alertas_enviados:
            await update.message.reply_text(
                f"Checagem concluida. {len(alertas_enviados)} alerta(s) novo(s) foram enviados."
            )
        else:
            await update.message.reply_text(
                "Checagem concluida. Nenhum alerta novo foi identificado."
            )
    except Exception as exc:
        await update.message.reply_text(
            "Erro ao executar a checagem de alertas.\n"
            f"Erro: {exc}"
        )


async def informe_diario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        mensagem = gerar_mensagem_informe_diario()
        await update.message.reply_text(mensagem)
    except Exception as exc:
        await update.message.reply_text(
            "Erro ao gerar o informe diario.\n"
            f"Erro: {exc}"
        )
