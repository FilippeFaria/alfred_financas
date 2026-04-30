# Instruções para Agentes de IA - Alfred Finanças

## Visão Geral do Projeto

**alfred_financas** é uma aplicação Streamlit para gerenciamento de fluxo de caixa pessoal com análise de despesas e patrimônio. Todos os dados são sincronizados com Google Sheets para persistência centralizada.

- **Execução**: `streamlit run app.py`
- **Linguagem**: Python 3.x
- **Framework principal**: Streamlit
- **Stack de IA**: LangChain + OpenAI GPT (preparado, parcialmente integrado)

---

## Arquitetura & Estrutura de Código

### Estrutura de Pastas
```text
src/
  ├── config.py              # Configurações centralizadas (contas, categorias, caminhos, Telegram)
  ├── models/transaction.py  # Classes de dados (Transaction)
  ├── services/
  │   ├── google_sheets.py   # Autenticação e sync com Google Sheets
  │   └── data_handler.py    # Manipulação de DataFrames (transformações, filtros)
  ├── analytics/
  │   ├── calculations.py    # Cálculos (saldo, despesas, comparativos por dia do mês)
  │   └── charts.py          # Gráficos Plotly
  └── telegram_bot/          # Integração com Telegram Bot
      ├── __init__.py        # Módulo do bot
      ├── alert_service.py   # Agendamento, execução e deduplicação dos alertas
      ├── alerts.py          # Regras de negócio e modelos de alerta
      ├── bot.py             # Inicialização, polling e registro dos jobs
      ├── data_provider.py   # Carregamento de dados com fallback para CSV local
      ├── daily_report.py    # Montagem do informe diário do bot
      ├── daily_report_service.py # Agendamento, envio e deduplicação do informe diário
      └── handlers.py        # Handlers para comandos e mensagens

paginas/
  ├── transacao.py          # Aba: Registro de transações
  ├── analise.py            # Aba: Análise de despesas
  ├── alfred.py             # Aba: Análise automática (IA) — PLACEHOLDER
  ├── patrimonio.py         # Aba: Patrimônio/ativos
  └── extrato.py            # Aba: Extrato de movimentações

app.py                       # Orquestrador: carrega dados, renderiza abas
run_telegram_bot.py          # Launcher local do bot para ambientes com .venv inconsistente
```

### Fluxo de Dados
1. **app.py** carrega CSV ou sincroniza com Google Sheets via `google_sheets.py`
2. **Session state** armazena DataFrame em cache com timestamp
3. Cada aba em **paginas/** chama `render(df, PATH)` para renderizar conteúdo
4. **analytics/** calcula métricas e gera visualizações
5. **telegram_bot/data_provider.py** centraliza a carga de dados financeiros para o bot
6. **telegram_bot/alert_service.py** agenda execuções automáticas de alertas
7. **telegram_bot/daily_report_service.py** agenda o informe diário

---

## Convenções de Código

### Nomenclatura
- **Variáveis e funções**: português com `snake_case` (ex: `saldo_total`, `calcular_despesas`)
- **Arquivos**: minúsculas com `_` separador (ex: `data_handler.py`)
- **Classes**: CamelCase em português (ex: `Transaction`)

### Padrões Streamlit
- **Cache com recurso**: `@st.cache_resource` para objetos de sessão (auth, conexões)
- **Cache de dados**: `@st.cache_data` para DataFrames, métricas calculadas
- **Invalidação**: Usa `last_update` timestamp em session_state para invalidar cache
- **Estrutura de página**: Cada aba exporta função `render(df, PATH)` — **sem** `if __name__ == "__main__"`

### Estrutura de Dados
- **Principal**: pandas DataFrame com colunas como `Data`, `Tipo`, `Categoria`, `Conta`, `Nome`, `Valor`
- **Persistência**: CSV em `historico_fluxo/` + Google Sheets

---

## Configuração & Autenticação

### Arquivo de Configuração
Todas as configurações estão em [src/config.py](src/config.py):
- **Contas** (ex: "Nubank", "Itaú")
- **Categorias de despesa** (ex: "Alimentação", "Transporte")
- **Paths**: diretório de dados, CSV e arquivos de estado locais do bot
- **Telegram**: token, chats autorizados, horários, timezone e limiares

### Google Sheets
- **Autenticação**: `credentials.json` (dev) ou `st.secrets` (produção)
- **Importar credenciais**: `gspread.authorize(google_auth_oauthlib)`
- **Sync bidirecional**: CSV local + Google Sheets

---

## Executando Localmente

```bash
# Instalar dependências
pip install -r requirements.txt

# Desenvolver
streamlit run app.py

# Subir o bot
python run_telegram_bot.py

# Acessar
# -> http://localhost:8501
```

### Variáveis de Ambiente
- Nenhuma requerida para dev local da interface web (usa `credentials.json`)
- Em produção, fornecer `st.secrets["google_sheets_creds"]` (JSON em base64)
- Para o bot, definir `TELEGRAM_BOT_TOKEN`
- Para alertas automáticos, definir `TELEGRAM_ALERT_CHAT_IDS` com IDs separados por vírgula
- Opcionalmente ajustar `TELEGRAM_ALERT_SCHEDULES` (padrão: `09:00,13:00,19:00`)
- Opcionalmente ajustar `TELEGRAM_ALERT_TIMEZONE` (padrão: `America/Sao_Paulo`)
- Para o informe diário, opcionalmente definir `TELEGRAM_DAILY_REPORT_CHAT_IDS`
- Para o informe diário, opcionalmente ajustar `TELEGRAM_DAILY_REPORT_SCHEDULE` (padrão: `08:00`)
- Para testes do informe diário, opcionalmente definir `TELEGRAM_DAILY_REPORT_TEST_MODE=true`
- Opcionalmente ajustar:
  - `ALERTA_SALDO_MINIMO_PADRAO`
  - `ALERTA_PERCENTUAL_GASTO_MENSAL`
  - `ALERTA_MULTIPLICADOR_DESPESA_CATEGORIA`
  - `ALERTA_PERCENTUAL_CATEGORIA_DESEJADA`

---

## Stack de Tecnologia & Dependências Críticas

| Componente | Propósito |
|-----------|----------|
| **streamlit** | Framework UI |
| **pandas** | Manipulação de dados |
| **plotly** | Visualizações interativas |
| **gspread** | Acesso a Google Sheets API |
| **google-auth-oauthlib** | OAuth2 para Google |
| **langchain + langchain-openai** | IA (preparado, não fully integrado) |
| **dataclasses-json** | Serialização de modelos |
| **python-telegram-bot** | Integração com Telegram Bot API |
| **APScheduler** | Suporte ao agendamento do `JobQueue` do Telegram Bot |

---

## Mudanças Recentes (v2)

### ✅ Fix: Normalização Centralizada de Data (24/04/2026)
**Problema**: `ValueError` ao adicionar transações devido a inconsistência de formato de data.
- Coluna `Data` tinha múltiplos formatos (`DD/MM/YYYY HH:MM` vs `YYYY-MM-DD HH:MM:SS`)
- Conversões falhavam quando misturados

**Solução Implementada**:
- Nova função `_normalizar_datas()` em [src/services/data_handler.py](src/services/data_handler.py)
- Normaliza qualquer formato -> `'%d/%m/%Y %H:%M'` (string)
- Chamada automaticamente em `carregar_dados()` e `salvar_transacao()`

### ✅ Feature: Tipo "Pagamento de Cartão" na aba de transações (26/04/2026)
**Objetivo**: Simplificar o lançamento de pagamentos de cartão com um formulário reduzido.

**Fluxo Implementado**:
- Novo tipo de transação: `Pagamento de Cartão`
- Campos numéricos visíveis para cada cartão
- Campo compartilhado de `Data` para todos os pagamentos preenchidos
- Um único botão `Salvar` processa todos os campos com valor maior que zero

### ✅ Feature: Integração com Telegram Bot (28/04/2026)
**Objetivo**: Adicionar bot do Telegram para acesso remoto aos dados financeiros.

**Fluxo Implementado**:
- Módulo `src/telegram_bot/` com polling local
- Comandos iniciais: `/start`, `/saldo`, `/despesas`, `/categorias_despesas`
- Token via variável de ambiente `TELEGRAM_BOT_TOKEN`

### ✅ Fix: Inicialização do Bot e comando `/despesas` (30/04/2026)
**Problemas**:
- Conflito de event loop na inicialização
- `TypeError` ao comparar a coluna `Data` com `Timestamp`
- `.venv` local podendo apontar para um Python inconsistente

**Soluções Implementadas**:
- `main()` síncrona com `application.run_polling()`
- Conversão defensiva de `Data` em `calcular_despesa_total()`
- Launcher [run_telegram_bot.py](run_telegram_bot.py)

### ✅ Feature: Sistema de Alertas Automáticos do Alfred Bot (30/04/2026)
**Objetivo**: Consultar a base em horários agendados e enviar alertas financeiros automáticos.

**Arquitetura Implementada**:
- `src/telegram_bot/data_provider.py` centraliza o carregamento dos dados
- `src/telegram_bot/alerts.py` concentra os modelos e regras
- `src/telegram_bot/alert_service.py` registra os jobs, executa o ciclo de alertas e controla deduplicação
- `src/telegram_bot/handlers.py` expõe o comando manual `/alertas`

**Regras Iniciais Implementadas**:
1. `Saldo baixo por conta`
2. `Despesa mensal acima da média` dos últimos 3 meses
3. `Categoria em alta` contra o mês anterior
4. Categorias acima ou próximas do orçamento desejado

**Configuração Centralizada**:
- `TELEGRAM_ALERT_CHAT_IDS`
- `TELEGRAM_ALERT_SCHEDULES`
- `TELEGRAM_ALERT_TIMEZONE`
- `ALERT_STATE_FILE`

### ✅ Feature: Informe Diário do Alfred Bot (30/04/2026)
**Objetivo**: Enviar um resumo diário com saldo, gasto acumulado no mês, uso do orçamento e maiores variações por categoria.

**Arquitetura Implementada**:
- `src/analytics/calculations.py` expõe funções reutilizáveis de comparação até o mesmo dia do mês
- `src/telegram_bot/daily_report.py` monta a mensagem final do informe
- `src/telegram_bot/daily_report_service.py` agenda o envio, gera a mensagem e controla deduplicação por dia
- `src/telegram_bot/handlers.py` expõe o comando manual `/informe_diario`
- `src/telegram_bot/bot.py` registra o job automático do informe no `JobQueue`

**Regras Implementadas**:
1. `Saldo`: usa o saldo total calculado pelo fluxo de caixa
2. `Gasto no mês`: compara o acumulado do mês atual versus o mesmo dia do mês anterior
3. `Orçamento usado`: usa os valores desejados por categoria e **desconsidera grandes despesas** (`GRANDES_TRANSACOES`)
4. `Categorias em atenção`: destaca categorias acima do orçamento ou próximas do limite
5. `Maiores aumentos`: mostra as categorias com maior aumento absoluto versus o mesmo dia do mês anterior

**Configuração Centralizada**:
- `TELEGRAM_DAILY_REPORT_CHAT_IDS`
- `TELEGRAM_DAILY_REPORT_SCHEDULE`
- `TELEGRAM_DAILY_REPORT_TEST_MODE`
- `TELEGRAM_DAILY_REPORT_TOP_CATEGORIAS`
- `DAILY_REPORT_STATE_FILE`

**Fluxo Recomendado Agora**:
1. Definir `TELEGRAM_BOT_TOKEN`
2. Definir `TELEGRAM_DAILY_REPORT_CHAT_IDS` ou reutilizar `TELEGRAM_ALERT_CHAT_IDS`
3. Ajustar `TELEGRAM_DAILY_REPORT_SCHEDULE` se necessário
4. Executar `python run_telegram_bot.py`
5. Validar manualmente com `/informe_diario`
6. Confirmar se o arquivo `historico_fluxo/telegram_daily_report_state.json` está sendo atualizado após o envio

---

## Armadilhas & Issues Conhecidas

### ⚠️ Autenticação Frágil
- **Problema**: Alternância entre `credentials.json` (dev) e `st.secrets` (prod)
- **Solução**: Validar ambiente antes de chamar `gspread.authorize()`

### ⚠️ Cache Pode Ficar Stale
- **Problema**: Múltiplas abas atualizando simultaneamente podem desincronizar
- **Solução**: Usar `st.cache_data(ttl=...)` com TTL curto ou invalidar explicitamente via session_state

### ⚠️ Página "Alfred" está Vazia
- **Status**: Placeholder apenas
- **Próximo passo**: Implementar análise automática com GPT

### ⚠️ Contas & Categorias Hardcoded
- **Problema**: Valores estão em [src/config.py](src/config.py)
- **Futuro**: Migrar para Google Sheets ou banco de dados

### ⚠️ Sem Tratamento de Erro Robusto
- **Problema**: Falhas de conexão com Google Sheets podem travar a app
- **Recomendação**: Adicionar fallback para CSV local e retry logic

### ⚠️ Ambiente Python Local Pode Estar Inconsistente
- **Problema**: A `.venv` pode estar apontando para um `python.exe` indisponível
- **Solução prática**: Usar [run_telegram_bot.py](run_telegram_bot.py)

### ⚠️ Alertas e Informes Dependem de Processo Vivo
- **Problema**: Os jobs só executam se o processo do bot estiver rodando continuamente
- **Recomendação**: Em produção, manter o bot sob supervisor/serviço e monitorar logs do `JobQueue`

### ⚠️ Deduplicação Local é Baseada em Arquivo
- **Problema**: O controle de reenvio usa arquivos locais em `historico_fluxo/`
- **Recomendação**: Em multi-instância, mover esse estado para storage compartilhado

---

## Dicas para Agentes IA

### Ao Adicionar Nova Funcionalidade
1. Centralize config em [src/config.py](src/config.py)
2. Crie serviço em `src/services/` se envolver I/O externo
3. Adicione cálculos em `src/analytics/calculations.py`
4. Crie nova aba em `paginas/` com função `render(df, PATH)`
5. Registre no orquestrador [app.py](app.py)

### Ao Modificar Estrutura de Dados
1. Atualize modelo em [src/models/transaction.py](src/models/transaction.py)
2. Migre histórico CSV com script em `notebooks/`
3. Atualize cache invalidation em [app.py](app.py)

### Ao Trabalhar com Google Sheets
1. Valide credenciais antes: `if "google_creds" not in st.session_state`
2. Use `try/except` com fallback para CSV
3. Teste em dev com `credentials.json` antes de prod

### Ao Trabalhar com Telegram Bot
1. Valide primeiro o token com `getMe` se houver dúvida de autenticação
2. Se a `.venv` local estiver quebrada, prefira [run_telegram_bot.py](run_telegram_bot.py)
3. Considere que os dados chegam com `Data` normalizada como string e os cálculos devem converter para datetime quando necessário
4. O comando `/categorias_despesas` tenta enviar uma imagem do Plotly; se o ambiente não tiver suporte a exportação PNG, envia um `.html` como fallback
5. Novas regras automáticas devem entrar em [src/telegram_bot/alerts.py](src/telegram_bot/alerts.py)
6. O formato do informe diário deve ficar em [src/telegram_bot/daily_report.py](src/telegram_bot/daily_report.py)
7. Altere horários, chats e limiares apenas via [src/config.py](src/config.py)
8. Se mudar a estratégia de deduplicação, revise também os arquivos de estado em `historico_fluxo/`
9. O cálculo de `Orçamento usado` no informe diário deve continuar desconsiderando `GRANDES_TRANSACOES`; se a regra de grandes despesas mudar, revise também [src/telegram_bot/daily_report.py](src/telegram_bot/daily_report.py)

---

## Documentação Relacionada

- [Readme.md](Readme.md) — Visão geral da estrutura
- Notebook de análise: [analise_fluxo_caixa.ipynb](analise_fluxo_caixa.ipynb)
- Google Sheets: sincronizado via [src/services/google_sheets.py](src/services/google_sheets.py)

---

**Última atualização**: 30/04/2026  
**Mantido por**: Agentes de IA do GitHub Copilot
