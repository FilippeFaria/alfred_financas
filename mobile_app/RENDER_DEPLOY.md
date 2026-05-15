# Deploy do mobile_app no Render (Web)

Este app Flutter web foi preparado para subir no Render com Docker e minima customizacao.

## 1) Pre-condicoes

- API FastAPI acessivel publicamente (Render ou outro host)
- Endpoint de health retornando `200`:
  - `GET https://<url-da-api>/health`
- CORS da API permitindo o frontend (atualmente esta amplo com `allow_origins=["*"]`)

## 2) Configurar o Web Service no Render

Crie um novo **Web Service** com runtime **Docker** e configure:

- **Repository**: este repositorio
- **Root Directory**: `mobile_app`
- **Dockerfile Path**: `Dockerfile.web`
- **Branch**: sua branch de deploy

Variavel de ambiente obrigatoria:

- `API_BASE_URL=https://<url-da-sua-api-no-render>`

Observacao: no Docker do Render, as variaveis de ambiente sao disponibilizadas como build args com a mesma chave. O `Dockerfile.web` usa `ARG API_BASE_URL` no `flutter build web`.

## 3) Primeiro deploy

Depois do deploy:

- abra a URL `onrender.com` gerada pelo serviço
- valide navegacao nas rotas:
  - `/transactions`
  - `/dashboard`
  - `/insights`
  - `/settings`
- recarregue em rota interna para confirmar fallback SPA (sem 404)

## 4) Smoke test funcional

Validar no frontend:

- carregamento de saldo/transacoes/dashboard snapshot
- pendencias IA carregando em Insights
- acoes de pendencia funcionando: `Confirmar`, `Editar`, `Ignorar`

Comportamento esperado no navegador:

- integracoes nativas Android de notificacao ficam desativadas/ocultas
- revisao de pendencias vindas do mobile continua disponivel
