from datetime import date
from io import BytesIO
import logging
from pathlib import Path
import os
import tempfile

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.analytics.calculations import adicionar_anomes, calcular_saldo, calcular_despesa_total
from src.analytics.charts import montar_grafico_categorias_despesas
from src.config import TELEGRAM_CHAT_NOMES
from src.services.pending_transaction_service import confirmar_transacao_pendente, ignorar_transacao_pendente
from src.telegram_bot.alert_service import executar_ciclo_alertas
from src.telegram_bot.daily_report_service import gerar_mensagem_informe_diario
from src.telegram_bot.data_provider import carregar_dados_financeiros
from src.ai.services import criar_pendencia_por_texto, sugerir_transacao_por_audio
from src.services.pending_transaction_service import criar_transacao_pendente

ROOT_PATH = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger(__name__)


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
    LOGGER.info("Comando /start recebido. chat_id=%s", chat_id)
    await update.message.reply_text(
        f"{montar_saudacao(update)} Eu sou o Alfred Bot.\n"
        "Use /saldo para ver seus saldos atuais e /despesas para ver seu gasto mensal.\n"
        "Envie /help para mais comandos.\n\n"
        f"Seu chat ID e: {chat_id}"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id_atual = update.effective_chat.id if update.effective_chat else "indisponivel"
    LOGGER.info("Comando /help recebido. chat_id=%s", chat_id_atual)
    await update.message.reply_text(
        f"{montar_saudacao(update)}\n"
        "Comandos disponiveis:\n"
        "/saldo - Ver saldo por conta e total\n"
        "/despesas - Ver despesas do mes atual e comparacao com o mes anterior\n"
        "/categorias_despesas - Ver grafico de categorias de despesas do mes atual\n"
        "/informe_diario - Gerar o resumo diario do fluxo\n"
        "/chat_id - Mostrar o ID desta conversa\n"
        "/alertas - Executar uma checagem manual de alertas\n"
        "Envie texto livre (ex.: 'gastei 50 no mercado no nubank') para criar uma pendencia de transacao\n"
        "Envie um audio para transcrever e criar uma pendencia automaticamente\n"
        "/help - Mostrar esta mensagem"
    )


async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id_atual = update.effective_chat.id if update.effective_chat else "indisponivel"
    LOGGER.info("Comando /chat_id recebido. chat_id=%s", chat_id_atual)
    nome_conversa = obter_nome_conversa(update)
    complemento = f"\nNome configurado: {nome_conversa}" if nome_conversa else ""
    await update.message.reply_text(f"Chat ID desta conversa: {chat_id_atual}{complemento}")


def _teclado_pendencia(pending_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Confirmar", callback_data=f"pendencia:confirmar:{pending_id}"),
                InlineKeyboardButton("Ignorar", callback_data=f"pendencia:ignorar:{pending_id}"),
            ]
        ]
    )


def _fmt_data(valor: str | None) -> str:
    if not valor:
        return "-"
    return valor.split("T")[0]


def _fmt_valor(valor) -> str:
    try:
        return format_real(float(valor))
    except Exception:
        return "-"


def _montar_texto_sugestao(
    *,
    pending_id: str,
    sugestao: dict,
    transcricao: str | None = None,
) -> str:
    linhas = [
        "Transacao sugerida (pendente):",
        f"ID: {pending_id}",
    ]
    if transcricao:
        linhas.append(f'Transcricao: "{transcricao}"')
    linhas.extend(
        [
            f"Data: {_fmt_data(sugestao.get('data'))}",
            f"Tipo: {sugestao.get('tipo') or '-'}",
            f"Categoria: {sugestao.get('categoria') or '-'}",
            f"Conta: {sugestao.get('conta') or '-'}",
            f"Nome: {sugestao.get('nome') or '-'}",
            f"Valor: {_fmt_valor(sugestao.get('valor'))}",
            f"Confianca: {int(float(sugestao.get('confianca') or 0) * 100)}%",
        ]
    )
    campos_incertos = sugestao.get("campos_incertos") or []
    if isinstance(campos_incertos, list) and campos_incertos:
        linhas.append(f"Campos incertos: {', '.join(str(c) for c in campos_incertos)}")
    return "\n".join(linhas)


def _mensagem_erro_interpretacao(exc: Exception) -> str:
    erro = str(exc).lower()
    if "network is unreachable" in erro or "supabase.co" in erro or "operationalerror" in erro:
        return (
            "Nao foi possivel interpretar sua mensagem agora por instabilidade na conexao com o banco.\n"
            "Tente novamente em instantes. Se persistir, ajuste o DATABASE_URL para o Session Pooler IPv4 do Supabase."
        )
    return "Nao foi possivel interpretar sua mensagem agora. Tente novamente em instantes."


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id_atual = update.effective_chat.id if update.effective_chat else "indisponivel"
    texto = (update.message.text or "").strip() if update.message else ""
    LOGGER.info("Mensagem texto recebida para cadastro IA. chat_id=%s", chat_id_atual)

    if not texto:
        await update.message.reply_text("Texto vazio. Envie uma frase de transacao para interpretar.")
        return

    try:
        pendencia = criar_pendencia_por_texto(texto)
        sugestao = pendencia.suggested_payload or {}
        mensagem = _montar_texto_sugestao(
            pending_id=pendencia.id,
            sugestao=sugestao,
            transcricao=None,
        )
        await update.message.reply_text(
            mensagem,
            reply_markup=_teclado_pendencia(pendencia.id),
        )
    except Exception as exc:
        LOGGER.exception("Falha ao interpretar texto no Telegram. chat_id=%s", chat_id_atual)
        await update.message.reply_text(_mensagem_erro_interpretacao(exc))


async def receber_audio_transacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id_atual = update.effective_chat.id if update.effective_chat else "indisponivel"
    LOGGER.info("Audio recebido para cadastro IA. chat_id=%s", chat_id_atual)
    if not update.message:
        return

    arquivo_telegram = None
    if update.message.voice:
        arquivo_telegram = await update.message.voice.get_file()
    elif update.message.audio:
        arquivo_telegram = await update.message.audio.get_file()
    elif update.message.document:
        arquivo_telegram = await update.message.document.get_file()

    if arquivo_telegram is None:
        await update.message.reply_text("Nao encontrei um arquivo de audio valido nessa mensagem.")
        return

    caminho_temp = None
    try:
        sufixo = ".ogg" if update.message.voice else ".mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=sufixo) as tmp:
            caminho_temp = tmp.name
        await arquivo_telegram.download_to_drive(custom_path=caminho_temp)

        resultado = sugerir_transacao_por_audio(caminho_temp)
        sugestao = resultado.sugestao.model_dump(mode="json")
        pendencia = criar_transacao_pendente(
            source="audio",
            raw_text=resultado.sugestao.descricao_original,
            transcription=resultado.texto_transcrito,
            suggested_payload=sugestao,
            confidence=resultado.confianca,
        )

        mensagem = _montar_texto_sugestao(
            pending_id=pendencia.id,
            sugestao=sugestao,
            transcricao=resultado.texto_transcrito,
        )
        await update.message.reply_text(
            mensagem,
            reply_markup=_teclado_pendencia(pendencia.id),
        )
    except Exception as exc:
        LOGGER.exception("Falha ao interpretar audio no Telegram. chat_id=%s", chat_id_atual)
        await update.message.reply_text(_mensagem_erro_interpretacao(exc))
    finally:
        if caminho_temp and os.path.exists(caminho_temp):
            os.remove(caminho_temp)


async def callback_pendencia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        return
    await query.answer()

    data = query.data or ""
    partes = data.split(":")
    if len(partes) != 3 or partes[0] != "pendencia":
        return

    acao = partes[1]
    pending_id = partes[2]

    try:
        if acao == "confirmar":
            pendencia, transacao = confirmar_transacao_pendente(
                pending_id=pending_id,
                payload_confirmado=None,
                auto_confirmed=False,
            )
            await query.edit_message_text(
                "Transacao confirmada com sucesso.\n"
                f"ID pendencia: {pendencia.id}\n"
                f"Transacao criada: {transacao.get('nome')} | {format_real(float(transacao.get('valor', 0.0)))}"
            )
            return

        if acao == "ignorar":
            pendencia = ignorar_transacao_pendente(pending_id=pending_id)
            await query.edit_message_text(
                "Sugestao ignorada.\n"
                f"ID pendencia: {pendencia.id}"
            )
            return

    except Exception as exc:
        LOGGER.exception("Falha ao processar callback de pendencia. pending_id=%s", pending_id)
        await query.edit_message_text(
            "Nao foi possivel concluir a acao da pendencia agora.\n"
            "Se o problema persistir, valide a conexao do banco (DATABASE_URL com Session Pooler IPv4 no Render)."
        )


async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id_atual = update.effective_chat.id if update.effective_chat else "indisponivel"
    LOGGER.info("Comando /saldo recebido. chat_id=%s", chat_id_atual)
    try:
        df = carregar_dados_financeiros()
        saldo_s = calcular_saldo(df)
        total = float(saldo_s.sum()) if not saldo_s.empty else 0.0
        lines = [f"{conta}: {format_real(valor)}" for conta, valor in saldo_s.items()]
        texto = f"*Saldo total:* {format_real(total)}\n\n" + "\n".join(lines)
        await update.message.reply_text(texto)
    except Exception as exc:
        LOGGER.exception("Falha ao executar /saldo. chat_id=%s", chat_id_atual)
        await update.message.reply_text(
            "Erro ao carregar dados financeiros. Verifique credentials.json, o CSV local ou as configuracoes do bot.\n"
            f"Erro: {exc}"
        )


async def despesas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id_atual = update.effective_chat.id if update.effective_chat else "indisponivel"
    LOGGER.info("Comando /despesas recebido. chat_id=%s", chat_id_atual)
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
        LOGGER.exception("Falha ao executar /despesas. chat_id=%s", chat_id_atual)
        await update.message.reply_text(
            "Erro ao calcular despesas. Verifique se os dados estao disponiveis e tente novamente.\n"
            f"Erro: {exc}"
        )


async def categorias_despesas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id_atual = update.effective_chat.id if update.effective_chat else "indisponivel"
    LOGGER.info("Comando /categorias_despesas recebido. chat_id=%s", chat_id_atual)
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
            LOGGER.info("Grafico PNG enviado no /categorias_despesas. chat_id=%s", chat_id_atual)
            return
        except Exception:
            LOGGER.warning(
                "Falha ao gerar PNG no /categorias_despesas; enviando HTML fallback. chat_id=%s",
                chat_id_atual,
            )
            html = fig.to_html(full_html=True, include_plotlyjs="cdn").encode("utf-8")
            arquivo = BytesIO(html)
            arquivo.name = f"categorias_despesas_{anome}.html"
            await update.message.reply_document(document=arquivo, caption=caption)
    except Exception as exc:
        LOGGER.exception("Falha ao executar /categorias_despesas. chat_id=%s", chat_id_atual)
        await update.message.reply_text(
            "Erro ao gerar o grafico de categorias de despesas.\n"
            f"Erro: {exc}"
        )


async def alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id_atual = update.effective_chat.id if update.effective_chat else "indisponivel"
    LOGGER.info("Comando /alertas recebido. chat_id=%s", chat_id_atual)
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
        LOGGER.exception("Falha ao executar /alertas. chat_id=%s", chat_id_atual)
        await update.message.reply_text(
            "Erro ao executar a checagem de alertas.\n"
            f"Erro: {exc}"
        )


async def informe_diario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id_atual = update.effective_chat.id if update.effective_chat else "indisponivel"
    LOGGER.info("Comando /informe_diario recebido. chat_id=%s", chat_id_atual)
    try:
        mensagem = gerar_mensagem_informe_diario()
        await update.message.reply_text(mensagem)
    except Exception as exc:
        LOGGER.exception("Falha ao executar /informe_diario. chat_id=%s", chat_id_atual)
        await update.message.reply_text(
            "Erro ao gerar o informe diario.\n"
            f"Erro: {exc}"
        )
