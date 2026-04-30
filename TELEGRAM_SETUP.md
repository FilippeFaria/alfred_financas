# Instruções para Configurar o Bot do Telegram

## Passo 1: Obter Token do BotFather
1. Abra o Telegram e procure por @BotFather.
2. Envie `/newbot` para criar um novo bot.
3. Siga as instruções:
   - Digite o nome do bot (ex.: "Alfred Finanças Bot").
   - Digite o username (ex.: "alfred_financas_bot" – deve terminar com "bot").
4. Copie o token fornecido (algo como `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`).
5. Configure o token no ambiente ou no arquivo `src/config.py`.

## Passo 2: Definir o token em ambiente (recomendado)
No Windows PowerShell use:
```
$env:TELEGRAM_BOT_TOKEN = "<SEU_TOKEN>"
```
No Linux/macOS use:
```
export TELEGRAM_BOT_TOKEN="<SEU_TOKEN>"
```

## Passo 3: Testar o Token (Opcional)
Use este comando curl para verificar se o token funciona:
```
curl "https://api.telegram.org/bot<SEU_TOKEN>/getMe"
```
Substitua `<SEU_TOKEN>` pelo seu token. Deve retornar informações do bot em JSON.

## Passo 4: Executar o Bot
No diretório raiz do projeto, execute:
```
python -m src.telegram_bot.bot
```

Se o bot iniciar corretamente, envie `/start` no Telegram para testar.

## Falha de dados do Google Sheets
O bot agora tenta carregar os dados do Google Sheets e, se não conseguir, usa o CSV local `fluxo_de_caixa.csv` como fallback.

## Notas
- Em produção, mova o token para `st.secrets` ou use a variável de ambiente `TELEGRAM_BOT_TOKEN`.
- Se houver erros, verifique os logs no console e confirme se o arquivo `credentials.json` está disponível ou se o CSV local existe.