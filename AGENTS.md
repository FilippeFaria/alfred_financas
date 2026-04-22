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
  └── analytics/
      ├── calculations.py    # Cálculos (saldo, despesas por categoria)
      └── charts.py          # Gráficos Plotly

paginas/
  ├── 1_transacao.py         # Aba: Registro de transações
  ├── 2_analise.py           # Aba: Análise de despesas
  ├── 3_alfred.py            # Aba: Análise automática (IA) — PLACEHOLDER
  ├── 4_patrimonio.py        # Aba: Patrimônio/ativos
  └── 5_extrato.py           # Aba: Extrato de movimentações

app.py                        # Orquestrador: carrega dados, renderiza abas
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

---

## Documentação Relacionada

- [Readme.md](Readme.md) — Visão geral da estrutura
- Notebook de análise: [analise_fluxo_caixa.ipynb](analise_fluxo_caixa.ipynb)
- Google Sheets: Sincronizado via [src/services/google_sheets.py](src/services/google_sheets.py)

---

**Última atualização**: 22/04/2026  
**Mantido por**: Agentes de IA do GitHub Copilot
