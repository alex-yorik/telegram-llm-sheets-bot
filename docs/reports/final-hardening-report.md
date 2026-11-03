# Final Hardening Report (Phase 8)

- **Date:** 2026-11-03
- **Branch:** `fix/final-hardening`
- **Pull request:** [#4](https://github.com/alex-yorik/telegram-llm-sheets-bot/pull/4) — OPEN, not merged
- **Base branch:** `main`
- **Author position:** AI-assisted self-review, not an independent third-party audit.
- **Merge policy:** merge into `main` is performed only by the repository owner. No merge was performed in this phase.

## 1. Summary

Phase 8 closes the hardening work tracked as T1–T5, plus the owner-role,
README-consistency, and CI-repair tasks. The branch is ready for owner review.

**Final state on HEAD `9bd7455`:**

- All **8 GitHub Actions checks** are green on the PR head.
- Unit tests: **81 passed, 0 skipped**.
- Unit-test coverage: **99.33%** against an 80% threshold.
- `pip-audit`: **no known vulnerabilities** for runtime and dev dependencies.
- `gitleaks`: **no leaks** over the full 23-commit history; all suppressions are
  documented false positives.
- `ruff check`, `ruff format --check`, and `bandit -ll` pass.
- No secrets and no `.env` content are included in this report or committed.
- No merge, force-push, rebase, or history rewrite was performed.

**Overall status: READY FOR OWNER REVIEW. Merge decision belongs to the owner.**

## 2. Commit SHA

| Item | Value | Status |
|---|---|---|
| Initial commit (tag `final-hardening-prep`, `main` baseline) | `5147caea82eafa8bf41dcb036659093e193c430f` | **VERIFIED** — `git rev-parse final-hardening-prep` |
| Final code commit verified in this report | `9bd7455ec18874b2e947fde9633ebdf5bd9f47ca` | **VERIFIED** — `git rev-parse HEAD` before this report commit; PR `headRefOid` matched at verification time |
| Short SHA | `9bd7455` | **VERIFIED** — `git rev-parse --short HEAD` |
| Branch | `fix/final-hardening` | **VERIFIED** — `git status` |

This report is added in a **docs-only commit** after the verification above.
That commit changes no application code, workflow, dependency, or test; the
verified code state remains `9bd7455`. After the report is pushed, the PR head
moves to the report commit SHA.

Commits between the baseline and the verified code HEAD:

```text
9bd7455 fix(ci): reword gitleaks ignore comment and record its false positive
80a38a5 fix(ci): resolve modularity and secrets-scan gate failures
5d79447 doc: final README consistency check per TZ section 6
b3ec090 doc: describe owner role as Project Owner and AI Development Orchestrator
b5e2f7e doc(T5): verify GitHub Actions runs and branch protection
0412f5f doc(T4): clarify unit-test coverage, add integration smoke test guide
9208c4c fix(T3): remove import-time Settings creation, explicit config loading
0dade43 fix(T2): add pip-audit as blocking CI check for runtime and dev dependencies
76ad925 fix(T1): update SECURITY.md and add logging privacy tests
```

## 3. Changes

All changes are confined to the hardening scope. No unrelated refactoring was
performed.

| Task | Commit | Files (repository-relative) | Change | Status |
|---|---|---|---|---|
| **T1 — log privacy audit** | `76ad925` | [SECURITY.md](../../SECURITY.md), [handlers.py](../../handlers.py), [llm.py](../../llm.py), [sheets.py](../../sheets.py), [main.py](../../main.py), [tests/test_logging_privacy.py](../../tests/test_logging_privacy.py) | Removed `logger.exception` tracebacks from LLM, Sheets, and handler paths; log only exception class/type. Removed `chat_id`, spreadsheet ID, and credentials path from logs. Documented exactly what is and is not logged. Added 8 privacy tests (17 total in the file). | **VERIFIED** |
| **T2 — dependency audit gate** | `0dade43` | [.github/workflows/quality-gates.yml](../../.github/workflows/quality-gates.yml) | Added a blocking `pip-audit` job that audits `requirements.txt` and `requirements-dev.txt` with `pip-audit==2.10.1`. | **VERIFIED** — job green on HEAD |
| **T3 — explicit configuration loading** | `9208c4c` | [config.py](../../config.py), [main.py](../../main.py), [handlers.py](../../handlers.py), [llm.py](../../llm.py), [sheets.py](../../sheets.py), [tests/conftest.py](../../tests/conftest.py), [tests/test_config.py](../../tests/test_config.py), [tests/test_main.py](../../tests/test_main.py), [tests/test_sheets.py](../../tests/test_sheets.py), [tests/test_llm.py](../../tests/test_llm.py) | Replaced import-time `settings = Settings()` with `load_settings()`; settings are loaded explicitly at application startup and passed through `bot_data`/function parameters. `GoogleSheetsClient` now requires explicit credentials, spreadsheet ID, and sheet name. No behavior change to the runtime path. | **VERIFIED** |
| **T4 — coverage clarity and smoke guide** | `0412f5f` | [README.md](../../README.md), [docs/integration-smoke-test.md](../integration-smoke-test.md) | Clarified that the measured number is unit-test coverage with fully mocked external services; documented that coverage does not prove external reachability. Added a 172-line manual smoke-test procedure for real Telegram, LLM, and Google Sheets. | **VERIFIED** — document exists; smoke test itself **NOT VERIFIED** (manual, not executed) |
| **T5 — CI and branch-protection verification** | `b5e2f7e` | [docs/reports/t5-ci-verification.md](t5-ci-verification.md) | Recorded run IDs, jobs, required-check ruleset, and gaps for `main` SHA `5147cae`. | **VERIFIED** — read-only API evidence; empirical merge block **NOT VERIFIED** |
| **Owner role statement** | `b3ec090` | [README.md](../../README.md) | Rewrote "Development approach" to describe the owner as project lead and AI development orchestrator, with responsibility for requirements, architecture, acceptance criteria, review, and final acceptance. | **VERIFIED** |
| **README consistency check** | `5d79447` | [README.md](../../README.md), [SECURITY.md](../../SECURITY.md), [TECH_DEBT.md](../../TECH_DEBT.md), [docs/reports/readme-consistency-check.md](readme-consistency-check.md) | Nine-item TZ-section-6 checklist; fixed deduplication wording, logging claims, dependency-install command, CI job list, and project tree. | **VERIFIED** — external URLs and screenshots remain **NOT VERIFIED** |
| **CI repair — modularity** | `80a38a5` | [llm.py](../../llm.py) | Extracted `_parse_lead_response` so `extract_lead` is within the 50-line limit (52 → 41) without behavior change. | **VERIFIED** — `modularity` job green |
| **CI repair — secrets scan** | `80a38a5`, `9bd7455` | [.gitleaksignore](../../.gitleaksignore) | Added documented fingerprints for confirmed `generic-api-key` false positives in tests and in the ignore-file comment itself. No secret is involved. | **VERIFIED** — `secrets-scan` job green |

## 4. Owner Contribution Statement

The owner is the **Project Owner and AI Development Orchestrator**.

Per the project documentation, the owner:

- defined the requirements, system constraints, architecture-level decisions,
  task breakdown, and acceptance criteria;
- coordinated the AI coding agents and directed implementation, analysis, and
  testing;
- reviewed the agents' output and directed testing, security checks, and quality
  improvements;
- remained responsible for technical decisions, validation, and final acceptance
  of the delivered work.

AI agents assisted with code implementation, analysis, and testing under human
direction. AI-assisted reviews are part of the development process and are
**not** independent third-party audits. This matches `README.md`
("Development approach"), commit `b3ec090`, and item 6 of
[readme-consistency-check.md](readme-consistency-check.md).

**Forbidden-formulation grep.** Command:

```bash
grep -rniE \
  "(\b(is|are|was|were)\s+(\*\*)?production[- ]ready)|(production[- ]ready (system|project|bot))|(\b(is|was)\s+(an?\s+)?independent (third-party )?audit)|(является независим)|(полностью (написан|создан) ИИ)|(без участия человека)|(\b(is|was)\s+(fully )?autonomous)|(owner (did not|didn't|was not) (participate|involved|write code))" \
  README.md SECURITY.md TECH_DEBT.md docs/
```

Output: **(empty, exit code 1)** — no positive claim of independent audit,
full autonomy, zero human involvement, or production readiness.

The words `production-ready` and `independent audit` occur only in explicit
negations ("not production-ready", "not an independent third-party audit").
Those are disclaimers, not claims, and are not forbidden formulations.

**Status: VERIFIED.**

## 5. Tooling Inventory

| Tool / artifact | Present | Evidence | Status | Notes |
|---|---|---|---|---|
| **OpenCode** | Yes | `opencode --version` → `1.18.35`; this report was produced in an OpenCode session. | **VERIFIED** | Used as the AI coding environment. |
| **OpenRouter** | Yes | `.env` indicator check returned `env_contains_openrouter=yes`; value not disclosed. `README.md` documents OpenRouter setup (`LLM_API_BASE=https://openrouter.ai/api/v1`). | **VERIFIED** | Used as the OpenAI-compatible LLM gateway. No key or URL value is reproduced here. |
| **DeepSeek V4.1 Flash** | Yes | Development-session model context (`deepseek/deepseek-flash`, described as DeepSeek V4.1 Flash in the task brief). | **VERIFIED (session context)** | No repository file records the model name; this is a session-level fact, not a repo artifact. |
| **mise** | Yes, installed | `mise --version` → `2026.10.25 linux-x64` (binary on `PATH`). | **VERIFIED (installed)** | No `mise.toml` / `.mise.toml` in the repository. Not used to pin this project's toolchain. Project usage: **NOT APPLICABLE**. |
| **AGENTS.md (repository-level)** | No | `ls AGENTS.md` → not found. | **VERIFIED absent** | A global OpenCode `~/.config/opencode/AGENTS.md` exists outside the repository. It is not part of the deliverable and was not committed. |
| **`.opencode/` (repository-level)** | No | `ls -la .opencode` → not found. | **VERIFIED absent** | No project-local OpenCode configuration exists. |
| **Planner / Builder / Reviewer roles** | No | No role configuration files in the repository (`find` for role/planner/builder/reviewer returned nothing). | **NOT APPLICABLE — not configured, unused** | Reason: the work was executed sequentially in a single session; the operating instructions prohibit invoking subagents. The roles were never set up, so they cannot be reported as used. |
| **n8n** | No | No `n8n` references in the repository; no `n8n` process; no `n8n` container in `docker ps`. | **NOT APPLICABLE — not connected** | No automation workflow was used. |

## 6. Tests

Commands and measured results (run locally on HEAD `9bd7455`):

```text
.venv/bin/python -m pytest --cov=. --cov-report=term-missing
81 passed, 0 skipped in 7.83s
Required test coverage of 80.0% reached. Total coverage: 99.33%

.venv/bin/ruff check .                 -> exit 0
.venv/bin/ruff format --check .        -> 15 files left unchanged, exit 0
.venv/bin/bandit -c pyproject.toml -r . -ll -q -> exit 0
```

Tool versions:

| Tool | Version | Status |
|---|---|---|
| Python | 3.12.3 | **VERIFIED** |
| pytest | 9.0.3 | **VERIFIED** |
| pytest-cov | 4.1.0 | **VERIFIED** |
| pytest-asyncio | 1.4.1.post1 | **VERIFIED** |
| coverage | 7.17.0 | **VERIFIED** |
| ruff | 0.1.6 (project pin) | **VERIFIED** |
| bandit | 1.7.6 | **VERIFIED** |
| pip-audit | 2.10.1 | **VERIFIED** |
| gitleaks | 8.30.1 | **VERIFIED** |

Coverage by module:

| Module | Coverage |
|---|---|
| `config.py` | 100% |
| `handlers.py` | 100% |
| `llm.py` | 100% |
| `main.py` | 96% |
| `models.py` | 100% |
| `sheets.py` | 100% |
| **TOTAL** | **99.33%** |

Important scope note: every external dependency is mocked. The suite makes no
real Telegram, LLM, or Google Sheets request. The result proves application
logic and error handling, not external reachability or credential validity.

**Status: VERIFIED** for the unit-test suite, coverage, lint, format, and
bandit. Live integrations are covered separately in section 9.

## 7. Security

### 7.1 Log privacy audit (T1)

- `SECURITY.md` now lists exactly what is logged and what is never logged.
- `handlers.py`, `llm.py`, `sheets.py`, and `main.py` no longer emit full
  tracebacks; they log only the exception class/type.
- `chat_id`, `user_id`, message content, extracted lead fields, spreadsheet ID,
  credentials path, bot token, and API key are not written to logs.
- [`tests/test_logging_privacy.py`](../../tests/test_logging_privacy.py) contains
  **17 tests**, including assertions that secrets, message content, spreadsheet
  IDs, and tracebacks do not appear in `caplog`.

**Status: VERIFIED** — `pytest tests/test_logging_privacy.py` passes as part of
the 81-test suite.

### 7.2 Dependency audit (`pip-audit`)

```text
.venv/bin/pip-audit -r requirements.txt       -> No known vulnerabilities found
.venv/bin/pip-audit -r requirements-dev.txt   -> No known vulnerabilities found
```

The earlier `pytest` advisory `PYSEC-2026-1845` was fixed by upgrading
`pytest` to `9.0.3` with `pytest-asyncio` `1.4.1.post1`. Details:
[pip-audit-report.md](pip-audit-report.md).

**Status: VERIFIED** for the current lock of direct dependencies. Transitive
dependencies are not hash-locked; see section 11.

### 7.3 Secrets scan

```text
gitleaks detect --source=. --redact --log-opts="--all"
23 commits scanned, ~270426 bytes, no leaks found
```

Tracked secret files check:

```text
git ls-files | grep -E '\.env$|credentials/.*\.json'  -> empty
```

`.env` and `credentials/*.json` are ignored (`.gitignore` rules 1 and 17). A
local `credentials/service-account.json` and a local `.env` exist on the host
but are untracked. No value or content is reproduced in this report.

**Status: VERIFIED** — no leaks found.

### 7.4 Documented `.gitleaksignore` fingerprints

All entries are confirmed false positives. No credential value is present.

| Fingerprint | File / line | Justification |
|---|---|---|
| `06ba5bd…:sheets.py:generic-api-key:49` | `sheets.py` | `generic-api-key` matched the `Credentials.from_service_account_file(...)` call, not a key. |
| `c95744f…:tests/test_logging_privacy.py:…:188/203` | test file | Matched `correlation_id=` literals used to assert that correlation IDs are logged while content is not. |
| `b3de7dc…:tests/test_logging_privacy.py:…:186/201` | test file | Same false positive after the PR #2 squash merge shifted line numbers. |
| `76ad925…:tests/test_logging_privacy.py:…:275/330/351` | test file | Test helper call followed by a `correlation_id=` literal; no credential follows. |
| `9208c4c…:tests/test_logging_privacy.py:…:187/330/351` | test file | Same false positive after the T3 changes shifted line numbers. |
| `80a38a5…:.gitleaksignore:generic-api-key:18` | ignore file | The explanatory comment itself contained the rule's trigger text. Reworded in `9bd7455`; the fingerprint remains as a historical record. |

**Status: VERIFIED** — every suppression is explained and contains no secret.

## 8. CI

PR #4 is **OPEN** and reported `mergeable = MERGEABLE`,
`mergeStateStatus = CLEAN`, `headRefOid = 9bd7455ec18874b2e947fde9633ebdf5bd9f47ca`
at verification time, before this docs-only report commit.

### 8.1 CI workflow — run `41630051080`

URL: https://github.com/alex-yorik/telegram-llm-sheets-bot/actions/runs/41630051080

| Job | Conclusion | Started (UTC) | Completed (UTC) |
|---|---|---|---|
| `docker-build` | success | 2026-11-03T11:45:16Z | 2026-11-03T11:45:28Z |
| `lint` | success | 2026-11-03T11:45:16Z | 2026-11-03T11:45:33Z |
| `test (3.12)` | success | 2026-11-03T11:45:16Z | 2026-11-03T11:45:40Z |

### 8.2 Quality Gates workflow — run `41630051157`

URL: https://github.com/alex-yorik/telegram-llm-sheets-bot/actions/runs/41630051157

| Job | Conclusion | Started (UTC) | Completed (UTC) |
|---|---|---|---|
| `bandit` | success | 2026-11-03T11:45:16Z | 2026-11-03T11:45:32Z |
| `pip-audit` | success | 2026-11-03T11:45:16Z | 2026-11-03T11:45:39Z |
| `secrets-scan` | success | 2026-11-03T11:45:16Z | 2026-11-03T11:45:24Z |
| `coverage-gate` | success | 2026-11-03T11:45:16Z | 2026-11-03T11:45:35Z |
| `modularity` | success | 2026-11-03T11:45:16Z | 2026-11-03T11:45:21Z |

Both runs are `event = pull_request`, `status = completed`,
`conclusion = success`, `headSha = 9bd7455ec18874b2e947fde9633ebdf5bd9f47ca`.

**All 8 checks are green on HEAD.** No merge was performed.

Ruleset note from [t5-ci-verification.md](t5-ci-verification.md): the active
ruleset enforces six required checks (`test (3.12)`, `lint`, `docker-build`,
`modularity`, `coverage-gate`, `secrets-scan`). `bandit` and `pip-audit` run and
pass on HEAD, but are **not** in the required-check list. Making them blocking
is an owner action on ruleset `26415946`. See section 10.

**Status: VERIFIED** for CI results on HEAD.

## 9. Integration Testing

### 9.1 What was checked earlier

The earlier publication report records an **owner-reported** successful live run
of an earlier revision: the bot wrote rows to Google Sheets using real Telegram,
LLM, and Google service-account credentials. That run predates the current
hardening revision.

Status: **NOT VERIFIED** as evidence for HEAD. It is owner-reported history, not
a committed log, screenshot, or CI artifact, and it was not reproduced in this
phase.

### 9.2 Current revision

The current HEAD was **not** run against real external services in this phase.
The automated suite mocks Telegram, the LLM client, and Google Sheets, so it does
not exercise real API permissions, sheet layout, quota limits, or latency.

A manual procedure exists in
[docs/integration-smoke-test.md](../integration-smoke-test.md): dedicated test
bot, dedicated LLM key, dedicated test spreadsheet, synthetic data, and secrets
kept outside the repository.

Status: **NOT VERIFIED** — the manual smoke test was **not executed**. It is a
human procedure and is intentionally excluded from public CI to avoid exposing
secrets.

### 9.3 External URLs, screenshots, and live services

| Item | Status | Reason |
|---|---|---|
| Telegram Bot API reachability | **NOT VERIFIED** | No live call on HEAD. |
| LLM provider reachability and model behavior | **NOT VERIFIED** | No live call on HEAD. |
| Google Sheets API, permissions, and rate limits | **NOT VERIFIED** | No live call on HEAD. |
| External documentation URLs (`github.com`, `t.me`, `openrouter.ai`, Google Cloud) | **NOT VERIFIED** | No network fetch was performed. |
| README screenshots reflect current UI/data | **NOT VERIFIED** | Requires human visual review; files exist and are linked. |

## 10. NOT VERIFIED

| Item | Status | Explanation |
|---|---|---|
| External URLs reachable | **NOT VERIFIED** | No network fetch was performed; link existence in the repository was checked, not remote availability. |
| Screenshots reflect current UI/data | **NOT VERIFIED** | Requires human visual comparison; the image files exist and are referenced correctly. |
| Empirical merge blocking | **NOT VERIFIED** | Merging into `main` is owner-only and was intentionally not attempted. Ruleset `26415946` is `enforcement = active`, `bypass_actors = []`, but this is configuration evidence, not an attempted-merge test. |
| Live Telegram / LLM / Google Sheets run on HEAD | **NOT VERIFIED** | The manual smoke test was not executed; see section 9. |
| `bandit` and `pip-audit` block merges | **NOT VERIFIED** | Both pass on HEAD but are absent from the ruleset's required-status-check list. Owner action is required to make them blocking. |
| Transitive dependency pinning | **NOT VERIFIED / OPEN** | Direct dependencies are pinned; transitive dependencies are resolved at install time and are not hash-locked. See section 11. |
| System `ruff` 0.16.1 formatting | **NOT APPLICABLE** | The project pins `ruff==0.1.6` and CI/pre-commit use that version. System ruff drift is documented and not used by the project. |

## 11. Remaining Technical Debt (not hidden)

| # | Debt | Impact | Current mitigation / status |
|---|---|---|---|
| 1 | **In-memory deduplication only** | `deque(maxlen=1000)` of `(chat_id, message_id)`; cleared on restart and evicts old keys under sustained load, so an old duplicate could be processed again. | Documented in `TECH_DEBT.md` #1 and `README.md`. **OPEN / ACKNOWLEDGED.** |
| 2 | **No dependency lock file** | `requirements.txt` pins direct dependencies only; transitive packages are resolved at build time. Reproducibility and supply-chain review are weaker. | `pip-audit` audits both requirement files; no hash-locked lockfile. **OPEN / ACKNOWLEDGED.** |
| 3 | **No healthcheck** | `docker-compose.yml` has no healthcheck; `restart: unless-stopped` only handles process exit, not a hung polling/LLM/Sheets loop. | Deliberate deviation: a process-existence check would give a false "healthy" signal. Documented in `TECH_DEBT.md` #6 and `README.md`. **OPEN / ACKNOWLEDGED.** |
| 4 | **No retry/queue for Sheets writes** | A transient Google API failure loses a lead. | Documented in `TECH_DEBT.md` #7. **OPEN / ACKNOWLEDGED.** |
| 5 | **No per-user rate limiting** | One user can generate unlimited LLM calls and cost. | Documented in `TECH_DEBT.md` #2. **OPEN / ACKNOWLEDGED.** |
| 6 | **No encryption at rest / GDPR-HIPAA tooling** | Google Sheets security depends on Google and deployer access controls; no data-subject tooling. | Documented in `SECURITY.md` and `TECH_DEBT.md` #3/#5. **OPEN / ACKNOWLEDGED.** |
| 7 | **Single worksheet only** | No rotation, archiving, or multi-sheet support. | Documented in `TECH_DEBT.md` #8. **OPEN / ACKNOWLEDGED.** |

None of these items were hidden or marked as fixed. They are accepted for a
Level D demo project and must be addressed before production use.

## Definition of Done — TZ Section 10

| ID | Definition of Done item | Status | Evidence |
|---|---|---|---|
| DoD-1 | T1–T5 implemented as specified | **VERIFIED** | Commits `76ad925`, `0dade43`, `9208c4c`, `0412f5f`, `b5e2f7e`; section 3. |
| DoD-2 | Owner role documented per TZ section 3 | **VERIFIED** | `README.md` "Development approach"; commit `b3ec090`; section 4. |
| DoD-3 | No forbidden owner-role formulations | **VERIFIED** | Forbidden-formulation grep returned empty (exit 1); section 4. |
| DoD-4 | README consistent with implementation | **VERIFIED** | [readme-consistency-check.md](readme-consistency-check.md), 9/9 items; external items explicitly deferred. |
| DoD-5 | Unit tests pass | **VERIFIED** | `81 passed, 0 skipped`; section 6. |
| DoD-6 | Coverage meets threshold | **VERIFIED** | `99.33%` vs `80%`; section 6. |
| DoD-7 | Lint, format, and static security checks pass | **VERIFIED** | `ruff check`, `ruff format --check`, `bandit -ll` all exit 0; section 6. |
| DoD-8 | Dependency audit is clean and blocking in CI | **VERIFIED** (CI job) / **NOT VERIFIED** (merge-blocking) | `pip-audit` green on HEAD; job is not in the required-check list (section 8). |
| DoD-9 | Secrets scan is clean | **VERIFIED** | `gitleaks` 8.30.1: 23 commits, no leaks; section 7.3. |
| DoD-10 | No secrets committed; suppressions documented | **VERIFIED** | `git ls-files` returns no `.env`/credential JSON; all `.gitleaksignore` entries justified; section 7.4. |
| DoD-11 | All CI checks green on final HEAD | **VERIFIED** | Runs `41630051080` and `41630051157`: 8/8 jobs success; section 8. |
| DoD-12 | Report created with explicit statuses | **VERIFIED** | This file. |
| DoD-13 | PR open and unmerged; owner-only merge | **VERIFIED** | PR #4 OPEN, `MERGEABLE`, `CLEAN`; no merge performed. |
| DoD-14 | Live integration smoke test executed | **NOT VERIFIED** | Manual procedure documented but not run; section 9. |
| DoD-15 | External URLs reachable and screenshots current | **NOT VERIFIED** | No network fetch; no human visual review; section 10. |
| DoD-16 | Empirical merge blocking tested | **NOT VERIFIED** | Merge is owner-only; ruleset checked read-only; section 10. |
| DoD-17 | `bandit` and `pip-audit` are required checks | **NOT VERIFIED** | They run and pass, but are not in ruleset `26415946`'s required list; owner action needed. |
| DoD-18 | Dependency lock file exists | **NOT VERIFIED / OPEN** | Direct pins only; no hash-locked lockfile; section 11. |

## Verdict

**Phase 8 deliverables are complete and verified to the extent possible without
live external services and without performing an owner-only merge.**

The branch may be merged by the **owner** after reviewing this report and, if
required by the owner's release policy, running the manual smoke test in
[docs/integration-smoke-test.md](../integration-smoke-test.md).
