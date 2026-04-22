# Estrutura de pastas

alfred_financas/
├── app.py                    # Entry point (75 linhas)
├── requirements.txt          # Dependências
├── src/
│   ├── __init__.py
│   ├── config.py             # Configurações centralizadas
│   ├── models/
│   │   ├── __init__.py
│   │   └── transaction.py    # Classes de dados
│   ├── services/
│   │   ├── __init__.py
│   │   ├── google_sheets.py  # Integração Sheets
│   │   └── data_handler.py   # Manipulação de dados
│   └── analytics/
│       ├── __init__.py
│       ├── calculations.py   # Cálculos (saldo, despesas)
│       └── charts.py         # Gráficos Plotly
├── paginas/
│   ├── __init__.py
│   ├── 1_transacao.py        # Aba Transação
│   ├── 2_analise.py          # Aba Análise
│   ├── 3_alfred.py           # Aba Alfred (IA)
│   ├── 4_patrimonio.py       # Aba Patrimônio
│   └── 5_extrato.py          # Aba Extrato
└── historico_fluxo/          # Dados históricos


streamlit run app.py