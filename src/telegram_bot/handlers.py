from datetime import date
from pathlib import Path

import pandas as pd
from telegram import Update
from telegram.ext import ContextTypes

from src.analytics.calculations import calcular_saldo, calcular_despesa_total
from src.services.data_handler import carregar_dados, _normalizar_datas

ROOT_PATH = Path(__file__).resolve().parents[2]


def format_real(value: float) -> str:
    text = f"{value:,.2f}"
    return "R$ " + text.replace(",", "X").replace(".", ",").replace("X", ".")


def load_financial_data() -> pd.DataFrame:
    try:
        return carregar_dados(str(ROOT_PATH))
    except Exception as exc:
        csv_path = ROOT_PATH / "fluxo_de_caixa.csv"
        if not csv_path.exists():
            raise RuntimeError(
                "Não foi possível carregar dados do Google Sheets e não há CSV local de fallback. "
                "Verifique credentials.json ou o CSV local e tente novamente."
            ) from exc

        df = pd.read_csv(
            csv_path,
            sep=';',
            encoding='latin1',
            decimal=',',
            parse_dates=['Data'],
            dayfirst=True,
        )
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
        df['desconsiderar'] = df['desconsiderar'].astype(str).str.upper().replace({
            'TRUE': True,
            'FALSE': False,
        })
        if 'Categoria' in df.columns:
            df['Categoria'] = df['Categoria'].str.replace('TV.Internet.Telefone', 'Assinaturas', regex=False)
        df = _normalizar_datas(df)
        return df


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Olá! Eu sou o Alfred Bot.\n'
        'Use /saldo para ver seus saldos atuais e /despesas para ver seu gasto mensal.\n'
        'Envie /help para mais comandos.'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Comandos disponíveis:\n'
        '/saldo - Ver saldo por conta e total\n'
        '/despesas - Ver despesas do mês atual e comparação com o mês anterior\n'
        '/help - Mostrar esta mensagem'
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f'Você disse: {update.message.text}')


async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        df = load_financial_data()
        saldo_s = calcular_saldo(df)
        total = float(saldo_s.sum()) if not saldo_s.empty else 0.0
        lines = [f'{conta}: {format_real(valor)}' for conta, valor in saldo_s.items()]
        texto = f'*Saldo total:* {format_real(total)}\n\n' + '\n'.join(lines)
        await update.message.reply_text(texto)
    except Exception as exc:
        await update.message.reply_text(
            'Erro ao carregar dados financeiros. Verifique credentials.json, o CSV local ou as configurações do bot.\n'
            f'Erro: {exc}'
        )


async def despesas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        df = load_financial_data()
        df = df[(df['desconsiderar'] == False) & (df['Tipo'] == 'Despesa')]
        anome = int(date.today().strftime('%Y%m'))
        metricas = calcular_despesa_total(df, anome)

        texto = (
            f'*Despesas {metricas["label_curr"]}:* {format_real(metricas["gasto_atual"])}\n'
            f'*Mês anterior ({metricas["label_prev"]}):* {format_real(metricas["gasto_anterior"])}\n'
            f'*Média últimos 3 meses:* {format_real(metricas["gasto_3m_media"])}\n'
        )
        if metricas['delta_atual'] is not None:
            texto += f'Variação vs mês anterior: {metricas["delta_atual"] * 100:.1f}%\n'
        if metricas['delta_3m'] is not None:
            texto += f'Variação vs trimestre anterior: {metricas["delta_3m"] * 100:.1f}%'

        await update.message.reply_text(texto)
    except Exception as exc:
        await update.message.reply_text(
            'Erro ao calcular despesas. Verifique se os dados estão disponíveis e tente novamente.\n'
            f'Erro: {exc}'
        )
