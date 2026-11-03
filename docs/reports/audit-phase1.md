# Audit Report — Phase 1 (Initial Audit)

- **Date:** 2026-11-02
- **Commit:** `a52ea7f` (`fix: redact bot token from logs, English UX, working Docker healthcheck`)
- **Branch:** `feat/publication-prep`
- **Rollback tag:** `pre-publication-prep` (pushed to `origin`)
- **Scope:** read-only audit. No source code was modified. Only this report was added.

---

## 1. Secret Scan Results

### 1.1 Current working tree (`gitleaks detect --no-git`)

Result: **2 findings**

| # | File | Line | RuleID | Verdict |
|---|------|------|--------|---------|
| 1 | `.env` | 2 | `generic-api-key` | **Real value present locally** (untracked file) |
| 2 | `sheets.py` | 49 | `generic-api-key` | **False positive** — matched the Google service-account credential loader call, no secret |

Notes:
- `.env` is listed in `.gitignore` and `.dockerignore`, is **not tracked** and was **never tracked** (`git log --all -- .env` is empty).
- The local `.env` contains non-placeholder values for `TELEGRAM_BOT_TOKEN` (49 chars), `LLM_API_KEY` (42 chars) and `GOOGLE_SPREADSHEET_ID` (47 chars). Values were **not** printed and are **not** in this report.
- Recommendation: treat these as live credentials. Do **not** commit `.env`; rotate the Telegram token and LLM key if the file was ever shared or uploaded anywhere.

### 1.2 Git history (`gitleaks detect --log-opts="--all"`)

Result: **1 finding**

| # | File | Line | Commit | RuleID | Verdict |
|---|------|------|--------|--------|---------|
| 1 | `sheets.py` | 49 | `06ba5bd` | `generic-api-key` | **False positive** (same as above) |

Conclusion: **no real secrets found in Git history.** No history rewrite is required. Per policy, no `git filter-repo`, rebase, or force-push was performed.

### 1.3 Tracked-files check

`git ls-files | grep -E '\.env$|credentials/.*\.json'` → **empty**.
Only `.env.example` and `credentials/.gitkeep` are tracked. `.env` and `credentials/*.json` are correctly ignored.

---

## 2. Structure Analysis

Tracked files:

```text
.dockerignore
.env.example
.gitignore
Dockerfile
README.md
config.py
credentials/.gitkeep
docker-compose.yml
handlers.py
llm.py
main.py
models.py
requirements.txt
sheets.py
```

Untracked local files (not in Git): `.env` (live secrets).

Missing vs. expected publication structure:
- `tests/` — absent
- `.github/workflows/` — absent
- `pyproject.toml` / `ruff.toml` — absent
- `SECURITY.md` — absent
- `TECH_DEBT.md` — absent
- `LICENSE` — absent (license text is inlined in README)
- `docs/reports/` — created for this report only
- `data/` — referenced by README and mounted in compose, but does not exist in the repo

Match with expected single-file MVP structure: otherwise matches (6 Python modules + Docker + compose + requirements + env template).

---

## 3. Code Issues Found (per auditor's checklist)

| File | Line | Issue | Priority | Description |
|------|------|-------|----------|-------------|
| `handlers.py` | 37 | `logger.info("Received message ... %s", text)` | **P0** | Full user message is written to logs verbatim. Contains name, phone and other personal data. Must be removed or replaced with metadata only (chat_id + length/hash). |
| `sheets.py` | 107 | `logger.info("Lead saved ... %s", row)` | **P0** | Logs the entire spreadsheet row: name, phone, service, original message. Direct PII leak into logs. |
| `.env` | — | Live credentials on disk | **P0** | Untracked but contains real-looking tokens. Risk if accidentally added/archived. Not in Git history, but rotate if ever shared. |
| `llm.py` | 44-49 | Logs user text (`text=%.100s`) | **P1** | First 100 chars of user message logged. Still PII; should log length only. |
| `llm.py` | 63 | `logger.info("LLM response received: %s", response)` | **P1** | Logs the full SDK response object (headers/usage/body). Verbose, may echo PII; should be removed or reduced to token counts. |
| `llm.py` | 73 | `logger.info("LLM raw content: %s", content)` | **P1** | Logs raw LLM JSON output, which repeats user PII. Must not be logged at INFO. |
| `handlers.py` | 40, 53-64 | No `Lead.has_data()` check | **P1** | If the LLM returns all-null fields, the bot still replies and saves an empty row. `Lead.has_data()` exists in `models.py` but is never called. Should treat empty leads as `LLMValidationError` and ask the user for more details. |
| `models.py` | 15-25 | `has_data()` unused (dead code) | **P1** | Method is defined but never referenced anywhere (`grep` confirms). Either wire it into `handlers.py` or remove it. |
| `config.py` | 26 | `settings = Settings()` at import time | **P1** | Module-level instantiation makes every import require a valid `.env`; blocks unit tests and any tooling that imports the modules without production secrets. Should use a lazy accessor / factory. |
| `main.py` | 34, 38 + `handlers.py` 19, 53 | Duplicate `sheets_client` state | **P1** | Client is stored both in `handlers.sheets_client` and `application.bot_data["sheets_client"]`, with a fallback chain. Single source of truth needed (prefer `bot_data` only). |
| `Dockerfile` | 1-17 | Runs as root | **P1** | No `USER` directive; container runs as root. Add a non-root user and `USER` before `CMD`. |
| — | — | No tests | **P1** | No `tests/` and no pytest coverage for `_strip_code_fences`, `Lead` validation, empty-lead handling, or Sheets error paths. |
| — | — | No CI | **P1** | No `.github/workflows/`; no lint/test/secret-scan gate on push/PR. |
| `sheets.py` | 85-88 | `get_all_values()` on every write | **P2** | Full sheet read on each message to detect emptiness; O(n) API traffic and latency. Cache the header-initialized state instead. |
| `main.py` | 63 | `assert application.updater is not None` | **P2** | `assert` is stripped under `python -O`; use an explicit check/raise. (Bandit B101, Low.) |
| `main.py` | 3-12 | Import order (ruff I001) | **P2** | `import handlers` placed after `from config import settings`; ruff flags unsorted imports. |
| `main.py` | — | No global error handler | **P2** | Unhandled handler exceptions rely on PTB defaults; add `application.add_error_handler`. |
| `llm.py` | 56-62 | No `response_format` / `max_tokens` / `temperature` | **P2** | Relies on prompt-only JSON discipline. Consider `response_format={"type":"json_object"}` (provider permitting) and a token cap. |
| `llm.py` | 50-54 | New `AsyncOpenAI` per request | **P2** | Re-creates client (and HTTP pool) on every message; reuse a module-level client. |

Formula-injection protection: **present** — `sheets.py:92,106` use `value_input_option="RAW"`. Good.

API-key logging: **not directly logged**. `llm.py:44` logs `base_url` and `model` only (safe); no key value in logs. **OK.**

---

## 4. Docker Issues

- **Root user:** `Dockerfile` has no `USER`; process runs as root (P1).
- **Healthcheck location:** defined only in `docker-compose.yml`, not in the `Dockerfile`; acceptable, but see next point.
- **Healthcheck quality:** `pgrep -f 'python main.py'` only proves the process exists, not that polling/Telegram connectivity works. It can report "healthy" for a hung bot (P2).
- **`procps` package:** used by the `pgrep` healthcheck, so it is **not** unused (OK).
- **Base image:** `python:3.12-slim` is not pinned by digest (P2, supply-chain reproducibility).
- **`./data:/app/data` mount:** directory does not exist in repo and is unused by the code (P2). Docker will create it as root on host.
- **No container hardening** (`read_only`, `cap_drop`, `security_opt`, `init: true`, resource limits) in compose (P2).
- `.dockerignore` correctly excludes `.env`, `credentials/*.json`, `data/`, `.git` — **OK** (no secret baked into image).

---

## 5. README Issues

- **Language:** English. Acceptable for public GitHub, but inconsistent with the project's Russian-facing internal conventions; decide and document (P2).
- **AI-assisted authorship disclosure:** **absent**. Public README does not disclose AI-assisted development (P2, required by the task).
- **License mismatch:** README §9 states **MIT License** with full MIT text, but the publication requirement is **"All rights reserved"**. There is also **no `LICENSE` file** (P2, blocker for the license task).
- **Structure accuracy:** README §8 lists `data/` and its purpose, but the directory is not present in the repo (P2).
- **Log accuracy:** README §4h "Expected startup lines" omits the `creds=...` fragment actually emitted by `sheets.py:52-58` (minor, P2).
- **Missing sections:** no Security, Testing, Contributing, or Limitations sections (P2).
- Otherwise the README accurately describes architecture, env vars, error handling, and RAW writes (verified against code).

---

## 6. Dependencies Issues

`requirements.txt`:

```text
python-telegram-bot[job-queue]==20.7
pydantic==2.5.0
pydantic-settings==2.1.0
openai==1.7.0
gspread==6.0.0
google-auth==2.25.0
```

| File | Issue | Priority | Description |
|------|-------|----------|-------------|
| `requirements.txt` | Unused `[job-queue]` extra | P2 | No `JobQueue` / `run_repeating` usage in code. Drop the extra to reduce image surface. |
| `requirements.txt` | Outdated pins | P2 | Current latest: `python-telegram-bot 22.8`, `pydantic 2.14.2`, `pydantic-settings 2.16.2`, `openai 3.42.1`, `gspread 6.2.1`, `google-auth 2.62.0`. Pins are 1-2 major versions behind; review/changelog before bumping. |
| `requirements.txt` | No lockfile / no hashes | P2 | Reproducibility and supply-chain integrity not enforced. |
| `requirements.txt` | No dev-dependency separation | P2 | `pytest`/`ruff`/`bandit` are not declared anywhere; add `requirements-dev.txt` or `pyproject.toml` extras. |

Bandit `-ll` (Medium+): **no findings**. Bandit `-l` (Low+): 1 finding — `main.py:63` `assert_used` (B101, Low).

Ruff: **1 error** — `I001` unsorted imports in `main.py` (auto-fixable).

---

## 7. Summary

- **Total issues:** 22
- **P0 (blockers):** 3
- **P1 (important):** 9
- **P2 (nice-to-have):** 10
- **Secrets in Git history:** none (only a false positive)
- **Live secrets in untracked `.env`:** yes (rotate if ever exposed)

---

## 8. Recommended Fix Order

1. **P0 — stop PII logging:** remove full message (`handlers.py:37`) and full row (`sheets.py:107`) logging; reduce `llm.py:44,63,73` to metadata.
2. **P0 — local secrets:** keep `.env` untracked; rotate Telegram token and LLM key if the file was ever shared. No history rewrite needed.
3. **P1 — empty-lead validation:** call `Lead.has_data()`; reject empty extraction with a user-facing "send more details".
4. **P1 — config testability:** replace import-time `Settings()` with a lazy accessor so tests can import modules without production env.
5. **P1 — Docker:** add non-root user + `USER` in `Dockerfile`.
6. **P1 — deduplicate `sheets_client`:** single source of truth via `bot_data`.
7. **P1 — tests + CI:** add `tests/` (red → green for the above fixes) and `.github/workflows/` (ruff, pytest, gitleaks).
8. **P2 — publication assets:** `LICENSE` = All rights reserved, fix README license section, add AI-assistance disclosure, `SECURITY.md`, `TECH_DEBT.md`, `pyproject.toml`/`ruff.toml`, README corrections (`data/`, log line).
9. **P2 — dependencies & hardening:** drop `[job-queue]`, review version bumps, add lockfile/dev requirements, improve healthcheck, container hardening, reuse `AsyncOpenAI` client, add `response_format`/`max_tokens`.

---

## Appendix — Tool Versions

- gitleaks: `/usr/local/bin/gitleaks`
- ruff: `0.16.1`
- bandit: `1.9.4`
- pytest: `7.4.3`
