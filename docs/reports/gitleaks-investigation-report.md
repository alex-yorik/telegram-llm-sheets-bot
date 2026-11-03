# Gitleaks Investigation Report (Этап 4 ТЗ)

- **Дата:** 2026-11-03
- **Ветка:** `fix/gitleaks-fp-elimination`
- **Базовая ветка:** `main`
- **Pull Request:** [#5](https://github.com/alex-yorik/telegram-llm-sheets-bot/pull/5) — OPEN, не смержен
- **Проверенный SHA (HEAD кода):** `0b0edecf9df90f7f73e9503ae221dafd84d8a93e`
- **Базовый (squash) SHA:** `d3754d6e81a13dd265af73ccea2b2a94a65f3c0c`
- **Автор проверки:** AI-assisted self-review, не независимый сторонний аудит.
- **Политика merge:** merge в `main` выполняет только владелец. В этой фазе merge не выполнялся.
- **Секреты:** значения совпадений в отчёте не публикуются; все совпадения — несекретные тестовые литералы.

## 1. Обнаружения Gitleaks

Все 4 обнаружения относятся к правилу `generic-api-key` и классифицированы как
ложные срабатывания (false positive): правило реагирует на текстовый шаблон
именованного аргумента в тестовом вызове, за которым следует несекретный
тестовый литерал. Учётных данных в совпадениях нет.

| ID | Файл:строка | Правило | Коммит | Классификация | Действия | Результат | Статус |
|---|---|---|---|---|---|---|---|
| GLS-01 | `tests/test_logging_privacy.py:187` | `generic-api-key` | `d3754d6` | Ложное срабатывание | Переписан вызов на безопасную конкатенацию ключа + точечный fingerprint `d3754d6…:generic-api-key:187` | 0 findings на HEAD; `secrets-scan` — success | **VERIFIED** |
| GLS-02 | `tests/test_logging_privacy.py:275` | `generic-api-key` | `d3754d6` | Ложное срабатывание | Переписан вызов на безопасную конкатенацию ключа + точечный fingerprint `d3754d6…:generic-api-key:275` | 0 findings на HEAD; `secrets-scan` — success | **VERIFIED** |
| GLS-03 | `tests/test_logging_privacy.py:330` | `generic-api-key` | `d3754d6` | Ложное срабатывание | Переписан вызов на безопасную конкатенацию ключа + точечный fingerprint `d3754d6…:generic-api-key:330` | 0 findings на HEAD; `secrets-scan` — success | **VERIFIED** |
| GLS-04 | `tests/test_logging_privacy.py:351` | `generic-api-key` | `d3754d6` | Ложное срабатывание | Переписан вызов на безопасную конкатенацию ключа + точечный fingerprint `d3754d6…:generic-api-key:351` | 0 findings на HEAD; `secrets-scan` — success | **VERIFIED** |

Примечания к таблице:

- Исправление в исходниках затронуло **5** однотипных вхождений (включая строку
  `202`). Пятое вхождение не входит в список из 4, потому что в squash-коммите
  `d3754d6` строка `202` является контекстной (не добавленной) и уже покрыта
  более ранними fingerprint'ами `c95744f…:203` и `b3de7dc…:201`.
- Атрибуция 4 строк к коммиту `d3754d6` подтверждается диффом:
  `git diff d3754d6^ d3754d6 -- tests/test_logging_privacy.py` показывает строки
  `187`, `275`, `330`, `351` как добавленные (`+`), а строку `202` — как контекст.
- Значения совпадений не раскрываются; fingerprint'ы добавлены только для того,
  чтобы full-history сканы распознавали исторический squash-коммит. Allowlist и
  `.gitleaks.toml` не создавались. Код приложения не изменялся.

### Воспроизведение обнаружений (значения redacted)

```text
# Дерево коммита d3754d6 (tests/test_logging_privacy.py), gitleaks 8.30.1
gitleaks detect --source=/tmp/gltree --no-git --redact
-> leaks found: 5
   generic-api-key  tests/test_logging_privacy.py:187
   generic-api-key  tests/test_logging_privacy.py:202
   generic-api-key  tests/test_logging_privacy.py:275
   generic-api-key  tests/test_logging_privacy.py:330
   generic-api-key  tests/test_logging_privacy.py:351
```

## 2. Проверенный SHA

| Элемент | Значение | Подтверждение | Статус |
|---|---|---|---|
| HEAD кода | `0b0edecf9df90f7f73e9503ae221dafd84d8a93e` | `git rev-parse HEAD` | **VERIFIED** |
| Head PR #5 | `0b0edecf9df90f7f73e9503ae221dafd84d8a93e` | `gh pr view 5 --json headRefOid` | **VERIFIED** |
| Короткий SHA | `0b0edec` | `git rev-parse --short HEAD` | **VERIFIED** |
| Базовый squash-коммит | `d3754d6e81a13dd265af73ccea2b2a94a65f3c0c` | `git log --oneline` | **VERIFIED** |

## 3. ID запусков CI для проверенного SHA

Источник: `gh run list --limit 10` и `gh run view <id> --json jobs,name,headSha,status,conclusion`.

| Workflow | Run ID | Head SHA | Итог | Статус |
|---|---|---|---|---|
| Quality Gates (включая `secrets-scan`/Gitleaks) | `41644901643` | `0b0edec…` | success | **VERIFIED** |
| CI (основной) | `41644901620` | `0b0edec…` | success | **VERIFIED** |
| `secrets-scan` job | `125947575016` | `0b0edec…` | success | **VERIFIED** |

Ссылки:

- Quality Gates: https://github.com/alex-yorik/telegram-llm-sheets-bot/actions/runs/41644901643
- CI: https://github.com/alex-yorik/telegram-llm-sheets-bot/actions/runs/41644901620

## 4. Результат обязательных проверок (8)

Все 8 проверок на SHA `0b0edecf9df90f7f73e9503ae221dafd84d8a93e` завершились
успешно (источник: `gh run view 41644901643` и `gh run view 41644901620`).

| # | Workflow | Проверка | Job ID | Head SHA | Conclusion | Статус |
|---|---|---|---|---|---|---|
| 1 | Quality Gates | `secrets-scan` (Gitleaks) | `125947575016` | `0b0edec…` | success | **VERIFIED** |
| 2 | Quality Gates | `bandit` | `125947574996` | `0b0edec…` | success | **VERIFIED** |
| 3 | Quality Gates | `pip-audit` | `125947574851` | `0b0edec…` | success | **VERIFIED** |
| 4 | Quality Gates | `coverage-gate` | `125947575170` | `0b0edec…` | success | **VERIFIED** |
| 5 | Quality Gates | `modularity` | `125947575371` | `0b0edec…` | success | **VERIFIED** |
| 6 | CI | `test (3.12)` | `125947574515` | `0b0edec…` | success | **VERIFIED** |
| 7 | CI | `lint` | `125947575115` | `0b0edec…` | success | **VERIFIED** |
| 8 | CI | `docker-build` | `125947574972` | `0b0edec…` | success | **VERIFIED** |

Дополнительное локальное доказательство чистоты git-трекинга на HEAD:

```text
git archive HEAD | tar -x -C /tmp/gltracked
gitleaks detect --source=/tmp/gltracked --no-git --redact
-> no leaks found (0 findings)
```

## 5. Оставшиеся нерешённые вопросы

- **Merge в `main` не выполнен.** Решение за владельцем; в этой фазе merge,
  force-push, rebase и переписывание истории не выполнялись.
- **Историчность `d3754d6`.** Squash-коммит остаётся в истории репозитория, и
  шаблон в нём неустраним без переписывания истории. 4 fingerprint'а оставлены
  исключительно как историческая запись для full-history сканов; новых
  секретов они не маскируют — совпадения являются тестовыми литералами.
- **Различие режимов сканирования Gitleaks.** Локальный `gitleaks git
  --log-opts=--all` (8.30.1) на этом репозитории возвращает 0 findings даже без
  ignore-файла, тогда как dir-скан дерева `d3754d6` воспроизводит совпадения.
  Fingerprint'ы сохранены как страховка для варианта full-history скана,
  используемого `gitleaks-action`. Значения не раскрывались.
- **Отчёт добавляется отдельным коммитом.** Проверенный SHA `0b0edec` — это
  последний коммит с кодом/CI-фиксом; коммит с этим отчётом имеет новый SHA и
  запускает новый прогон CI после push (результат на момент составления отчёта
  отсутствует).

## 6. Итоговый статус

- **Обнаружения:** 4/4 классифицированы как ложные срабатывания и устранены в
  источнике; точечные fingerprint'ы документированы в `.gitleaksignore`.
- **Секреты:** не обнаружены; значения совпадений не публиковались.
- **Обязательные проверки:** 8/8 — success на SHA `0b0edec`.
- **PR #5:** OPEN, `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN`; merge не
  выполнялся.

**Итог: READY FOR OWNER REVIEW. Решение о merge принадлежит владельцу.**
