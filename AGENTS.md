# Instruções para Agentes de IA - Alfred Finanças

## Visão Geral do Projeto

**alfred_financas** é um projeto centrado no app mobile em Flutter para gerenciamento de fluxo de caixa pessoal, análises de despesas e patrimônio. A interface Streamlit existe como um cliente legado e não deve ser alterada a não ser que o usuário solicite explicitamente.

- **Execução do app móvel**: `cd mobile_app && flutter run`
- **Linguagem principal do backend**: Python 3.x
- **Frontend principal**: Flutter mobile (`mobile_app/`)
- **Interface legacy**: Streamlit (`app.py` / `paginas/`)
- **Stack de IA**: OpenAI API + pipeline próprio (`src/ingestion` + `src/ai`) para sugestão de transações pendentes

O repositório mantém ainda um app Streamlit legado e uma API FastAPI para integração com o app móvel.

---

## Arquitetura & Estrutura de Código

### Estrutura de Pastas
```text
src/
  ├── config.py              # Configurações centralizadas (contas, categorias, caminhos, Telegram)
  ├── models/transaction.py  # Classes de dados (Transaction)
  ├── models/pending_transaction.py # Modelo de domínio para pendências de IA
  ├── api/
  │   ├── main.py            # Aplicação FastAPI e rotas
  │   ├── schemas.py         # Contratos request/response (Pydantic)
  │   ├── services.py        # Regras de negócio e integração com dados
  │   ├── errors.py          # Tratamento de erros padronizado da API
  │   ├── auth.py            # Middleware/dependency para autenticação futura
  │   └── client.py          # Cliente HTTP interno usado pelo Streamlit
  ├── services/
  │   ├── google_sheets.py   # Autenticação e sync com Google Sheets
  │   └── data_handler.py    # Manipulação de DataFrames (transformações, filtros)
  │   └── pending_transaction_service.py # Ciclo de vida de pendências (criar, confirmar, ignorar)
  ├── ingestion/
  │   ├── __init__.py
  │   ├── audio/
  │   │   ├── normalizer.py  # Validação de extensão/tamanho e metadados
  │   │   └── transcriber.py # Transcrição de áudio para português
  │   ├── notification/
  │   │   ├── normalizer.py  # Whitelist/filtro financeiro de notificações Android
  │   │   └── deduplicator.py # Deduplicação por chave/similaridade temporal
  │   └── text/
  │       └── normalizer.py  # Normalização de texto de entrada
  ├── ai/
  │   ├── __init__.py
  │   ├── clients.py         # Cliente OpenAI centralizado e tratamento de erro
  │   ├── schemas.py         # Contratos de sugestão de transação
  │   ├── services.py        # Orquestração IA + criação de pendência
  │   ├── validators.py      # Validações financeiras da sugestão
  │   ├── confidence.py      # Cálculo de confiança
  │   ├── matching.py        # Canonicalização categórica (normalização, exato, fuzzy, LLM)
  │   ├── prompts/
  │   │   └── transaction_from_text.md
  │   └── parsers/
  │       ├── text_parser.py
  │       └── audio_parser.py
  │       └── notification_parser.py
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
  ├── alfred.py             # Aba Streamlit para evolução de IA (web)
  ├── patrimonio.py         # Aba: Patrimônio/ativos
  └── extrato.py            # Aba: Extrato de movimentações

app.py                       # Orquestrador: carrega dados, renderiza abas
run_api.py                   # Launcher local da API FastAPI
run_telegram_bot.py          # Launcher local do bot para ambientes com .venv inconsistente
mobile_app/                  # App Flutter por features; aba Alfred (Insights) já integra texto+áudio com IA
```

### Fluxo de Dados
1. **app.py** carrega dados exclusivamente via API (`src/api/client.py`)
2. **Session state** armazena DataFrame em cache com timestamp
3. Cada aba em **paginas/** chama `render(df, PATH)` para renderizar conteúdo
4. **src/api/main.py** expõe endpoints tipados e regras críticas via `src/api/services.py`
5. **analytics/** permanece focado em cálculos e visualizações reutilizáveis
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

### Padrões Flutter Mobile
- **Estrutura por features**: `mobile_app/lib/core` e `mobile_app/lib/features/*`
- **Gerenciamento de estado**: `flutter_riverpod`
- **HTTP**: `dio` com client centralizado em `mobile_app/lib/core/network/`
- **Rotas**: `go_router`
- **Ambiente**: `--dart-define=FLAVOR=dev|prod` e `--dart-define=API_BASE_URL=...`
- **Telas**: manter `loading`, `erro amigavel`, `pull-to-refresh` e atualizacao automatica das listas quando a acao de cadastro for bem-sucedida
- **Encoding**: nao reescrever textos ou config com encoding diferente; manter UTF-8 original dos arquivos existentes

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

### Flutter Mobile

```bash
# Entrar no app mobile
cd mobile_app

# Em Windows, se o flutter ainda nao estiver no PATH, chame o executavel diretamente
C:\Users\lippe\flutter\bin\flutter.bat pub get

# Rodar no navegador
C:\Users\lippe\flutter\bin\flutter.bat run -d chrome --dart-define=FLAVOR=dev --dart-define=API_BASE_URL=http://127.0.0.1:8000

# Rodar no celular Android com API remota
C:\Users\lippe\flutter\bin\flutter.bat run -d <device_id> --dart-define=FLAVOR=prod --dart-define=API_BASE_URL=https://<sua-api>.onrender.com
```

**Observações do Flutter**
- A API do Render deve ser usada no mobile em producao; para testes locais no navegador, a FastAPI precisa aceitar CORS.
- `flutter build apk` exige Android SDK instalado e configurado no Windows.
- Se o `flutter` nao estiver no `PATH`, use `C:\Users\lippe\flutter\bin\flutter.bat` diretamente.
- Para testar no celular via IP local do PC, a API deve subir com `--host 0.0.0.0`; isso e apenas para desenvolvimento.

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
- Para IA (API FastAPI):
  - `OPENAI_API_KEY`
  - `OPENAI_TEXT_MODEL` (ex.: `gpt-5.5`)
  - `OPENAI_TRANSCRIPTION_MODEL` (ex.: `gpt-4o-transcribe`)
  - `OPENAI_REQUEST_TIMEOUT_SECONDS` (ex.: `30`)

---

## Stack de Tecnologia & Dependências Críticas

| Componente | Propósito |
|-----------|----------|
| **streamlit** | Framework UI |
| **pandas** | Manipulação de dados |
| **plotly** | Visualizações interativas |
| **gspread** | Acesso a Google Sheets API |
| **google-auth-oauthlib** | OAuth2 para Google |
| **openai** | Interpretação de texto e transcrição de áudio |
| **dataclasses-json** | Serialização de modelos |
| **python-telegram-bot** | Integração com Telegram Bot API |
| **APScheduler** | Suporte ao agendamento do `JobQueue` do Telegram Bot |

---

## Mudanças Recentes (v3)

### ✅ Feature: Deploy do `mobile_app` Web no Render + hardening de compatibilidade (16/05/2026)
**Objetivo**: publicar o app Flutter Web no Render com o mínimo de mudanças e sem quebrar fluxos já existentes.

**Infra implementada (`mobile_app/`)**:
- `Dockerfile.web` com build multi-stage (Flutter -> Nginx)
- `nginx.conf` com fallback SPA (`try_files ... /index.html`) para rotas internas
- `RENDER_DEPLOY.md` com checklist de configuração/validação

**Ajustes de código para Web**:
- `mobile_app/lib/main.dart`:
  - proteção de integrações nativas Android com `kIsWeb`
  - inicialização de notificações locais somente fora do Web
- `mobile_app/lib/features/insights/presentation/insights_page.dart`:
  - ocultação/desativação da captura nativa Android no navegador
  - manutenção das ações de pendências (`Confirmar`, `Editar`, `Ignorar`) no Web
  - gravação nativa ajustada para usar diretório temporário quando aplicável
- `mobile_app/lib/core/network/alfred_api_client.dart`:
  - timeout específico e maior para `/mobile/dashboard_snapshot`
  - mensagens de timeout mais precisas (`conectar`, `aguardar resposta`, `enviar`)

**Ajustes de versionamento que impactavam o build no Render**:
- `mobile_app/.gitignore`: remoção de `web/` para garantir versionamento da pasta `mobile_app/web/`
- `.gitignore` raiz: `env/` passou para `/env/` para não ignorar `mobile_app/lib/core/env/`
- `mobile_app/pubspec.yaml`: inclusão de `path_provider`

**Resultado esperado**:
- build/deploy web estável no Render
- app web navegável em `/transactions`, `/dashboard`, `/insights`, `/settings`
- fluxos Android nativos preservados no mobile sem bloquear uso no navegador

### ✅ Perf: cache de snapshot do dashboard na API (16/05/2026)
**Problema observado**:
- endpoint `GET /mobile/dashboard_snapshot` com latência significativamente maior que os demais endpoints, causando timeout intermitente no Web sob concorrência/cold start.

**Backend implementado (`src/api/services.py`)**:
- cache em memória para payload de `obter_dashboard_snapshot_mobile(...)`
  - TTL configurável por env: `ALFRED_DASHBOARD_CACHE_TTL_SECONDS` (padrão `60`)
  - chave inclui filtros relevantes (`desconsiderar`, `va`, `vr`, `bianca`, `filippe`, `day_to_date`, `anome_referencia`, `categoria`, `meses_historico`)
  - limite de até 32 entradas com descarte da mais antiga
- invalidação automática do cache em mutações que alteram visão de dashboard:
  - `criar_transacao`
  - `excluir_transacao_por_id`
  - `atualizar_transacao_por_id`
  - `atualizar_flags_transacao_por_id`
  - `salvar_orcamento_valores`

**Resultado esperado**:
- primeira carga pode continuar mais cara, mas recargas/navegação subsequente ficam substancialmente mais rápidas
- redução de timeout por recomputação completa em chamadas repetidas

### ✅ Fix: Transferência com criação atômica + edição robusta + refresh de saldos no mobile (15/05/2026)
**Problemas observados**:
- algumas transferências eram gravadas/consultadas com apenas uma linha, quebrando a edição de origem/destino
- em cenários antigos, edição podia convergir para `destino -> destino`
- após salvar transferência, o dashboard/saldos no app mobile podia continuar com cache antigo

**Backend implementado**:
- `POST /transacoes` passou a aceitar `conta_destino` para `Transferência`
- criação de transferência agora é **atômica**: cria débito e crédito no mesmo `legacy_id`
- validações para evitar persistência inválida:
  - `conta_destino` obrigatória em transferência
  - origem e destino devem ser diferentes
  - valor deve ser positivo (normalizado internamente)
- edição de transferência foi reforçada para:
  - atualizar linha específica quando aplicável (`linha_id`)
  - recriar o par completo quando o registro estiver incompleto (apenas 1 linha)

**Mobile implementado (`mobile_app/lib/features/transactions`)**:
- cadastro de transferência passou a ser uma única chamada com `contaDestino` (não duas chamadas separadas)
- edição parcial (troca apenas de origem **ou** destino) só acontece quando o par débito/crédito está completo
- quando o par está incompleto, a edição força atualização completa para recuperar consistência
- após `cadastrar`, `editar`, `excluir` e atualização de flags:
  - invalida cache de dashboard
  - força novo snapshot para atualizar saldos automaticamente

**Compatibilidade com fluxos existentes**:
- confirmação de pendências de IA agora repassa `conta_destino` quando presente
- cliente interno da API (usado por Streamlit) passou a aceitar `conta_destino`

**Resultado esperado**:
- toda nova transferência deve persistir em duas linhas (débito origem + crédito destino) com mesmo `id` lógico
- edição de transferência passa a preservar corretamente origem/destino
- saldos no mobile devem refletir a transferência sem necessidade de refresh manual extra

### ✅ Fix: Edição de pendência IA para Transferência respeita conta destino (15/05/2026)
**Problema observado**:
- no fluxo de pendência (`Insights`), ao editar uma sugestão de `Receita` para `Transferência`, o app permitia selecionar `Conta destino`, mas ao confirmar retornava erro de destino obrigatório

**Causa raiz**:
- o mobile enviava `conta_destino`, porém o schema do endpoint `POST /transacoes/pendentes/{pending_id}/confirmar` não aceitava esse campo
- o payload era sanitizado pelo Pydantic e `conta_destino` era descartada antes de chegar na confirmação

**Implementado**:
- `src/api/schemas.py`:
  - `ConfirmarTransacaoPendenteRequest` agora inclui `conta_destino`
- `mobile_app/lib/features/insights/presentation/insights_page.dart`:
  - ao trocar tipo para `Transferência`, categoria é ajustada automaticamente para `Transferência`
  - confirmação de pendência agora também invalida cache financeiro (dashboard/saldos)

**Resultado**:
- edição de pendência para `Transferência` passa a confirmar com origem/destino corretamente
- saldos e dashboard refletem a confirmação sem depender de refresh manual extra

### ✅ Feature: Filtro de transações com múltiplas contas (15/05/2026)
**Objetivo**:
- permitir selecionar mais de uma conta simultaneamente no filtro da tela de transações

**Implementado**:
- Mobile:
  - `TransactionsFilters` migrou de `conta` (única) para `contas` (lista)
  - UI de filtros passou a usar seleção múltipla com `FilterChip` na seção de contas
  - persistência dos filtros mantém compatibilidade com formato legado (campo `conta`)
- API:
  - `GET /transacoes` passou a aceitar `contas` como query param repetido (`?contas=A&contas=B`)
  - `src/api/services.py` e `src/database/repositories.py` aplicam `IN (...)` quando há múltiplas contas
  - compatibilidade preservada com `conta` única

**Observação operacional**:
- após deploy local dessas mudanças, é necessário reiniciar a FastAPI para o novo parâmetro `contas` aparecer no `/openapi.json` e começar a filtrar efetivamente

### ✅ Feature: Otimização de performance da tela Insights (11/05/2026)
**Objetivo**: melhorar a responsividade das ações `Confirmar`, `Ignorar` e `Editar` nas pendências detectadas por notificação.

**Mobile implementado (`mobile_app/lib/features/insights/presentation/insights_page.dart`)**:
- Atualização otimista nas pendências de notificação:
  - remove o card imediatamente ao confirmar/ignorar
  - mantém chamada de API em background
  - faz rollback do item na posição original quando ocorre falha
- Estado de carregamento por item:
  - controle por ID de pendência em processamento
  - desabilita ações apenas do card afetado
  - evita duplo clique e requests duplicadas
- Cache local de categorias para o fluxo `Editar`:
  - preload em `initState` sem bloquear a renderização inicial
  - reutiliza categorias em memória nas aberturas seguintes do diálogo

**Resultado**:
- A tela reage de forma imediata ao toque nas ações de pendência.
- O fluxo de edição fica mais rápido após a primeira carga de categorias.
- O pull-to-refresh permanece como mecanismo manual de sincronização completa.

### ✅ Feature: Épicos 5-6 — Notificações Android -> Pendências com revisão (10/05/2026)
**Objetivo**: detectar notificações financeiras no Android, transformar em sugestão de transação e criar pendência (sem salvar direto).

**Backend implementado**:
- Endpoint novo em `src/api/main.py`:
  - `POST /ai/notificacao/transacao`
- Contratos novos em `src/api/schemas.py`:
  - `NotificacaoTransacaoRequest`
  - `NotificacaoTransacaoResponse`
- Novo pipeline de notificação:
  - `src/ingestion/notification/normalizer.py` (whitelist + indícios financeiros)
  - `src/ingestion/notification/deduplicator.py` (chave + similaridade em janela de 5 min)
  - `src/ai/parsers/notification_parser.py` (heurísticas de tipo/valor/conta/nome/data)
  - `src/ai/services.py` (orquestração IA + regras + criação de pendência)
- `src/services/pending_transaction_service.py` agora aceita `source="android_notification"`.

**Regras de notificação implementadas**:
- Nunca cria transação definitiva diretamente.
- Se não houver valor identificável, não cria pendência (`created=false`).
- Deduplicação por:
  - `notification_key`
  - `package_name + valor + estabelecimento + janela de 5 minutos`
- Retorna motivo quando ignora por duplicidade.
- Inferência de conta por `package_name/app_name` (com suporte a variantes `com.itau*`).

**Mobile implementado (`mobile_app/lib/features/insights`)**:
- Leitura de notificações Android via serviço nativo:
  - `mobile_app/android/app/src/main/kotlin/.../AlfredNotificationListenerService.kt`
  - `NotificationCaptureStore.kt` + `MethodChannel` no `MainActivity.kt`
- Seção na Insights:
  - Status da permissão
  - Ação para abrir configurações de acesso a notificações
  - Lista de `Pendencias detectadas por notificacao` com:
    - `Confirmar`
    - `Editar`
    - `Ignorar`
  - Pull-to-refresh para atualizar status + lista
- Cliente mobile chama `POST /ai/notificacao/transacao` para processamento automático.

### ✅ Feature: Épicos 1-4 de IA (texto + áudio + pendências + mobile) (10/05/2026)
**Objetivo**: permitir cadastro inteligente por texto e áudio com revisão antes da persistência final.

**Backend implementado**:
- `src/ingestion/` para entrada bruta de texto/áudio (normalização e transcrição)
- `src/ai/` para parser, validação, confiança e matching categórico
- `src/database/models.py`: nova tabela `pending_transactions`
- `src/services/pending_transaction_service.py`: criar, listar, confirmar e ignorar pendências
- Endpoints novos em `src/api/main.py`:
  - `POST /ai/texto/transacao`
  - `POST /ai/audio/transacao`
  - `POST /transacoes/pendentes/{pending_id}/confirmar`
  - `POST /transacoes/pendentes/{pending_id}/ignorar`
  - endpoints de apoio em `/ia/pendencias/*` para ciclo completo

**Regras implementadas de IA**:
- IA nunca salva transação definitiva diretamente
- Toda sugestão vira pendência antes da confirmação
- Campo `data` assume data atual quando não informado pelo usuário
- `Tipo`, `Conta` e `Categoria` passam por pipe de canonicalização:
  1. normalização de string
  2. matching exato
  3. matching fuzzy
  4. desempate por LLM
  5. validação final contra catálogo permitido

**Mobile implementado (`mobile_app/lib/features/insights`)**:
- aba Alfred deixou de ser placeholder
- entrada por texto natural com botão `Interpretar`
- fluxo de áudio com gravação/seleção e `Interpretar áudio`
- exibição de transcrição + transação sugerida
- ações `Confirmar`, `Editar` e `Ignorar`
- edição com dropdown para campos categóricos (`Tipo`, `Categoria`, `Conta`)

### ✅ Fix: Dashboard mobile inicia no mês atual e preserva a tela durante recarga (07/05/2026)
**Problema**: ao trocar o mês no dashboard, a tela podia “sumir” enquanto a nova análise carregava e o filtro não partia de um mês intuitivo.

**Implementado**:
- `mobile_app/lib/features/dashboard/data/dashboard_repository.dart`: filtro padrão passou a usar o `anome` corrente (`YYYYMM`).
- `mobile_app/lib/features/dashboard/presentation/dashboard_page.dart`: o slider de mês aplica o filtro no `onChangeEnd`, reduzindo re-renderizações intermediárias.
- `mobile_app/lib/features/dashboard/presentation/dashboard_page.dart`: a UI mantém o conteúdo anterior visível enquanto a nova resposta da API é carregada.

**Resultado**:
- O dashboard abre no mês atual por padrão.
- A troca de mês ficou mais fluida e sem “piscar” a página inteira.

### ✅ Fix: Formulário de transação suporta Transferência sem quebrar o dropdown (07/05/2026)
**Problema**: ao alternar para `Transferência`, o `DropdownButtonFormField` podia receber um valor inválido ou duplicado e quebrar a tela.

**Implementado**:
- `mobile_app/lib/features/transactions/presentation/transactions_page.dart`: remoção de valores duplicados nas listas de `DropdownMenuItem`.
- Normalização defensiva de categoria, conta origem e conta destino antes de renderizar o formulário.
- Limpeza de campos incompatíveis quando o tipo de transação muda.

**Resultado**:
- O formulário não quebra ao usar `Transferência`.
- O valor selecionado sempre é coerente com as opções atuais do tipo escolhido.

### ✅ Fix: Arredondamento de métricas na página de transação (07/05/2026)
**Problema**: saldos de contas/cartões apareciam com ruído de ponto flutuante na UI (ex.: `1607.0100000000175`).

**Implementado**:
- `paginas/transacao.py`: criação de helper `formatar_moeda(valor)` para exibição em formato monetário brasileiro.
- Aplicação do formatter nos `st.metric` de saldos (`Itaú CC`, cartões, `Inter`, `Nubank`, `VA`, `VR`).

**Resultado**:
- Exibição consistente com 2 casas decimais (ex.: `R$ 1.607,01`) sem alterar a regra de cálculo.

### ✅ Fix: Fallback silencioso na análise sem credenciais do Google Sheets (07/05/2026)
**Problema**: a aba de análise exibia aviso operacional quando faltavam credenciais do Google Sheets para carregar valores desejados.

**Implementado**:
- `src/analytics/charts.py` (`_carregar_valores_desejados`): remoção do `st.warning(...)` para erro de credenciais.
- Em caso de falha de leitura, manutenção de fallback local em memória (`st.session_state.valores_desejados`) e marcação de carga concluída.

**Resultado**:
- A página de análise não é poluída por alerta técnico de infraestrutura.
- Fluxo de análise permanece funcional mesmo sem integração ativa com Sheets.

### ✅ Feature: ETAPA 3.1 — Persistência PostgreSQL + API híbrida (06/05/2026)
**Objetivo**: iniciar migração incremental de persistência para PostgreSQL (Supabase), mantendo continuidade operacional.

**Implementado**:
- `src/database/connection.py`: engine SQLAlchemy, `SessionLocal`, `Base`, `init_db()`, leitura de `DATABASE_URL` via `.env`.
- `src/database/models.py`: modelos ORM iniciais (`User`, `Account`, `Category`, `Transaction`) com UUID e timestamps.
- `src/database/repositories.py`: camada de repositories para desacoplar API da persistência.
- `scripts/migrate_sheets_to_postgres.py`: migração Google Sheets -> PostgreSQL com logs, deduplicação e validação.
- `src/api/services.py`: PostgreSQL como fonte principal, fallback opcional para Google Sheets.

**Decisões de modelagem**:
- `Transaction.id` (UUID) é chave primária física.
- `Transaction.legacy_id` representa o `id_transacao` legado (não único, pode repetir).
- Transferências e parcelamentos devem preservar múltiplas linhas com mesmo `legacy_id`.

**Flags operacionais**:
- `ALFRED_SHEETS_FALLBACK_ENABLED` (fallback leitura para Sheets)
- `ALFRED_DUAL_WRITE_ENABLED` (escrita dupla opcional)
- `ALFRED_DEFAULT_USER_EMAIL` e `MIGRATION_USER_EMAIL` devem ser consistentes para evitar leitura “zerada”.

### ✅ Feature: ETAPA 2.3 — Regras críticas centralizadas no backend (06/05/2026)
**Objetivo**: retirar regras financeiras críticas do Streamlit e centralizar na API.

**Implementado**:
- Novo endpoint `POST /analise/resumo` com filtros, agregações e métricas mensais processadas no backend
- Validações de transação centralizadas em `src/api/services.py` (tipo/categoria/sinal do valor)
- Streamlit passou a consumir saldo e resumo analítico processado pela API

**Resultado**:
- Frontend reduzido a camada de apresentação
- Backend devolve dados já processados para análise

### ✅ Feature: ETAPA 2.4 — Camada de modelos de resposta padronizada (06/05/2026)
**Objetivo**: padronizar contratos da API e documentação OpenAPI.

**Implementado em `src/api/schemas.py`**:
- `SaldoResponse`
- `TransacaoResponse`
- `CategoriaResponse`
- `InsightResponse`
- `StatusResponse` e modelos auxiliares de erro

**Resultado**:
- Endpoints com `response_model` explícito
- `/docs` documenta os contratos corretamente

### ✅ Feature: ETAPA 2.5 — Tratamento de erros padronizado (06/05/2026)
**Objetivo**: impedir stacktrace bruto no cliente e padronizar falhas.

**Implementado**:
- `src/api/errors.py` com exceção de domínio `ApiServiceError`
- Handlers globais FastAPI para:
  - erro de validação de request
  - erros de serviço
  - erro inesperado
- Resposta de erro padronizada:
  - `{"error": {"code": "...", "message": "...", "details": {...}}}`
- Logs estruturados (JSON) para falhas operacionais

**Casos cobertos**:
- falha Google Sheets
- timeout
- dados inválidos
- autenticação (estrutura pronta para evolução)

### ✅ Feature: ETAPA 2.7 — Preparação para autenticação futura (06/05/2026)
**Objetivo**: preparar arquitetura multiusuário sem exigir login agora.

**Implementado**:
- `src/api/auth.py` com:
  - middleware para leitura de header `Authorization`
  - dependency `get_current_user_optional`
  - `UserContext` injetado nos endpoints

**Resultado**:
- Estrutura pronta para JWT
- fluxo atual preservado (sem bloqueio de endpoints)

### ✅ Feature: Backend FastAPI Inicial (ETAPA 1) (06/05/2026)
**Objetivo**: Iniciar a separação entre frontend (Streamlit) e backend, criando uma camada de API para consumo futuro da interface.

**Arquitetura Implementada**:
- Novo pacote `src/api/` com:
  - `main.py`: aplicação FastAPI e definição de rotas
  - `schemas.py`: modelos de request/response (Pydantic)
  - `services.py`: regras de negócio e integração com dados (Google Sheets)
- Novo launcher local `run_api.py` para subir a API com `uvicorn`

**Endpoints Iniciais**:
1. `GET /saldo`
2. `GET /transacoes`
3. `POST /transacoes`
4. `GET /categorias`
5. `POST /insights`
6. `GET /health` (apoio operacional)

**Observações Técnicas**:
- A API reutiliza os serviços de integração com Google Sheets (`src/services/google_sheets.py`).
- O endpoint `/insights` foi iniciado com implementação básica (resumo e sinais principais), preparado para evolução com IA.
- `requirements.txt` foi ajustado para suportar FastAPI:
  - `fastapi==0.115.12`
  - `starlette==0.46.2` (compatível com a versão do FastAPI acima)

**Comando de Execução da API**:
```bash
python run_api.py
# Docs: http://localhost:8000/docs
```

### ✅ Feature: Alertas Personalizados por Chat com Prioridade e Histórico Diário (05/05/2026)
**Objetivo**: Organizar os alertas automáticos por usuário, enviando no máximo um alerta por horário com prioridade fixa.

**Arquitetura Implementada**:
- `src/config.py` define `TELEGRAM_CONTAS_POR_CHAT_ID` com mapeamento **hardcoded** de contas por `chat_id`
- `src/telegram_bot/alerts.py` recebe contexto por chat (`chat_id`, `nome_usuario`, `contas_usuario`)
- `src/telegram_bot/alert_service.py` executa o ciclo **por chat**, seleciona apenas um alerta elegível por execução e persiste histórico diário

**Regras e Prioridade Atual**:
1. `regra_lembrete_sem_cadastro`
2. `regra_categoria_acima_do_orcamento`
3. `regra_gasto_categoria_proximo_do_limite`
4. `regra_categoria_com_disparo_relevante`

**Comportamento de Envio**:
- Em cada horário agendado, envia no máximo **1 alerta por chat**
- A seleção respeita a prioridade: se a regra 1 não se aplicar, tenta a 2, depois 3, depois 4
- Cada alerta pode ser enviado **apenas uma vez por dia por chat**

**Detalhes da `regra_lembrete_sem_cadastro`**:
- Filtra por contas do usuário (`TELEGRAM_CONTAS_POR_CHAT_ID`)
- Usa a coluna `Data Criacao` para calcular o último cadastro
- Considera apenas `Tipo` em `Despesa` ou `Receita`
- Se passar de 2 dias sem cadastro, envia lembrete personalizado

**Persistência do Estado**:
- Arquivo: `historico_fluxo/telegram_alert_state.json`
- Chaves de deduplicação por chat: `chat_id:chave_alerta`
- Histórico diário em `historico_por_dia` com timestamp, chat_id, chave, título, mensagem e severidade

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

### ✅ Feature: Healthcheck HTTP no processo do bot para uptime no Render Free (06/05/2026)
**Objetivo**: Permitir monitoramento externo (UptimeRobot) sem separar outro serviço web, mantendo o bot acordado no plano gratuito.

**Arquitetura Implementada**:
- `run_telegram_bot.py` agora sobe um servidor HTTP leve em thread daemon usando `ThreadingHTTPServer`
- Rotas de healthcheck expostas no mesmo processo do bot:
  - `GET /` e `GET /health` -> `200` com `{"status":"online"}`
  - `HEAD /` e `HEAD /health` -> `200` (sem body), compatível com plano gratuito do UptimeRobot
- Porta definida por `PORT` (Render) com fallback local para `10000`

**Uso recomendado (Render + UptimeRobot)**:
1. Manter start command do serviço: `python run_telegram_bot.py`
2. No UptimeRobot gratuito, criar monitor `HEAD` para `https://<seu-servico>.onrender.com/health`
3. Intervalo sugerido: 5 minutos

**Observações**:
- Esse healthcheck foi implementado no launcher do bot (`run_telegram_bot.py`), não na FastAPI (`src/api/main.py`)
- A rota `/health` da FastAPI só existe quando a API é iniciada explicitamente com `run_api.py`

## Armadilhas & Issues Conhecidas

### ⚠️ Autenticação Frágil
- **Problema**: Alternância entre `credentials.json` (dev) e `st.secrets` (prod)
- **Solução**: Validar ambiente antes de chamar `gspread.authorize()`

### ⚠️ Cache Pode Ficar Stale
- **Problema**: Múltiplas abas atualizando simultaneamente podem desincronizar
- **Solução**: Usar `st.cache_data(ttl=...)` com TTL curto ou invalidar explicitamente via session_state

### ⚠️ Catálogo categórico ainda parcialmente hardcoded
- **Problema**: parte do matching de `Conta`/`Categoria` ainda depende do catálogo em `src/config.py`.
- **Próximo passo**: complementar catálogo com leitura dinâmica por usuário no PostgreSQL para evitar divergência entre base viva e configuração.

### ⚠️ Contas & Categorias Hardcoded
- **Problema**: Valores estão em [src/config.py](src/config.py)
- **Futuro**: Migrar para Google Sheets ou banco de dados

### ⚠️ Sem Tratamento de Erro Robusto
- **Status**: mitigado na API com tratamento padronizado e respostas controladas
- **Próximo passo**: adicionar retry com backoff para operações no Google Sheets em cenários intermitentes

### ⚠️ Ambiente Python Local Pode Estar Inconsistente
- **Problema**: A `.venv` pode estar apontando para um `python.exe` indisponível
- **Solução prática**: Usar [run_telegram_bot.py](run_telegram_bot.py)

### ⚠️ Alertas e Informes Dependem de Processo Vivo
- **Problema**: Os jobs só executam se o processo do bot estiver rodando continuamente
- **Recomendação**: Em produção, manter o bot sob supervisor/serviço e monitorar logs do `JobQueue`

### ⚠️ Deduplicação Local é Baseada em Arquivo
- **Problema**: O controle de reenvio usa arquivos locais em `historico_fluxo/`
- **Recomendação**: Em multi-instância, mover esse estado para storage compartilhado

### ⚠️ Deploy Render exige serviços separados
- **Problema**: `run_telegram_bot.py` não sobe a FastAPI, então Streamlit apontando para API falha.
- **Recomendação**:
  1. Serviço API: `python run_api.py`
  2. Serviço Streamlit: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
  3. Serviço Telegram: `python run_telegram_bot.py` (opcional sob demanda em free tier)

### ⚠️ `ALFRED_API_BASE_URL` deve vir de env do serviço Streamlit
- **Problema**: definir somente em `secrets.toml` não afeta `os.getenv`.
- **Recomendação**: configurar em **Environment Variables** do Render no serviço Streamlit.

### ⚠️ Supabase + Render pode falhar via IPv6
- **Problema**: `OperationalError: Network is unreachable` ao resolver host IPv6.
- **Recomendação**: usar `DATABASE_URL` do **Session Pooler (IPv4)** no formato URI.

### ⚠️ Lentidão por carga total de `/transacoes`
- **Problema**: carregar todo histórico em cada refresh causa timeout/lentidão.
- **Recomendação**:
  - usar `ALFRED_TRANSACOES_LIMIT_DEFAULT` (ex.: `500` ou `1000`)
  - manter `ALFRED_API_TIMEOUT_SECONDS` maior em produção (ex.: `30`)
  - evitar recargas duplicadas após operações compostas (ex.: transferência)

### ⚠️ Snapshot do dashboard pode ser caro sem cache aquecido
- **Problema**: `GET /mobile/dashboard_snapshot` agrega múltiplas visões em uma única resposta e pode ter latência alta em cold start/concorrência.
- **Mitigação atual**:
  - cache em memória no backend (`ALFRED_DASHBOARD_CACHE_TTL_SECONDS`, padrão `60`)
  - invalidação automática em mutações de transação e orçamento
- **Recomendação**:
  - manter TTL > 0 em produção
  - monitorar latência P95 desse endpoint no Render
  - em plano free/sleep, considerar pré-aquecimento leve após wake-up

### ⚠️ Não versionar bancos locais
- **Problema**: arquivos `.db` em Git geram risco de dados sensíveis e conflitos binários.
- **Recomendação**: manter `*.db` no `.gitignore`.

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

**Última atualização**: 16/05/2026  
**Mantido por**: Agentes de IA do GitHub Copilot
