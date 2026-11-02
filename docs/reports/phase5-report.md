# Отчет: Phase 5 — тесты, CI/CD и инструменты качества

> Журнал ИИ-assisted инженерных правок. Это не независимый аудит.

## Baseline

| Измерение | Значение | Команда |
|-----------|----------|---------|
| Ветка | `feat/publication-prep` | `git branch --show-current` |
| Коммит до правок | `f2e182a` | `git log --oneline -1` |
| Откатный тег | `pre-publication-prep` | `git tag -l` |
| Тесты | отсутствовали | `find tests -type f` |
| CI | отсутствовал | `find .github -type f` |
| Конфигурация линтеров | отсутствовала | `test -f pyproject.toml` |

## Задачи

| Задача | Статус | Команда | Результат |
|--------|--------|---------|-----------|
| T1: `pyproject.toml` (pytest, coverage, ruff, bandit) | DONE | `pytest`, `ruff`, `bandit` | конфигурация применяется |
| T2: dev-инструменты в `requirements.txt` | DONE | `pip install -r requirements.txt` | установка в `.venv` успешна |
| T3: `.pre-commit-config.yaml` | DONE | статическая проверка YAML | файл валиден |
| T4: тесты с полным мокированием | DONE | `pytest --cov=.` | 55 passed |
| T5: CI workflows (`ci.yml`, `quality-gates.yml`) | DONE | YAML parse + локальные команды | 7 jobs, все проверки блокирующие |
| T6: гигиена репозитория | DONE | `git status`, gitleaks | секретов нет |
| T7: Docker-сборка | DONE | `docker build` | образ собран |

## Сырой вывод ключевых измерений

### pytest + coverage

```text
55 passed in 6.64s

Name          Stmts   Miss Branch BrPart  Cover   Missing
---------------------------------------------------------
config.py        13      0      0      0   100%
handlers.py      88      0     24      0   100%
llm.py           37      0      2      0   100%
main.py          48      1      4      1    96%   93
models.py        10      0      0      0   100%
sheets.py        54      0      4      0   100%
---------------------------------------------------------
TOTAL           250      1     34      1    99%

Required test coverage of 80% reached. Total coverage: 99.30%
```

Охват: 6 test-файлов, 55 test-функций, 55 passed, 0 skipped; покрытие 99.30% по модулям `config.py`, `handlers.py`, `llm.py`, `main.py`, `models.py`, `sheets.py`.

### Ruff

```text
ruff check .              -> OK (0 errors)
ruff format --check .     -> 14 files left unchanged
```

### Bandit

```text
bandit -c pyproject.toml -r . -ll -q -> exit 0
```

### Gitleaks (полная история)

```text
5 commits scanned
no leaks found
```

### Modularity

```text
Modularity check passed
```

### Docker

```text
docker compose config -q  -> OK
docker build -t telegram-llm-sheets-bot:ci . -> Successfully built
```

## Подавления проверок

| Файл | Подавление | Причина |
|------|------------|---------|
| `main.py` | `# type: ignore[arg-type]` | `signal.signal` принимает `signal.Signals` в runtime, stub ожидает `int`; добавлен комментарий-причина |
| `.gitleaksignore` | 1 fingerprint | ложное срабатывание `generic-api-key` в коммите `06ba5bd` на вызове `Credentials.from_service_account_file`; секрета нет (SEC-06) |

Других `# noqa`, `# nosec`, `# type: ignore` в проекте нет.

## Измененные существующие тесты

Существующих тестов не было. Все тесты созданы в Phase 5.

## Отклонения от ТЗ

1. **Пустой `choices` от LLM** — в примере теста ожидался `LLMRequestError`; фактический и семантически корректный путь возвращает `LLMValidationError` (нет контента для валидации). Тест адаптирован, production-код не менялся.
2. **Интерфейс `GoogleSheetsClient`** — пример тестов обращался к `client.worksheet` и `client.spreadsheet_id`, которых в классе нет. Тесты написаны под реальный интерфейс `_get_worksheet()` и `_spreadsheet_id`; production-интерфейс не расширялся ради тестов.
3. **`requirements.txt` содержит dev-инструменты** — прямое требование ТЗ. Это отличается от `DEP-01` (отдельные `requirements-prod.txt` / `requirements-dev.txt`); разделение вынесено в Phase 6.
4. **CI: `docker build` вместо `docker compose up`** — запуск бота требует реальных Telegram/LLM/Sheets-секретов (`CI-03` запрещает передавать их в тесты), а контейнер с фиктивным токеном не является рабочей проверкой. Блокирующая сборка образа сохранена.
5. **`coverage-gate` сделан самодостаточным** — исходный пример использовал `needs: test` между разными workflow, что не поддерживается GitHub Actions. Гейт запускает `pytest --cov-fail-under=80` в своем job.
6. **`.gitleaksignore` вне списка Allowed files** — создан по требованию `SEC-06` для единственного документированного ложного срабатывания; без него блокирующий скан истории невозможен.
7. **Ruff format** применен к разрешенным source-файлам, чтобы `ruff format --check .` был зеленым. Логика не менялась.
8. **`models.Lead.has_data`** — теперь строки из одних пробелов не считаются данными (требование теста и `COD-03`).
9. **`docs/reports/audit-phase1.md` не включен в коммит** — файл был untracked до Phase 5. Чтобы не смешивать задачи (`PRC-04`) и не публиковать исторический отчет без пометки `DOC-05`, он оставлен для Phase 6.

## NOT VERIFIED

| Что | Причина | Кто проверяет |
|-----|---------|---------------|
| Запуск GitHub Actions workflows | workflows ещё не отправлены в GitHub; локально проверены только команды и YAML | владелец после push/PR |
| `gitleaks-action` в CI | локально проверен CLI gitleaks 8.30.1, не GitHub Action; для организаций может потребоваться `GITLEAKS_LICENSE` | владелец по результату Actions |
| `docker compose up` | требует реальных секретов и создал бы второй polling-инстанс бота | владелец на изолированном стенде |
| Ruleset/branch protection | настраивается только в GitHub | владелец |

## Baseline vs итог

| Метрика | Baseline | Итог |
|---------|----------|------|
| Тесты | 0 | 55 passed |
| Покрытие | не измерялось | 99.30% (6 модулей) |
| Ruff | не настроен | 0 ошибок, формат чистый |
| Bandit | не запускался | 0 medium+ |
| Gitleaks (история) | 1 false positive | 0 findings (fingerprint в `.gitleaksignore`) |
| CI | отсутствовал | 2 workflow, 7 jobs, блокирующие |
| Docker build | не проверялся в Phase 5 | успешно |
