# T5 — Verification of GitHub Actions and Required Checks

Date: 2026-11-03
Repository: `alex-yorik/telegram-llm-sheets-bot`
Verified branch: `main`
Working branch: `fix/final-hardening`
Tool: `gh` CLI (authenticated as `alex-yorik`, scopes: `gist`, `read:org`, `repo`)

## 1. Target commit

| Item | Value |
| --- | --- |
| Latest `main` SHA | `5147caea82eafa8bf41dcb036659093e193c430f` |
| Commit subject | `fix: fix Quality Gates failure on main after merge (#3)` |
| Timestamp | 2026-11-03T05:38:26Z |

Verified via `git fetch origin main` + `git rev-parse origin/main`, and confirmed by the `headSha` field of both workflow runs below.

## 2. Workflow runs for this SHA

Command: `gh run list --commit 5147caea82eafa8bf41dcb036659093e193c430f`

| Workflow | Run ID | Event | Conclusion | Duration | URL |
| --- | --- | --- | --- | --- | --- |
| CI | `41585082388` | push | success | 24s | https://github.com/alex-yorik/telegram-llm-sheets-bot/actions/runs/41585082388 |
| Quality Gates | `41585082444` | push | success | 29s | https://github.com/alex-yorik/telegram-llm-sheets-bot/actions/runs/41585082444 |

Both runs report `headSha = 5147caea82eafa8bf41dcb036659093e193c430f`.

### CI (41585082388) — jobs and steps

Command: `gh run view 41585082388 --json jobs`

| Job | Conclusion | Key steps |
| --- | --- | --- |
| `lint` | success | Run Ruff — success; Run Bandit — success |
| `docker-build` | success | Build Docker image — success |
| `test (3.12)` | success | Install dependencies — success; Run tests with coverage — success; Upload coverage report — success |

All steps in all three jobs concluded `success`.

### Quality Gates (41585082444) — jobs and steps

Command: `gh run view 41585082444 --json jobs`

| Job | Conclusion | Key steps |
| --- | --- | --- |
| `bandit` | success | Run Bandit — success |
| `secrets-scan` | success | Run Gitleaks — success |
| `modularity` | success | Check file and function lengths — success |
| `coverage-gate` | success | Check coverage threshold — success |

At this SHA the `quality-gates.yml` workflow contained 4 jobs. The `pip-audit` job is **not** present on `main`: it was added later on `fix/final-hardening` (commit `0dade43`, "fix(T2): add pip-audit as blocking CI check..."). Diff of `.github/workflows/quality-gates.yml` between `origin/main` and the working branch confirms this. Therefore `pip-audit` has no run on the verified SHA.

## 3. Branch protection / Rulesets for `main`

Command: `gh api repos/alex-yorik/telegram-llm-sheets-bot/branches/main/protection`

Result: HTTP 404 `{"message":"Branch not protected"}`.

This does **not** mean `main` is unprotected. Classic branch protection is not in use; protection is implemented through an active Repository Ruleset. That is why the classic-protection endpoint returns 404.

Command: `gh api repos/alex-yorik/telegram-llm-sheets-bot/rulesets`
Command: `gh api repos/alex-yorik/telegram-llm-sheets-bot/rulesets/26415946`

| Ruleset field | Value |
| --- | --- |
| id | `26415946` |
| name | `Main` |
| target | `branch` |
| source_type | `Repository` |
| enforcement | `active` |
| conditions.ref_name.include | `["~DEFAULT_BRANCH"]` |
| conditions.ref_name.exclude | `[]` |
| bypass_actors | `[]` |
| current_user_can_bypass | `never` |
| created_at | 2026-11-03T02:03:38Z |
| updated_at | 2026-11-03T02:03:38Z |

### Rules in the ruleset

| Rule type | Parameters |
| --- | --- |
| `deletion` | block branch deletion |
| `non_fast_forward` | block force-push / history rewrite |
| `pull_request` | required_approving_review_count = 0; dismiss_stale_reviews_on_push = false; required_reviewers = []; require_code_owner_review = false; require_last_push_approval = false; required_review_thread_resolution = false; require_extra_approval_for_unattributed_changes = true; allowed_merge_methods = [merge, squash, rebase] |
| `required_status_checks` | strict_required_status_checks_policy = false; do_not_enforce_on_create = false |

### Required status checks (enforced)

All contexts have `integration_id = 15368` (GitHub Actions):

| Required context | Present and green on `main` SHA `5147cae` |
| --- | --- |
| `test (3.12)` | YES — CI job success |
| `lint` | YES — CI job success |
| `docker-build` | YES — CI job success |
| `modularity` | YES — Quality Gates job success |
| `coverage-gate` | YES — Quality Gates job success |
| `secrets-scan` | YES — Quality Gates job success |

All six enforced contexts were produced and concluded `success` on the verified SHA. The merge gate for these checks is configured and active.

### Gaps found

1. `bandit` runs in both workflows but is **not** in the ruleset's required status check list. A `bandit` failure would fail the workflow run but would not by itself block a merge.
2. `pip-audit` is added to `quality-gates.yml` on `fix/final-hardening` but is **not** a required check, and does not exist on `main` yet. After this branch merges, the job will run, but merges will not be blocked by it unless the ruleset is updated.
3. `required_approving_review_count = 0` — no human approval is technically required; the owner merges manually by policy.
4. `require_extra_approval_for_unattributed_changes = true` is set; it does not add a required review count.

Items 1–2 require an owner action on ruleset `26415946` if the intent is for `bandit` and `pip-audit` to be blocking. Exact settings to change in GitHub UI (Settings → Rules → Rulesets → `Main` → Require status checks to pass): add contexts `bandit` and `pip-audit`.

Note: the ruleset rules and required checks were verified read-only through the API. Actual enforcement was not empirically tested by attempting a merge, because merging into `main` is performed only by the owner. Configuration-level enforcement is confirmed: `enforcement = active`, `bypass_actors = []`.

## 4. Permissions in workflow files

Command: `grep -n "permissions:" -A3 .github/workflows/*.yml`

### `ci.yml`

```yaml
permissions:
  contents: read
```

- Top-level only; all jobs inherit `contents: read`.
- No `write` permissions anywhere.

### `quality-gates.yml`

```yaml
permissions:
  contents: read
```

Job-level override in `secrets-scan`:

```yaml
    permissions:
      contents: read
      pull-requests: read
```

- No `write` permissions anywhere.
- `pull-requests: read` is required by `gitleaks/gitleaks-action@v2` and is scoped to that single job only.
- `GITHUB_TOKEN` is passed to Gitleaks via `env`, with no elevated scope.

Result: minimum-permission principle is satisfied in both workflow files.

### Additional observation (not a requirement violation)

All actions are referenced by major-version tags, not by commit SHA:

- `actions/checkout@v4`
- `actions/setup-python@v5`
- `actions/upload-artifact@v4`
- `gitleaks/gitleaks-action@v2`

Pin-by-SHA would harden the supply chain against tag retargeting. Recorded as a recommendation; not changed in this task because allowed file scope is documentation plus verification only.

## 5. Working branch `fix/final-hardening`

Command: `gh run list --branch fix/final-hardening --limit 10`

Result: no workflow runs.

Reason (fact, not a failure): `ci.yml` triggers on `push` only for `main` and `feat/**`; `quality-gates.yml` triggers on `push` only for `main`. A push to `fix/final-hardening` does not match either filter. Both workflows do trigger on `pull_request` targeting `main`, so runs will appear when the owner opens the PR. No run exists at T5 because the branch has not been opened as a PR.

## 6. Summary

| Check | Status |
| --- | --- |
| Latest `main` SHA obtained | OK |
| Both expected workflows ran for that SHA | OK |
| All jobs and steps green on that SHA | OK |
| Protection mechanism exists for `main` | OK — active Ruleset `26415946` (classic API returns 404 by design) |
| Required checks include `test (3.12)`, `lint`, `docker-build`, `modularity`, `coverage-gate`, `secrets-scan` | OK |
| The six required checks are green on the verified SHA | OK |
| `bandit` blocking | NOT VERIFIED as blocking — runs but not required |
| `pip-audit` blocking | NOT VERIFIED as blocking — absent from `main`, not required in ruleset |
| Minimal `permissions` in `ci.yml` | OK — `contents: read` |
| Minimal `permissions` in `quality-gates.yml` | OK — `contents: read`, plus job-scoped `pull-requests: read` |
| Actual merge block empirically tested | NOT VERIFIED — merge into `main` is owner-only and was intentionally not attempted |

No claim of green CI on `main` is based on local `pytest`; every status above comes from GitHub Actions run data for SHA `5147cae`.

## 7. Owner actions (if blocking `bandit` and `pip-audit` is required)

In GitHub: Settings → Rules → Rulesets → `Main` → edit → "Require status checks to pass" → add:

- `bandit`
- `pip-audit`

No other settings changes are required for the six currently enforced checks.
