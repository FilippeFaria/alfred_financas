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
```
src/
  ├── config.py              # Configurações centralizadas (contas, categorias, caminhos)
  ├── models/transaction.py  # Classes de dados (Transaction)
  ├── services/
  │   ├── google_sheets.py   # Autenticação e sync com Google Sheets
  │   └── data_handler.py    # Manipulação de DataFrames (transformações, filtros)
  ├── analytics/
  │   ├── calculations.py    # Cálculos (saldo, despesas por categoria)
  │   └── charts.py          # Gráficos Plotly
  └── telegram_bot/          # Integração com Telegram Bot
      ├── __init__.py        # Módulo do bot
      ├── bot.py             # Inicialização e polling do bot
      └── handlers.py        # Handlers para comandos e mensagens

paginas/
  ├── 1_transacao.py         # Aba: Registro de transações
  ├── 2_analise.py           # Aba: Análise de despesas
  ├── 3_alfred.py            # Aba: Análise automática (IA) — PLACEHOLDER
  ├── 4_patrimonio.py        # Aba: Patrimônio/ativos
  └── 5_extrato.py           # Aba: Extrato de movimentações

app.py                        # Orquestrador: carrega dados, renderiza abas
run_telegram_bot.py           # Launcher local do bot para ambientes com .venv inconsistente
```

### Fluxo de Dados
1. **app.py** carrega CSV ou sincroniza com Google Sheets via `google_sheets.py`
2. **Session state** armazena DataFrame em cache com timestamp
3. Cada aba em **paginas/** chama `render(df, PATH)` para renderizar conteúdo
4. **analytics/** calcula métricas e gera visualizações

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
- **Principal**: pandas DataFrame com colunas: `data`, `tipo`, `categoria`, `descricao`, `valor`
- **Persistência**: CSV em `historico_fluxo/` + Google Sheets

---

## Configuração & Autenticação

### Arquivo de Configuração
Todas as configurações estão em [src/config.py](src/config.py):
- **Contas** (ex: "Nubank", "Itaú")
- **Categorias de despesa** (ex: "Alimentação", "Transporte")
- **Paths**: Diretório de dados, arquivo CSV

### Google Sheets
- **Autenticação**: `credentials.json` (dev) ou `st.secrets` (produção)
- **Importar credenciais**: `gspread.authorize(google_auth_oauthlib)`
- **Sync bidirecional**: CSV local + Google Sheets (sincroniza em carregamento)

---

## Executando Localmente

```bash
# Instalar dependências
pip install -r requirements.txt

# Desenvolver
streamlit run app.py

# Acessar
# → http://localhost:8501
```

### Variáveis de Ambiente
- Nenhuma requirida para dev local (usa `credentials.json`)
- Em produção, fornecer `st.secrets["google_sheets_creds"]` (JSON em base64)

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

---

## Mudanças Recentes (v2)

### ✅ Fix: Normalização Centralizada de Data (24/04/2026)
**Problema**: ValueError ao adicionar transações devido a inconsistência de formato de data
- Coluna 'Data' tinha múltiplos formatos (DD/MM/YYYY HH:MM vs YYYY-MM-DD HH:MM:SS)
- Conversões falhavam quando misturados

**Solução Implementada**:
- Nova função `_normalizar_datas()` em [src/services/data_handler.py](src/services/data_handler.py) (linhas 14-38)
- Normaliza qualquer formato → `'%d/%m/%Y %H:%M'` (string)
- Chamada automaticamente em `carregar_dados()` (linha 41) e `salvar_transacao()` (linha 167)

**Arquivos Modificados**:
1. [src/services/data_handler.py](src/services/data_handler.py) — Nova função de normalização
2. [src/analytics/charts.py](src/analytics/charts.py) — Removido `format='mixed'`
3. [src/analytics/calculations.py](src/analytics/calculations.py) — Removido `format='mixed'` em 3 funções
4. [paginas/1_transacao.py](paginas/1_transacao.py) — Ajustado para lidar com Data como string

**Fluxo Garantido Agora**:
1. Carregamento: Google Sheets → normaliza tudo → string `'%d/%m/%Y %H:%M'`
2. Novos registros: Qualquer formato → normaliza → string `'%d/%m/%Y %H:%M'`
3. Analytics: Lê string → converte para datetime quando precisa extrair dia/mês/ano

### ✅ Feature: Tipo "Pagamento de Cartão" na aba de transações (26/04/2026)
**Objetivo**: Simplificar o lançamento de pagamentos de cartão com um formulário reduzido.

**Fluxo Implementado**:
- Novo tipo de transação: `Pagamento de Cartão`
- Formulário com campos numéricos visíveis logo na tela para cada cartão
- Campo compartilhado de `Data` para definir a data de lançamento em todos os pagamentos preenchidos
- Cartões disponíveis: `Cartão Filippe`, `Cartão Nath`, `Cartão Bianca`, `Cartão Pai`, `Cartão Mãe`
- Um único botão `Salvar` processa todos os campos preenchidos com valor maior que zero

**Regras de Negócio**:
1. Para `Cartão Nath`, `Cartão Filippe` e `Cartão Bianca`:
   - Lança uma transferência com origem fixa em `Itaú CC`
   - Cria o débito em `Itaú CC` e o crédito na conta do cartão correspondente
2. Para `Cartão Pai` e `Cartão Mãe`:
   - Lança uma `Despesa` em `Itaú CC`
   - `Categoria`: `Outros`
   - `desconsiderar`: `True`
   - `Obs`, `TAG` e `parcelas`: vazios

**Arquivos Modificados**:
1. [src/config.py](src/config.py) — Novas listas centralizadas para cartões e grupos de pagamento
2. [paginas/transacao.py](paginas/transacao.py) — Novo formulário e fluxo de salvamento para `Pagamento de Cartão`

### ✅ Feature: Integração com Telegram Bot (28/04/2026)
**Objetivo**: Adicionar bot do Telegram para acesso remoto aos dados financeiros e futura integração com Alfred (IA).

**Fluxo Implementado**:
- Novo módulo `src/telegram_bot/` com estrutura básica para polling local via BotFather.
- Comandos iniciais: `/start` (boas-vindas), `/saldo` (saldo por conta e total), `/despesas` (mês atual, mês anterior e média 3M), e eco de mensagens.
- Token configurado em `src/config.py` (mover para `st.secrets` em produção).
- Preparado para integração com dados: handlers podem acessar DataFrame e cálculos via imports de `src.services` e `src.analytics`.

**Arquivos Criados/Modificados**:
1. [src/telegram_bot/__init__.py](src/telegram_bot/__init__.py) — Módulo do bot
2. [src/telegram_bot/bot.py](src/telegram_bot/bot.py) — Inicialização com polling e registro de handlers
3. [src/telegram_bot/handlers.py](src/telegram_bot/handlers.py) — Funções para comandos e mensagens
4. [src/config.py](src/config.py) — Adicionada configuração `TELEGRAM_BOT_TOKEN`
5. [requirements.txt](requirements.txt) — Adicionada dependência `python-telegram-bot`

**Próximos Passos**:
- Endurecer a configuração do token para usar variável de ambiente ou `st.secrets` em produção.
- Adicionar mais comandos e formatação melhor nas respostas do bot.
- Conectar com Alfred para respostas inteligentes via LangChain/OpenAI.

### ✅ Fix: Inicialização do Bot e comando `/despesas` (30/04/2026)
**Problemas**:
- `src/telegram_bot/bot.py` usava `asyncio.run(main())` com `application.run_polling()`, causando conflito de event loop na inicialização.
- O comando `/despesas` comparava a coluna `Data` como string com `Timestamp`, gerando `TypeError`.
- Em alguns ambientes locais, a `.venv` pode estar apontando para um `python.exe` indisponível do Windows Store.

**Soluções Implementadas**:
- `src/telegram_bot/bot.py` passou a usar `main()` síncrona com `application.run_polling()` diretamente.
- `src/analytics/calculations.py` agora converte `Data` para datetime dentro de `calcular_despesa_total()`.
- Novo launcher [run_telegram_bot.py](run_telegram_bot.py) para subir o bot localmente reaproveitando `site-packages` da `.venv` quando necessário.

**Arquivos Modificados**:
1. [src/telegram_bot/bot.py](src/telegram_bot/bot.py) — Ajuste do entrypoint e polling
2. [src/analytics/calculations.py](src/analytics/calculations.py) — Conversão defensiva de `Data` em `/despesas`
3. [run_telegram_bot.py](run_telegram_bot.py) — Novo launcher local do bot

**Fluxo Recomendado Agora**:
1. Atualizar `TELEGRAM_BOT_TOKEN`
2. Executar `python run_telegram_bot.py` ou `python -m src.telegram_bot.bot` quando o ambiente Python estiver saudável
3. Testar `/start`, `/saldo` e `/despesas`

---

## Armadilhas & Issues Conhecidas

### ⚠️ Autenticação Frágil
- **Problema**: Alternância entre `credentials.json` (dev) e `st.secrets` (prod)
- **Solução**: Validar ambiente antes de chamar `gspread.authorize()`
- **Arquivo**: [src/services/google_sheets.py](src/services/google_sheets.py)

### ⚠️ Cache Pode Ficar Stale
- **Problema**: Múltiplas abas atualizando simultaneamente podem desincronizar
- **Solução**: Usar `st.cache_data(ttl=...)` com TTL curto ou invalidar explicitamente via session_state

### ⚠️ Página "Alfred" está Vazia
- **Status**: Placeholder apenas (imports de LangChain presentes, mas `render()` não implementada)
- **Arquivo**: [paginas/3_alfred.py](paginas/3_alfred.py)
- **Próximo passo**: Implementar análise automática com GPT

### ⚠️ Contas & Categorias Hardcoded
- **Problema**: Valores estão em [src/config.py](src/config.py) — difícil adicionar novos sem editar código
- **Futuro**: Migrar para Google Sheets ou banco de dados

### ⚠️ Sem Tratamento de Erro Robusto
- **Problema**: Falhas de conexão com Google Sheets podem travar a app
- **Recomendação**: Adicionar fallback para CSV local e retry logic

### ⚠️ Ambiente Python Local Pode Estar Inconsistente
- **Problema**: A `.venv` pode ter sido criada apontando para um `python.exe` do Windows Store indisponível
- **Sintoma**: `python` da `.venv` falha antes mesmo de iniciar o bot
- **Solução prática**: Usar [run_telegram_bot.py](run_telegram_bot.py) com um Python funcional e manter o token em variável de ambiente ou `src/config.py`

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

---

## Documentação Relacionada

- [Readme.md](Readme.md) — Visão geral da estrutura
- Notebook de análise: [analise_fluxo_caixa.ipynb](analise_fluxo_caixa.ipynb)
- Google Sheets: Sincronizado via [src/services/google_sheets.py](src/services/google_sheets.py)

---

**Última atualização**: 30/04/2026  
**Mantido por**: Agentes de IA do GitHub Copilot
