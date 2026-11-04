# Telegram LLM Sheets Bot

A Telegram bot that turns free-form messages into structured leads with an LLM, replies with the extracted fields, and stores the result in Google Sheets.

**Pipeline:** Telegram bot -> LLM -> Google Sheets.

[![CI](https://github.com/alex-yorik/telegram-llm-sheets-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/alex-yorik/telegram-llm-sheets-bot/actions/workflows/ci.yml)
[![Quality Gates](https://github.com/alex-yorik/telegram-llm-sheets-bot/actions/workflows/quality-gates.yml/badge.svg)](https://github.com/alex-yorik/telegram-llm-sheets-bot/actions/workflows/quality-gates.yml)

## Demo

![Telegram bot dialog](docs/images/telegram-bot-response.png)

A user sends a free-form message and receives the extracted fields plus a save confirmation.

![Google Sheets result](docs/images/google-sheets-result.png)

The same lead is appended as a new row in Google Sheets.

## About the Development Process

This project was developed under the direction of its owner, who acted as the project lead and AI development orchestrator. The owner defined the requirements, system constraints, architecture-level decisions, task breakdown, and acceptance criteria; coordinated AI coding agents; reviewed their output; and directed testing, security checks, and quality improvements. AI agents assisted with code implementation, analysis, and testing under human direction. The owner remained responsible for technical decisions, validation, and final acceptance of the delivered work.

## Features

- **LLM-powered extraction.** Converts unstructured text into a validated `Lead` model with `name`, `phone`, `service`, `date`, and `time` fields.
- **Rate limiting.** Per-user in-memory limiter allows 3 requests per 60-second window and blocks the fourth before any paid LLM call is made.
- **Concurrency safety.** An `asyncio.Lock` serializes the duplicate check and mark, so concurrent identical updates cannot both pass deduplication and trigger duplicate LLM requests.
- **Deduplication.** Processed `(chat_id, message_id)` pairs are tracked in a bounded deque to prevent duplicate sheet rows.
- **Robust error handling.** Handles LLM validation failures, provider timeouts, empty extractions, oversized messages, non-text messages, and Google Sheets outages without crashing the bot. Startup succeeds even when Sheets is temporarily unavailable.
- **Google Sheets integration.** Automatically creates the header row, appends leads with `value_input_option="RAW"` to prevent formula injection, and runs blocking `gspread` calls through `asyncio.to_thread`.
- **Docker support.** Ships with a `python:3.12-slim` image, a non-root runtime user, a Compose service, a read-only credentials mount, and graceful shutdown on `SIGINT` / `SIGTERM`.
- **Strict CI/CD pipelines.** GitHub Actions cover tests, coverage gates, linting, Docker builds, secret scanning, dependency auditing, and static security analysis.

## Architecture & Tech Stack

```text
Telegram user
    -> Telegram Bot API (long polling)
    -> handlers.py
        -> llm.py -> OpenAI-compatible API -> validated Pydantic Lead
        -> sheets.py (gspread via asyncio.to_thread) -> Google Sheets
```

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Telegram | python-telegram-bot 20.7 |
| LLM | OpenAI Python SDK / OpenAI-compatible API (OpenAI, OpenRouter, etc.) |
| Data validation | Pydantic 2 and pydantic-settings |
| Google Sheets | Google Sheets API via gspread and a Google Service Account |
| Testing | pytest, pytest-asyncio, pytest-cov |
| Linting and formatting | ruff |
| Security tooling | Bandit, pip-audit, Gitleaks |
| Runtime and delivery | Docker, Docker Compose, GitHub Actions |

### Project layout

```text
.
├── main.py                 # Application setup, polling, graceful shutdown
├── handlers.py             # Commands, text handling, rate limiting, deduplication
├── llm.py                  # LLM extraction, JSON parsing, validation errors
├── sheets.py               # Google Sheets client and row appends
├── models.py               # Pydantic Lead model
├── config.py               # Environment-based settings
├── tests/                  # Unit tests with all external APIs mocked
├── .github/workflows/      # CI and Quality Gates pipelines
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Quality & Testing

The project maintains **98%+ test coverage** measured by `pytest` with `pytest-cov`. The current suite contains **89 tests** and reports **99.14% total coverage** (100% for `handlers.py`, `config.py`, `models.py`, and `sheets.py`).

Every external dependency is isolated with mocks: Telegram updates are mocked, `llm.AsyncOpenAI` is patched, and Google credentials, `gspread.authorize`, and worksheets are patched. No real Telegram, LLM, or Google Sheets requests are made during the unit test run.

The CI pipeline is split into two GitHub Actions workflows:

| Workflow | Jobs | Purpose |
|---|---|---|
| `ci.yml` | `test`, `lint`, `docker-build` | Runs pytest with coverage, ruff checks, Bandit, and builds the Docker image. |
| `quality-gates.yml` | `secrets-scan`, `pip-audit`, `bandit`, `coverage-gate`, `modularity` | Runs Gitleaks, audits runtime and development dependencies, enforces the coverage threshold, and checks file/function size limits. |

The coverage gate fails below 80%, while the measured suite stays above 99%. Strict security checks run through **Bandit**, **pip-audit**, and **Gitleaks** on every push and pull request to `main`.

Run the full verification locally:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

python -m pytest --cov=. --cov-report=term-missing
ruff check .
ruff format --check .
bandit -c pyproject.toml -r . -ll -q
pip-audit -r requirements.txt
```

## Getting Started

### Prerequisites

- Docker and Docker Compose v2
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- An API key for an OpenAI-compatible LLM provider
- A Google Cloud project with the Google Sheets API enabled
- A Google Service Account JSON key

### 1. Clone the repository

```bash
git clone https://github.com/alex-yorik/telegram-llm-sheets-bot.git
cd telegram-llm-sheets-bot
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your own values:

```env
TELEGRAM_BOT_TOKEN=0000000000:YOUR_BOT_TOKEN
LLM_API_KEY=sk-your-llm-key
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=30
GOOGLE_SPREADSHEET_ID=your-spreadsheet-id
GOOGLE_SHEET_NAME=Sheet1
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account.json
LOG_LEVEL=INFO
```

`GOOGLE_APPLICATION_CREDENTIALS` is the in-container path. Keep the default `/app/credentials/service-account.json` and do not use a host path here.

To use OpenRouter, set:

```env
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_MODEL=your-openrouter-model-id
```

### 3. Add the Google Service Account key

Download the JSON key from Google Cloud and place it at:

```text
./credentials/service-account.json
```

Share the target spreadsheet with the service account email as **Editor**. The `credentials/` directory is mounted read-only into the container and the key is gitignored.

### 4. Start the bot

```bash
docker compose up -d --build
```

### 5. Check logs and container status

```bash
docker compose ps
docker compose logs -f --tail=30
```

After changing application code or the Docker image:

```bash
docker compose down && docker compose up -d --build
```

Expected startup messages:

```text
sheets - INFO - GoogleSheetsClient initialized (sheet=Sheet1)
__main__ - INFO - Bot started (polling).
```

### Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | - | Bot token from @BotFather. |
| `LLM_API_KEY` | Yes | - | API key for the LLM provider. |
| `LLM_API_BASE` | No | `https://api.openai.com/v1` | Base URL of the OpenAI-compatible API. |
| `LLM_MODEL` | No | `gpt-4o-mini` | Model name or provider-specific model ID. |
| `LLM_TIMEOUT_SECONDS` | No | `30` | LLM request timeout in seconds. |
| `GOOGLE_SPREADSHEET_ID` | Yes | - | Spreadsheet ID from the Google Sheets URL. |
| `GOOGLE_SHEET_NAME` | No | `Sheet1` | Worksheet name. Falls back to the first sheet if not found. |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | - | In-container path to the service account JSON. |
| `LOG_LEVEL` | No | `INFO` | Python log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |

## Security

- **Secrets are never committed.** `.env`, `credentials/*.json`, and local data are excluded by `.gitignore`. Only `.env.example` with placeholders is tracked.
- **Environment-based configuration.** Runtime secrets are loaded from `.env` through `pydantic-settings`; no credentials are hardcoded.
- **Gitleaks protection with documented false positives.** Secret scanning runs in GitHub Actions on every push and pull request. Confirmed false positives are recorded by fingerprint in `.gitleaksignore` with an explanation, so they cannot hide real leaks while keeping the scan strict.
- **Least-privilege runtime.** The Docker container runs as a non-root user (`uid 1000`), and the Google credentials directory is mounted read-only.
- **Privacy-aware logging.** Logs contain metadata such as `correlation_id`, message length, processing stage, and outcome. Telegram `chat_id` / `user_id`, message text, extracted personal data, spreadsheet IDs, credential paths, and API keys are not written to logs.
- **Formula injection protection.** Sheet writes use `value_input_option="RAW"`.
- **Dependency and static analysis.** Bandit, pip-audit, and Gitleaks are blocking quality gates for changes targeting `main`.

## Operational Notes

- Rate limiting and deduplication are in-memory and per process. They reset when the bot restarts.
- Google Sheets writes are synchronous but isolated with `asyncio.to_thread`; transient Google API failures are reported to the user and are not retried automatically.
- The bot is a portfolio/demonstration project. Production use with real personal data requires a separate privacy, legal, and security review.

## License

All rights reserved. See [LICENSE](LICENSE) for the full terms.
