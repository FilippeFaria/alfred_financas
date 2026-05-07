# Alfred Financas Mobile (Flutter)

Base inicial do aplicativo mobile da ETAPA 4.

## O que ja esta pronto

- Arquitetura por features em `lib/core` e `lib/features`
- Navegacao com `go_router` e shell com `NavigationBar`
- Estado com `flutter_riverpod`
- Cliente HTTP com `dio`
- Ambiente `dev/prod` com `--dart-define`
- Integracao basica com backend:
  - `GET /health`
  - `GET /saldo`
  - `GET /transacoes`

## Estrutura

```text
lib/
  core/
    env/
    network/
    router/
    theme/
  features/
    auth/
    dashboard/
    transactions/
    insights/
    settings/
```

## Como executar

1. Instale o Flutter SDK.
2. Na pasta `mobile_app`, execute:

```bash
flutter create .
flutter pub get
flutter run --dart-define=FLAVOR=dev --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

Para producao:

```bash
flutter run --release --dart-define=FLAVOR=prod --dart-define=API_BASE_URL=https://sua-api
```
