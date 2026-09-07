# Telegram LLM Sheets Bot

## 1. Project Description

Telegram bot that receives free-form text messages, extracts structured lead data (name, phone, service, date, time) using an LLM (OpenAI-compatible API), replies to the user with the extracted fields, and appends the lead as a row in Google Sheets.

## 2. Architecture

```text
Telegram user → Telegram Bot API (polling) → handlers.py
    → llm.py → LLM API (OpenAI-compatible, e.g. OpenRouter) → Lead model
    → sheets.py (gspread, sync, via asyncio.to_thread) → Google Sheets
```

- `python-telegram-bot v20+` polls Telegram with `Application` + `MessageHandler`.
- `llm.py` sends a system prompt requesting strict JSON (`name/phone/service/date/time`) and validates it into a Pydantic `Lead` model.
- `sheets.py` (`GoogleSheetsClient`) opens the spreadsheet by ID via a Service Account and appends a row with `value_input_option='RAW'`.
- Configuration is loaded from environment variables via `pydantic-settings` (`config.py`).

## 3. Requirements

- Docker and Docker Compose (v2, `docker compose` command)
- Telegram account (to talk to [@BotFather](https://t.me/BotFather) and to test the bot)
- OpenRouter API key (free tier available) — or any OpenAI-compatible endpoint
- Google Cloud account (free tier is enough for the Sheets API)

## 4. Deployment Instructions

### a) Create a Telegram bot via @BotFather

1. Open Telegram and talk to [@BotFather](https://t.me/BotFather).
2. Send `/newbot`, choose a display name and a username ending in `bot`.
3. Copy the bot token, e.g. `1234567890:AA...`. You will put it into `.env` as `TELEGRAM_BOT_TOKEN`.

### b) Get an OpenRouter API key

1. Sign up at [openrouter.ai](https://openrouter.ai).
2. Go to [openrouter.ai/keys](https://openrouter.ai/keys) and create a key.
3. Copy the key (starts with `sk-or-v1-...`). You will use it as `LLM_API_KEY`. Free models (e.g. `...:free`) work without billing.

### c) Google Cloud setup

1. **Create a project:** go to [Google Cloud Console](https://console.cloud.google.com/), create a new project (e.g. `telegram-bot-sheets`).
2. **Enable the Google Sheets API:** in the project, open *APIs & Services → Library*, find *Google Sheets API* and click *Enable*.
3. **Create a Service Account:** go to *IAM & Admin → Service Accounts → Create Service Account*. Give it a name (e.g. `telegram-bot`), skip optional role grants.
4. **Download the JSON key:** open the service account → *Keys → Add Key → Create new key → JSON*. Save the file as `service-account.json`.
5. **Create a Google Spreadsheet:** go to [sheets.google.com](https://sheets.google.com/), create a new spreadsheet. Copy the spreadsheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`.
6. **Share the spreadsheet with the service account as Editor:** in the spreadsheet click *Share*, paste the service account email (e.g. `telegram-bot@YOUR-PROJECT.iam.gserviceaccount.com`), set role to *Editor*, uncheck *Notify people*, click *Share*. Without this step writes fail with permission errors.

### d) Clone the repository

```bash
git clone <YOUR_REPO_URL> telegram-llm-sheets-bot
cd telegram-llm-sheets-bot
```

### e) Copy `.env.example` to `.env` and fill in variables

```bash
cp .env.example .env
```

Edit `.env` (see the Environment variables table below). Example (placeholders only):

```env
TELEGRAM_BOT_TOKEN=1234567890:YOUR_BOT_TOKEN
LLM_API_KEY=sk-or-v1-YOUR_KEY
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_MODEL=nvidia/nemotron-3.5-lightning:free
LLM_TIMEOUT_SECONDS=30
GOOGLE_SPREADSHEET_ID=YOUR_SPREADSHEET_ID
GOOGLE_SHEET_NAME=Sheet1
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account.json
LOG_LEVEL=INFO
```

> Note: `GOOGLE_APPLICATION_CREDENTIALS` is the **in-container** path. Keep the default `/app/credentials/service-account.json` — do not put a host path here.

### f) Place `service-account.json`

Copy the downloaded Google Service Account key to:

```text
./credentials/service-account.json
```

The file is mounted read-only into the container (`./credentials:/app/credentials:ro`). It is gitignored — never commit it.

```bash
ls -la credentials/
# service-account.json  .gitkeep
```

### g) Start the bot

```bash
docker compose up -d --build
```

### h) View logs

```bash
docker compose logs -f
docker compose logs -f --tail=30
```

Expected startup lines:

```text
sheets - INFO - GoogleSheetsClient initialized: spreadsheet_id=... sheet=Sheet1
__main__ - INFO - Bot started (polling).
```

Useful commands:

```bash
docker compose ps
docker compose down
docker compose down && docker compose up -d --build
```

## 5. Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Bot token from @BotFather. |
| `LLM_API_KEY` | Yes | — | API key for the LLM provider (e.g. OpenRouter). |
| `LLM_API_BASE` | No | `https://api.openai.com/v1` | Base URL of the OpenAI-compatible API. For OpenRouter: `https://openrouter.ai/api/v1`. |
| `LLM_MODEL` | No | `gpt-4o-mini` | Model name, e.g. `gpt-4o-mini` or an OpenRouter model id. |
| `LLM_TIMEOUT_SECONDS` | No | `30` | Timeout for the LLM request in seconds. |
| `GOOGLE_SPREADSHEET_ID` | Yes | — | Google Spreadsheet ID (from the sheet URL). |
| `GOOGLE_SHEET_NAME` | No | `Sheet1` | Worksheet name. If not found, the first sheet is used. |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | — | **In-container** path to the service account JSON. Keep `/app/credentials/service-account.json`. |
| `LOG_LEVEL` | No | `INFO` | Python log level (`DEBUG`, `INFO`, `WARNING`, ...). |

## 6. Usage Examples

**Input message (user → bot):**

```text
Hi, I'm Ivan, phone +1-555-010-2233, I need a haircut tomorrow at 10:00
```

**Bot response:**

```text
Extracted data:
Name: Ivan
Phone: +1-555-010-2233
Service: haircut
Date: tomorrow
Time: 10:00
✅ Data saved to spreadsheet
```

Missing fields are shown as `-`.

**Example row in Google Sheets:**

| Name | Phone | Service | Date | Time | Original Message | Created At |
|---|---|---|---|---|---|---|
| Ivan | +1-555-010-2233 | haircut | tomorrow | 10:00 | Hi, I'm Ivan, phone +1-555-010-2233, I need a haircut tomorrow at 10:00 | 2026-09-07T06:15:52.448049+00:00 |

The header row is created automatically if the sheet is empty. `None` values are stored as empty strings. Writes use `value_input_option='RAW'` to prevent formula injection. `Created At` is a UTC ISO-8601 timestamp.

## 7. Error Handling

| Situation | What the user sees | What happens internally |
|---|---|---|
| LLM returns invalid JSON / validation fails (`LLMValidationError`) | `Could not extract data, please send more details` | Error logged, no sheet write. |
| LLM network/API/timeout error (`LLMRequestError`) | `Processing error, try again later` | Error logged, no sheet write. |
| Unexpected error during LLM step | `An error occurred` | `logger.exception`, no sheet write. |
| Sheets not configured at startup (`SheetsError`) | Bot still starts; user gets extracted data without the `✅` line | `Sheets unavailable, bot starts without writing` logged; `sheets_client` is `None`, write is skipped with a warning. |
| Sheets write fails at message time (`SheetsError`) | User still gets extracted data, but **without** `✅ Data saved to spreadsheet` | `Failed to save lead to spreadsheet` logged with traceback; exception is swallowed so the bot keeps working. |

The synchronous `gspread` call runs via `asyncio.to_thread()` so polling is never blocked.

## 8. Project Structure

```text
.
├── main.py              # Entry point: logging, Application setup, polling loop
├── handlers.py          # /start and text handlers; LLM → Sheets orchestration
├── llm.py               # LLM extraction: prompt, OpenAI client, Lead validation
├── sheets.py            # GoogleSheetsClient, SheetsError, append_lead + header logic
├── models.py            # Pydantic Lead model (name/phone/service/date/time)
├── config.py            # pydantic-settings Settings loaded from .env
├── requirements.txt     # python-telegram-bot, pydantic, openai, gspread, google-auth
├── Dockerfile           # python:3.12-slim image, runs `python main.py`
├── docker-compose.yml   # bot service, .env, credentials + data mounts, healthcheck
├── .env.example         # Template for environment variables (no secrets)
├── credentials/         # Place service-account.json here (gitignored)
│   └── .gitkeep
└── data/                # Local persistent data mount
```

## 9. License

MIT License.

Copyright (c) 2026.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
