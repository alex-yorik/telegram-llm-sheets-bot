# Integration smoke test

This guide describes a **manual** smoke test against real Telegram, LLM, and
Google Sheets APIs. It verifies that the configured credentials and network
paths actually work. It is intentionally **not** part of CI: public CI runs
only the mocked unit tests and must never receive real secrets.

## What this test proves

The automated suite (`pytest`) isolates every external dependency with mocks:

- Telegram updates are `MagicMock` objects; no call to the Bot API is made.
- `llm.AsyncOpenAI` is patched, so no LLM request leaves the machine.
- `sheets.Credentials`, `gspread.authorize`, and `gspread.Worksheet` are
  patched, so no Google API call is made.

Therefore unit-test coverage proves application logic only. This smoke test is
the manual complement that proves the real services are reachable and that the
credentials have the required permissions.

## Safety rules

- Use a **dedicated test bot**, a **dedicated LLM key**, and a **dedicated test
  spreadsheet**. Never point this guide at production resources.
- Use only synthetic data (for example `Test User`, `+1-555-010-0000`). Do not
  enter real personal data.
- Never commit tokens, key files, spreadsheet IDs, or test rows. Keep all
  secrets outside the repository (this guide uses `/tmp`).
- Never add this procedure to GitHub Actions or any other public CI with
  secrets. Run it locally or in a trusted environment only.

## 1. Preparation

### 1.1 Telegram test bot

1. Open [@BotFather](https://t.me/BotFather) and send `/newbot`.
2. Create a bot named like `telegram-llm-sheets-bot-smoke` with a unique
   username ending in `bot`.
3. Copy the token. It is used only in the local smoke env file.

### 1.2 Test LLM API key

1. Create a separate key with a low spending limit (for example on
   [openrouter.ai/keys](https://openrouter.ai/keys)).
2. Note the base URL and model to use. A free model keeps the cost at zero.

### 1.3 Test Google Sheet

1. In the [Google Cloud Console](https://console.cloud.google.com/), create or
   reuse a **test** project and enable the **Google Sheets API**.
2. Create a dedicated **test** service account and download its JSON key.
3. Create a new spreadsheet, for example `telegram-bot-smoke-test`, and copy its
   spreadsheet ID from the URL.
4. Share the spreadsheet with the service account email as **Editor**.

### 1.4 Local working directory

All secrets stay outside the repository:

```bash
mkdir -p /tmp/telegram-bot-smoke/credentials
cp /path/to/test-service-account.json \
  /tmp/telegram-bot-smoke/credentials/service-account.json
```

Create `/tmp/telegram-bot-smoke/.env.smoke` with synthetic values:

```env
TELEGRAM_BOT_TOKEN=0000000000:SMOKE_TEST_BOT_TOKEN
LLM_API_KEY=sk-smoke-test-key
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_MODEL=your-free-test-model
LLM_TIMEOUT_SECONDS=30
GOOGLE_SPREADSHEET_ID=smoke-test-spreadsheet-id
GOOGLE_SHEET_NAME=Sheet1
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account.json
LOG_LEVEL=INFO
```

Restrict the file permissions:

```bash
chmod 600 /tmp/telegram-bot-smoke/.env.smoke
chmod 600 /tmp/telegram-bot-smoke/credentials/service-account.json
```

## 2. Run

From the repository root, build the image and start one smoke container. The
`--env-file` supplies the test configuration, and the credentials directory is
mounted read-only.

```bash
docker build -t telegram-llm-sheets-bot:smoke .

docker run -d \
  --name telegram-llm-sheets-bot-smoke \
  --env-file /tmp/telegram-bot-smoke/.env.smoke \
  -v /tmp/telegram-bot-smoke/credentials:/app/credentials:ro \
  telegram-llm-sheets-bot:smoke
```

Follow the logs:

```bash
docker logs -f --tail=30 telegram-llm-sheets-bot-smoke
```

Then exercise the bot in Telegram:

1. Send `/start`. Expect the greeting and the privacy note.
2. Send a synthetic text message, for example:
   `Hi, I'm Test User, phone +1-555-010-0000, I need a haircut tomorrow at 10:00`.
3. Send a non-text message (a sticker or photo). Expect the text-only reply.

## 3. Expected results

| Check | Expected result |
|---|---|
| Startup log | `GoogleSheetsClient initialized` and `Bot started (polling).` |
| `/start` | Greeting with the privacy note about the external LLM and Google Sheets. |
| Synthetic text message | Reply lists the extracted fields and ends with `Data saved to spreadsheet`. |
| Google Sheet | A header row is created if the sheet was empty, then one row with the synthetic lead is appended. |
| Non-text message | `I only process text messages. Please send me a text description.` |
| Log privacy | Logs contain `correlation_id`, length, and stage only. No token, API key, spreadsheet ID, `chat_id`/`user_id`, or message text. |
| Container | `docker ps` shows the container running; no restart loop. |

If Google Sheets credentials are wrong, the bot still starts (by design) and
replies with extracted data plus a save warning. That is a failed smoke test for
the Sheets integration, not a crash.

## 4. Cleanup

Stop and remove the smoke container and image:

```bash
docker stop telegram-llm-sheets-bot-smoke
docker rm telegram-llm-sheets-bot-smoke
docker rmi telegram-llm-sheets-bot:smoke
```

Remove the test data from the spreadsheet: delete the synthetic rows, or delete
the dedicated spreadsheet entirely.

Revoke the temporary credentials:

1. Delete or disable the test LLM API key.
2. Revoke the test bot token via BotFather (`/revoke`) or delete the test bot.
3. Delete the test service account key in Google Cloud.

Remove the local secret files:

```bash
rm -rf /tmp/telegram-bot-smoke
```

Finally, confirm the repository is clean and contains no secrets:

```bash
git status --short
git grep -nE 'SMOKE_TEST_BOT_TOKEN|sk-smoke-test-key|smoke-test-spreadsheet-id' || true
```

## 5. Reporting

Record the date, the model used, and the outcome (pass/fail per check) in the
team's internal notes. Do not paste tokens, spreadsheet IDs, or test personal
data into issues or pull requests. Only report the status and the observed
behavior.

A smoke test that was not actually executed must be reported as
`NOT VERIFIED`, even when the unit tests pass.
