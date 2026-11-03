# README Consistency Check (TZ Section 6)

- **Date:** 2026-11-03
- **Branch:** `fix/final-hardening`
- **Baseline commit:** `b3ec090`
- **Scope:** public documentation only (`README.md`, `SECURITY.md`, `TECH_DEBT.md`, `docs/`)
- **Author position:** AI-assisted self-review, not an independent third-party audit.
- **Application code changed:** no.

## Verdict

The public documentation matches the actual implementation after the fixes listed
below. Two items remain `NOT VERIFIED` because they require real external
services or human visual review, not because of a known defect.

## Checklist

| # | TZ Section 6 item | Status | Evidence |
|---|---|---|---|
| 1 | README features exist in code | **VERIFIED** | `/start` privacy notice and text-only reply in `handlers.py`; extraction and fence stripping in `llm.py`; header creation and `RAW` writes in `sheets.py`; polling and graceful shutdown in `main.py`; env defaults in `config.py`. |
| 2 | Security/Privacy statements match actual logging | **VERIFIED** | `tests/test_logging_privacy.py` (17 tests) passes. `SECURITY.md` now lists `message_id` as logged and explicitly excludes `chat_id`/`user_id`. README error table no longer claims a traceback is logged (code logs error type only). |
| 3 | Demo / Portfolio status preserved | **VERIFIED** | `README.md` Status section (`Level D: Demo / Portfolio`), `SECURITY.md`, and `TECH_DEBT.md` all state this is a demonstration prototype. |
| 4 | Third-party LLM and Google Sheets limits are honest | **VERIFIED** | README "Security and privacy notes" and "Known limitations"; `TECH_DEBT.md` items 3-5; `SECURITY.md` known limitations. Message content goes to a third-party LLM, data is stored in Google Sheets, no GDPR/HIPAA, no encryption at rest beyond Google. |
| 5 | No production-readiness claim | **VERIFIED** | README line 12: "not a production system". The word "production" appears only in "if this project evolves beyond a demo" and in negative statements. |
| 6 | AI-assisted workflow with human technical direction | **VERIFIED** | README "Development approach" describes the owner as project lead and AI development orchestrator, defining requirements, architecture, acceptance criteria, review, and final acceptance; AI reviews are not called independent audits. |
| 7 | Install/run instructions match dependencies and Docker | **VERIFIED** | `requirements.txt` is runtime only; `requirements-dev.txt` contains pytest/ruff/bandit/pip-audit. README local-check block now installs `requirements-dev.txt`. Dockerfile installs `requirements.txt` only; README uses `docker compose up -d --build`. |
| 8 | Links and filenames in README are current | **VERIFIED** | All local targets exist: `docs/images/telegram-bot-response.png`, `docs/images/google-sheets-result.png`, `docs/integration-smoke-test.md`, `SECURITY.md`, `TECH_DEBT.md`, `LICENSE`. Project tree updated: `requirements-dev.txt`, `docs/images/`, `docs/reports/`, data volume in compose. CI job list updated with `pip-audit`. |
| 9 | No secrets, local paths, or private identifiers | **VERIFIED** | A grep for absolute home/workspace path prefixes in `README.md`, `SECURITY.md`, and `TECH_DEBT.md` returns nothing. README uses only placeholders and the in-container path `/app/credentials/service-account.json`. The repo owner/handle in the clone URL is public. |

## Additional Verification

| Check | Status | Evidence |
|---|---|---|
| Unit tests after doc changes | **VERIFIED** | `81 passed, 0 skipped`; unit-test coverage `99.32%` (threshold 80%). |
| External URLs reachable | **NOT VERIFIED** | Out of scope: documentation check only; no network fetch of `github.com`, `t.me`, `openrouter.ai`, `console.cloud.google.com`. |
| Screenshots reflect the current UI/data | **NOT VERIFIED** | Requires human visual review; files exist and are referenced correctly. |
| Live Telegram / LLM / Google Sheets run | **NOT VERIFIED** | Manual smoke test not executed in this phase. See `docs/integration-smoke-test.md`. |

## Fixes Applied

- `README.md`: local checks now install `requirements-dev.txt`; quality-gates job
  list includes `pip-audit`; deduplication described as a bounded in-memory
  `deque` (last 1000), not a `set`; duplicate-logging row clarifies that
  `message_id` is logged and `chat_id` is not; startup-without-Sheets row now
  shows the actual save warning; unexpected-error row no longer claims a
  traceback; OpenRouter setup mentions `LLM_API_BASE`; project tree corrected and
  extended.
- `SECURITY.md`: dedup key and bounded store corrected; `chat_id` explicitly
  listed as never logged; `message_id` explicitly listed as potentially logged;
  key-feature wording no longer says "Telegram identifiers" while logging
  `message_id`.
- `TECH_DEBT.md`: dedup limitation rewritten to match the `deque(maxlen=1000)`
  implementation; removed the stale refactoring item about module-level
  `Settings()` (already fixed by `load_settings()` in commit `9208c4c`).

## Commit Scope Note

`docs/reports/graphify-baseline/` remains untracked and is intentionally not
committed: its `.graphify_root` and `.graphify_python` files contain absolute
local machine paths to the workspace and Python tool directory, which would leak
development environment details into the public repository.
