# Final Publication Readiness Report

- **Date:** 2026-11-02
- **Branch:** `feat/publication-prep`
- **Baseline tag:** `pre-publication-prep` (`a52ea7f`)
- **HEAD at verification:** `487e0f0`
- **Project level:** D (Demo / Portfolio) per `QUALITY_STANDARD.md` v2.1
- **Author position:** AI-assisted self-review, not an independent third-party audit (`DOC-ROLE-01`, `PRC-00`).

## Audit Summary

Phases 1-6 are complete and this report records the Phase 7 verification run.
The project is a Level D demo. All automated gates that are executable in this
environment were run locally and their raw results are listed below.

| Area | Result |
|---|---|
| Secret scan (full history) | **PASS** - no leaks found |
| Test suite | **PASS** - 55 passed, 0 skipped |
| Coverage | **PASS** - 99.30% (threshold 80%) |
| `ruff check` | **PASS** |
| `ruff format --check` (pinned 0.1.6) | **PASS** |
| `ruff format --check` (system 0.16.1) | **FAIL** - version mismatch, see Code Quality |
| Bandit (`-ll`) | **PASS** - 0 findings |
| Docker build from clean state | **PASS** |
| `docker compose config -q` | **PASS** |
| Required publication files | **PASS** - all present |
| Secrets in `.env` / credentials tracked by Git | **PASS** - none tracked |

**Overall:** the project is ready for public demonstration as a Level D
portfolio project. It is **not** production-ready. Remaining deviations are
listed under Known Limitations and Recommended Next Steps.

## Security Findings

### Secret scan - full Git history

Command:

```bash
gitleaks detect --source=. --verbose --redact --log-opts="--all"
```

Actual result:

```text
10 commits scanned.
scanned ~96923 bytes (96.92 KB) in 823ms
no leaks found
```

- No real secrets were found in the full commit history.
- `.gitleaksignore` contains **one** documented fingerprint (SEC-06): a
  `generic-api-key` false positive on `sheets.py:49` in commit `06ba5bd`
  (`Credentials.from_service_account_file` call). No secret value is involved.
- No history rewrite, rebase, or force-push was performed (PRC-03).

### Tracked `.env` / credentials

Command:

```bash
git ls-files | grep -E "\.env$|credentials/.*\.json"
```

Actual result: **empty** (exit code 1). Only `.env.example` and
`credentials/.gitkeep` are tracked. `.env` and `credentials/*.json` are ignored.

### README secret check

Command:

```bash
grep -E "sk-or-v1-[a-zA-Z0-9]{10,}|1234567890:AA[a-zA-Z0-9]{10,}" README.md
```

Actual result: **empty** (exit code 1). No token-like values in `README.md`.

### Local secrets note

A local, untracked `.env` exists in the working tree with non-placeholder
values. It is gitignored, was never tracked, and no value is reproduced in this
report or anywhere in the repository. If that file was ever shared outside the
host, rotate the Telegram token in BotFather and the LLM API key.

## Bugs Fixed (Phases 1-6)

Security and privacy:

- Removed full user message text from logs (PII leak in `handlers.py`).
- Removed full spreadsheet row from logs (PII leak in `sheets.py`).
- Reduced LLM logging to metadata; stopped logging raw prompt text, SDK
  response objects, and raw model output.
- Redacted bot token from logs.
- Confirmed `.env` and Google service-account JSON are untracked and excluded
  from the Docker build context.
- Added a privacy notice to `/start`.

Validation and correctness:

- Rejects empty LLM extractions via `Lead.has_data()`; whitespace-only fields
  are no longer treated as data.
- Added a 2000-character input limit before any LLM or Sheets call.
- Deduplication by `(chat_id, message_id)` so a message is not written twice.
- Multi-line / fenced JSON from the LLM is normalized before validation.
- Non-text messages receive an explicit explanation.
- Startup fails on missing required configuration (pydantic-settings).
- Google Sheets writes use `value_input_option="RAW"` to block formula
  injection.
- Reduced duplicate `sheets_client` state to a single lookup path via
  `bot_data`.
- Added graceful shutdown on `SIGINT` / `SIGTERM`.

Quality and delivery:

- Added 6 test files / 55 test functions with mocked external services.
- Added `pyproject.toml` (pytest, coverage, ruff, bandit).
- Added `.pre-commit-config.yaml`.
- Added two CI workflows: `ci.yml` (test, lint, docker-build) and
  `quality-gates.yml` (secrets-scan, bandit, coverage-gate, modularity).
- Made the container run as a non-root user (`uid 1000`).
- Removed the unused `[job-queue]` extra and other unused dependencies.
- Made `SECURITY.md`, `TECH_DEBT.md`, `LICENSE` (All rights reserved), and a
  rewritten `README.md` with the required AI-authorship disclosure.

## Files Changed

Diff from the rollback tag to HEAD: **28 files, +1798 / -181**.

- Code: `config.py`, `handlers.py`, `llm.py`, `main.py`, `models.py`,
  `sheets.py`.
- Delivery: `Dockerfile`, `docker-compose.yml`, `requirements.txt`,
  `.dockerignore`, `.gitignore`.
- Quality: `pyproject.toml`, `.pre-commit-config.yaml`,
  `.github/workflows/ci.yml`, `.github/workflows/quality-gates.yml`,
  `.gitleaksignore`.
- Tests: `tests/__init__.py`, `tests/conftest.py`, `tests/test_config.py`,
  `tests/test_handlers.py`, `tests/test_llm.py`, `tests/test_main.py`,
  `tests/test_models.py`, `tests/test_sheets.py`.
- Docs: `README.md`, `SECURITY.md`, `TECH_DEBT.md`, `LICENSE`,
  `docs/reports/phase5-report.md`, and this report.

Note: `docs/reports/audit-phase1.md` remains **untracked**. It is the Phase 1
read-only audit and was intentionally left out of the Phase 5/6 commits.

## Tests

Command:

```bash
pytest --cov=. --cov-report=term-missing
```

Actual result:

```text
collected 55 items
55 passed in 28.62s
Required test coverage of 80.0% reached. Total coverage: 99.30%
```

Coverage by module:

| Module | Stmts | Miss | Branch | BrPart | Cover |
|---|---:|---:|---:|---:|---:|
| `config.py` | 13 | 0 | 0 | 0 | 100% |
| `handlers.py` | 88 | 0 | 24 | 0 | 100% |
| `llm.py` | 37 | 0 | 2 | 0 | 100% |
| `main.py` | 48 | 1 | 4 | 1 | 96% |
| `models.py` | 10 | 0 | 0 | 0 | 100% |
| `sheets.py` | 54 | 0 | 4 | 0 | 100% |
| **TOTAL** | **250** | **1** | **34** | **1** | **99%** |

Scope and counting method: 6 test files, 55 test functions, 55 passed,
0 skipped. Tests use mocks and do not require network, Telegram, LLM, or Google
credentials (TST-06). The only uncovered line is a defensive branch in
`main.py`.

## Code Quality

### Ruff check

```bash
ruff check .
# All checks passed! (exit 0)
```

### Ruff format - toolchain discrepancy

Default `PATH` uses **system ruff 0.16.1**, while the project pins
`ruff==0.1.6` in `requirements.txt`, CI, and `.pre-commit-config.yaml`.

```bash
ruff format --check .          # system ruff 0.16.1
# 3 files would be reformatted: handlers.py, main.py, sheets.py (exit 1)

.venv/bin/ruff format --check .   # pinned ruff 0.1.6
# 14 files left unchanged (exit 0)
```

The difference is only cosmetic implicit-string-concatenation joining
introduced by the newer formatter. The project-pinned toolchain used by CI and
pre-commit is green. This is recorded as an environment/reproducibility caveat,
not as a hidden pass.

### Bandit

```bash
bandit -c pyproject.toml -r . -ll -q
# exit 0, no findings at Medium or High severity
```

System Bandit 1.9.4 and pinned Bandit 1.7.6 both return exit 0. There are no
`# nosec` suppressions.

## Docker

Commands and actual results:

```bash
docker compose down          # exit 0
docker compose build         # exit 0, image built successfully
docker compose config -q     # exit 0, config valid
```

Environment: Docker 29.1.3, Docker Compose v2.29.7.

- Build succeeded from a clean compose state.
- Container runs as non-root `appuser` (`uid 1000`).
- `credentials/` is mounted read-only.
- No ports are published.
- The obsolete `version:` key is absent.
- **No `healthcheck` is defined** in `Dockerfile` or `docker-compose.yml`.
  This is documented as a known limitation (TECH_DEBT.md #6) and is a
  deviation from `DCK-01` / `OBS-02`.

## README / Demo

- `README.md` states the project is Level D (Demo / Portfolio), not production.
- AI-assisted authorship is disclosed in "How this project was built".
- Quick start covers Telegram bot creation, LLM key, Google service account,
  environment variables, credentials placement, and Docker start.
- All example data is explicitly fictional.
- Privacy note explains that message content is sent to a third-party LLM and
  extracted data is stored in Google Sheets.
- Architecture, environment variables, error handling, test results, security
  notes, limitations, and project structure are documented.
- `SECURITY.md` documents the vulnerability-reporting policy.
- `TECH_DEBT.md` documents 8 known limitations with severity and rationale.

## Known Limitations

1. **No Docker healthcheck** (`DCK-01`, `OBS-02`). A real liveness probe would
   need an application-level endpoint; a process-exists check was removed as a
   misleading signal. Documented in `TECH_DEBT.md`.
2. **Dependencies are not split per `DEP-01`.** `requirements.txt` still mixes
   runtime and development tools; there is no `requirements-prod.txt` /
   `requirements-dev.txt`. Phase 5 flagged this for Phase 6, but Phase 6 was
   documentation-only, so the split was not completed.
3. **Ruff formatter version drift.** The repository pins `0.1.6`; a newer
   system-installed ruff reformats three files. CI is green because it pins
   `0.1.6`, but a contributor using the latest ruff will see a diff.
4. **In-memory deduplication.** The `(chat_id, message_id)` set is lost on
   restart.
5. **No per-user rate limiting.** A single user can generate unlimited LLM
   calls and cost.
6. **No retry/queue for Google Sheets writes.** Transient failures can lose a
   lead.
7. **In-memory dedup set is bounded by clearing.** When it exceeds 1000 entries
   the whole set is cleared, which temporarily permits duplicates.
8. **No GDPR/HIPAA tooling**, no consent flow, no data export/deletion, and no
   encryption at rest beyond Google's controls.
9. **Local untracked `.env` holds live-looking values.** Not in Git, but rotate
   if it was ever shared.
10. **`docs/reports/audit-phase1.md` is untracked.** It is not part of the
    published tree.
11. **Base image is not pinned by digest** and there is no lockfile/hashes for
    dependencies (supply-chain reproducibility).
12. **`data/` bind mount is unused by the code**; on a clean clone Docker may
    create it as root. It does not break the bot because the code never writes
    there, but the mount is unnecessary.

## Publication Readiness

**Status: CONDITIONAL GO for public demo (Level D).**

- Security gate: **PASS** - no secrets in history or tracked files.
- Tests and coverage: **PASS**.
- Lint/Bandit: **PASS** under the pinned toolchain.
- Docker build: **PASS**.
- Documentation: **PASS** for a Level D publication.

The project can be published as a portfolio demo. It must not be presented as
production-ready. The three standards deviations are: missing healthcheck,
combined requirements file, and ruff formatter version drift. None of them
exposes data or blocks a private/public demo, but they should be fixed before
any claim of full `QUALITY_STANDARD.md` v2.1 compliance.

## Recommended Next Steps

1. Split `requirements.txt` into `requirements-prod.txt` and
   `requirements-dev.txt` per `DEP-01`, update CI and README commands.
2. Either reformat the three files with ruff 0.1.6-compatible output or bump the
   pinned ruff version in `requirements.txt`, CI, and pre-commit together.
3. Decide on a real `/health` probe and add `HEALTHCHECK` plus a compose
   `healthcheck` if the project moves beyond Level D.
4. Remove the unused `./data:/app/data` mount or document why it exists.
5. Commit or delete `docs/reports/audit-phase1.md`; do not leave historical
   reports untracked indefinitely.
6. Rotate Telegram/LLM credentials if the local `.env` was ever shared.
7. Add a lockfile with hashes and pin the base image by digest if reproducible
   builds become a requirement.
8. Verify the GitHub Actions workflows after pushing (they have not run in
   GitHub yet in this environment) and confirm `gitleaks-action` works without
   an organization license.

## Verification Matrix

### VERIFIED

- `gitleaks detect --source=. --verbose --redact --log-opts="--all"` -> no leaks.
- `git ls-files | grep -E "\.env$|credentials/.*\.json"` -> empty.
- README secret `grep` -> empty.
- `pytest --cov=. --cov-report=term-missing` -> 55 passed, 99.30%.
- `ruff check .` -> pass (system and pinned).
- `ruff format --check .` with pinned ruff 0.1.6 -> pass.
- `bandit -c pyproject.toml -r . -ll -q` -> pass, 0 Medium/High.
- `docker compose down` -> exit 0.
- `docker compose build` -> exit 0.
- `docker compose config -q` -> exit 0.
- Required files exist: `README.md`, `SECURITY.md`, `TECH_DEBT.md`, `LICENSE`,
  `pyproject.toml`, `.pre-commit-config.yaml`.
- `git log --oneline -10` inspected; working tree clean apart from the untracked
  Phase 1 audit and this new report.

### NOT VERIFIED

- `ruff format --check .` with **system ruff 0.16.1** -> fails on 3 files
  (cosmetic; pinned 0.1.6 passes).
- GitHub Actions execution on GitHub -> not run here; only local command
  equivalents and YAML inspection.
- `gitleaks-action` in GitHub (vs local gitleaks 8.30.1) -> not run here; may
  require `GITLEAKS_LICENSE` for organizations.
- Live end-to-end bot run (`docker compose up` with real Telegram, LLM, and
  Google credentials) -> intentionally not performed; it would start a second
  polling instance and requires live credentials.
- Production behavior, load, and Google Sheets rate limits -> out of scope for
  Level D.
