"""
Configurações globais do projeto Alfred Finanças.
Contas, caminhos, e constantes centralizadas.
"""

from pathlib import Path

# Caminhos
BASE_PATH = Path(__file__).parent.parent
HISTORICO_PATH = BASE_PATH / "historico_fluxo"

# Contas bancárias
CONTAS = [
    'Itaú CC',
    'Cartão Filippe',
    'Cartão Bianca',
    'Cartão Nath',
    'VR',
    'VA',
    'Nubank',
    'Inter',
]

# Cartoes disponiveis na tela de pagamento de cartao
CARTOES_PAGAMENTO = [
    'Cartão Filippe',
    'Cartão Nath',
    'Cartão Bianca',
    'Cartão Pai',
    'Cartão Mãe',
]

# Cartoes cujo pagamento gera transferencia a partir da Itau CC
CARTOES_PAGAMENTO_TRANSFERENCIA = [
    'Cartão Nath',
    'Cartão Filippe',
    'Cartão Bianca',
]

# Cartoes cujo pagamento deve ser lancado como despesa
CARTOES_PAGAMENTO_DESPESA = [
    'Cartão Pai',
    'Cartão Mãe',
]

# Contas de investimento
CONTAS_INVEST = [
    'Ion',
    'Nuinvest',
    '99Pay',
    'C6Invest',
    'InterInvest',
]

# Categorias de despesas
CATEGORIAS_DESPESA = [
    'Restaurante',
    'Supermercado',
    'Cosméticos',
    'Viagem',
    'Transporte',
    'Assinaturas',
    'Lazer',
    'Compras',
    'Educação',
    'Multas',
    'Casa',
    'Serviços',
    'Saúde',
    'Presentes',
    'Outros',
    'Onix',
    'Investimento',
]

# Categorias de receita
CATEGORIAS_RECEITA = [
    'Salário',
    'Cobrança',
    'Outros',
]

# Categorias de investimento
CATEGORIAS_INVESTIMENTO = [
    'Tesouro Selic',
    'CDB',
    'Fundos',
    'LCI',
    'LCA',
    'Ações',
]

# Transações para desconsiderar na análise
GRANDES_TRANSACOES = [
    98, 99, 103, 229, 245, 558, 549, 701, 771, 1012, 1014, 1018,
    995, 978, 971, 1081, 1050, 1326, 1733, 1663, 1744, 1756,
    1766, 1867, 2327, 2350, 2625, 3341, 3580,3671
]

# Nome da planilha no Google Sheets
SPREADSHEET_NAME = "fluxo_de_caixa"
SPREADSHEET_VALORES_NAME = "valores_desejados"
