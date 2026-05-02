"""
Configuracoes globais do projeto Alfred Financas.
Contas, caminhos, e constantes centralizadas.
"""

import os
import re
from pathlib import Path

# Caminhos
BASE_PATH = Path(__file__).parent.parent
HISTORICO_PATH = BASE_PATH / "historico_fluxo"


def _carregar_env_local(env_path: Path) -> None:
    """Carrega variaveis simples de um arquivo .env sem sobrescrever o ambiente atual."""
    if not env_path.exists():
        return

    for linha in env_path.read_text(encoding="utf-8").splitlines():
        conteudo = linha.strip()
        if not conteudo or conteudo.startswith("#") or "=" not in conteudo:
            continue

        chave, valor = conteudo.split("=", 1)
        chave = chave.strip()
        valor = valor.strip().strip('"').strip("'")
        if chave and chave not in os.environ:
            os.environ[chave] = valor


def _carregar_nomes_chats_telegram(valor_bruto: str) -> dict[int, str]:
    """Converte pares chat_id:nome em um dicionario para personalizacao do bot."""
    nomes_por_chat: dict[int, str] = {}

    for item in valor_bruto.split(","):
        conteudo = item.strip()
        if not conteudo or ":" not in conteudo:
            continue

        chat_id, nome = conteudo.split(":", 1)
        chat_id = chat_id.strip()
        nome = nome.strip()

        if not chat_id or not nome:
            continue

        try:
            nomes_por_chat[int(chat_id)] = nome
        except ValueError:
            continue

    return nomes_por_chat


def _carregar_chat_ids_telegram(valor_bruto: str) -> list[int]:
    """Extrai chat IDs validos mesmo quando o .env contem entradas malformadas."""
    chat_ids: list[int] = []

    for item in valor_bruto.split(","):
        conteudo = item.strip()
        if not conteudo:
            continue

        match = re.search(r"\d+", conteudo)
        if not match:
            continue

        try:
            chat_ids.append(int(match.group(0)))
        except ValueError:
            continue

    return chat_ids


# Carrega variaveis locais do projeto sem depender de configuracao manual no terminal.
_carregar_env_local(BASE_PATH / ".env")

# Contas bancarias
CONTAS = [
    "Itaú CC",
    "Cartão Filippe",
    "Cartão Bianca",
    "Cartão Nath",
    "VR",
    "VA",
    "Nubank",
    "Inter",
]

# Cartoes disponiveis na tela de pagamento de cartao
CARTOES_PAGAMENTO = [
    "Cartão Filippe",
    "Cartão Nath",
    "Cartão Bianca",
    "Cartão Pai",
    "Cartão Mae",
]

# Cartoes cujo pagamento gera transferencia a partir da Itau CC
CARTOES_PAGAMENTO_TRANSFERENCIA = [
    "Cartão Nath",
    "Cartão Filippe",
    "Cartão Bianca",
]

# Cartoes cujo pagamento deve ser lancado como despesa
CARTOES_PAGAMENTO_DESPESA = [
    "Cartão Pai",
    "Cartão Mae",
]

# Contas de investimento
CONTAS_INVEST = [
    "Ion",
    "Nuinvest",
    "99Pay",
    "C6Invest",
    "InterInvest",
]

# Categorias de despesas
CATEGORIAS_DESPESA = [
    "Restaurante",
    "Supermercado",
    "Cosmeticos",
    "Viagem",
    "Transporte",
    "Assinaturas",
    "Lazer",
    "Compras",
    "Educação",
    "Multas",
    "Casa",
    "Serviços",
    "Saude",
    "Presentes",
    "Outros",
    "Onix",
    "Investimento",
]

# Categorias de receita
CATEGORIAS_RECEITA = [
    "Salário",
    "Cobrança",
    "Outros",
]

# Categorias de investimento
CATEGORIAS_INVESTIMENTO = [
    "Tesouro Selic",
    "CDB",
    "Fundos",
    "LCI",
    "LCA",
    "Ações",
]

# Transacoes para desconsiderar na analise
GRANDES_TRANSACOES = [
    98, 99, 103, 229, 245, 558, 549, 701, 771, 1012, 1014, 1018,
    995, 978, 971, 1081, 1050, 1326, 1733, 1663, 1744, 1756,
    1766, 1867, 2327, 2350, 2625, 3341, 3580, 3671,
]

# Nome da planilha no Google Sheets
SPREADSHEET_NAME = "fluxo_de_caixa"
SPREADSHEET_VALORES_NAME = "valores_desejados"

# Configuracoes do Telegram Bot
# Obter token via BotFather no Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Chats autorizados a receber alertas automaticos do bot.
# Formato esperado: "123456,987654"
TELEGRAM_ALERT_CHAT_IDS = [
    chat_id
    for chat_id in _carregar_chat_ids_telegram(os.getenv("TELEGRAM_ALERT_CHAT_IDS", ""))
]

# Nomes fixos por conversa para personalizar mensagens.
# Formato esperado: "123456:Filippe,987654:Nath"
TELEGRAM_CHAT_NOMES = _carregar_nomes_chats_telegram(
    os.getenv("TELEGRAM_CHAT_NOMES", "")
)

# Horarios de execucao dos alertas automaticos.
# Formato esperado: "09:00,13:00,19:00"
TELEGRAM_ALERT_SCHEDULES = [
    horario.strip()
    for horario in os.getenv("TELEGRAM_ALERT_SCHEDULES", "09:00,13:00,19:00").split(",")
    if horario.strip()
]

TELEGRAM_ALERT_TIMEZONE = os.getenv("TELEGRAM_ALERT_TIMEZONE", "America/Sao_Paulo")
TELEGRAM_ALERT_TEST_MODE = os.getenv("TELEGRAM_ALERT_TEST_MODE", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
TELEGRAM_ALERT_TEST_MESSAGE = os.getenv(
    "TELEGRAM_ALERT_TEST_MESSAGE",
    "Teste de agendamento do Alfred Bot. O timer configurado em TELEGRAM_ALERT_SCHEDULES foi executado.",
)

_telegram_daily_report_chat_ids_raw = os.getenv("TELEGRAM_DAILY_REPORT_CHAT_IDS", "").strip()
if _telegram_daily_report_chat_ids_raw:
    TELEGRAM_DAILY_REPORT_CHAT_IDS = _carregar_chat_ids_telegram(_telegram_daily_report_chat_ids_raw)
else:
    TELEGRAM_DAILY_REPORT_CHAT_IDS = TELEGRAM_ALERT_CHAT_IDS

TELEGRAM_DAILY_REPORT_SCHEDULE = os.getenv("TELEGRAM_DAILY_REPORT_SCHEDULE", "08:04").strip() or "08:00"
TELEGRAM_DAILY_REPORT_TOP_CATEGORIAS = int(
    os.getenv("TELEGRAM_DAILY_REPORT_TOP_CATEGORIAS", "3")
)
TELEGRAM_DAILY_REPORT_TEST_MODE = os.getenv(
    "TELEGRAM_DAILY_REPORT_TEST_MODE", "false"
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Limiares iniciais para as regras automaticas do Alfred Bot.
ALERTA_SALDO_MINIMO_PADRAO = float(os.getenv("ALERTA_SALDO_MINIMO_PADRAO", "500"))
ALERTA_PERCENTUAL_GASTO_MENSAL = float(os.getenv("ALERTA_PERCENTUAL_GASTO_MENSAL", "0.15"))
ALERTA_MULTIPLICADOR_DESPESA_CATEGORIA = float(
    os.getenv("ALERTA_MULTIPLICADOR_DESPESA_CATEGORIA", "1.5")
)
ALERTA_PERCENTUAL_CATEGORIA_DESEJADA = float(
    os.getenv("ALERTA_PERCENTUAL_CATEGORIA_DESEJADA", "0.8")
)

ALERT_STATE_FILE = HISTORICO_PATH / "telegram_alert_state.json"
DAILY_REPORT_STATE_FILE = HISTORICO_PATH / "telegram_daily_report_state.json"
