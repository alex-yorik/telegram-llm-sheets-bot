# Post-Review Fixes Report

- **Дата:** 2026-11-03
- **Ветка:** `fix/post-review-improvements`
- **Базовая ветка:** `main`
- **Pull Request:** [#2](https://github.com/alex-yorik/telegram-llm-sheets-bot/pull/2)
- **Исходный commit SHA (`post-review-prep` tag):** `176af4cb2d3e8ea3361428b9bc935c79a1dc7e73`
- **Итоговый HEAD (код до коммита этого отчёта):** `c19a5048464fe8b32c2008b07bcc3021950303d2`
- **Коммит отчёта:** последний коммит в ветке (SHA выдаётся в чате и виден через `git log -1`)
- **Автор проверки:** AI-assisted self-review, не независимый сторонний аудит.

## 1. Область работы

Закрытие замечаний внешнего post-review ТЗ по пунктам 10, 11, 12:
проверка CI workflows, локальный прогон всех quality gates, финальный
отчёт с фактическими статусами. Merge в `main` не выполнялся.

## 2. Изменённые файлы

| Файл | Тип | Описание |
|---|---|---|
| `handlers.py` | M | `deque(maxlen=N)` вместо `set.clear()`, FIFO-вытеснение; `_mark_seen` только после успешной записи в Sheets; `correlation_id` вместо `chat_id` в логах |
| `llm.py` | M | `correlation_id` в `extract_lead` и во всех лог-сообщениях; перевод docstring на английский |
| `sheets.py` | M | `chat_id` заменён на `correlation_id` в `append_lead` и логах; английские docstring |
| `main.py` | M | Английские docstring; без изменения логики запуска |
| `models.py` | M | Английские docstring |
| `config.py` | M | Английские docstring |
| `requirements.txt` | M | Удалены dev/CI-инструменты, остались только runtime-зависимости |
| `requirements-dev.txt` | A | `-r requirements.txt` + pytest/pytest-cov/pytest-asyncio/ruff/bandit/pip-audit |
| `.github/workflows/ci.yml` | M | Установка из `requirements-dev.txt`; cache по двум requirements-файлам |
| `.github/workflows/quality-gates.yml` | M | Установка из `requirements-dev.txt`; cache по двум requirements-файлам |
| `.gitleaksignore` | M | Задокументированы 2 false positive по тестовым `correlation_id` |
| `SECURITY.md` | M | Раздел «What is NOT logged»: перечень PII, который не попадает в логи |
| `README.md` | M | Переформулирован раздел об AI-assisted разработке |
| `LICENSE` | M | Удалено противоречивое «proprietary and confidential» |
| `tests/test_handlers.py` | M | Тесты FIFO-вытеснения, повторной попытки после LLM/Sheets ошибки, отсутствия повторной обработки |
| `tests/test_logging_privacy.py` | A | Проверка, что в логах есть `correlation_id` и нет `chat_id`/текста сообщения |
| `tests/test_sheets.py` | M | Сигнатура `correlation_id` вместо `chat_id` |
| `docs/reports/pip-audit-*` | A | Полные результаты pip-audit (json/txt) и отчёт Фазы 3 |
| `docs/reports/post-review-fixes-report.md` | A | Этот отчёт |

## 3. Исправленные проблемы

### P1 — критические

**P1-1. Дедупликация сообщений (`handlers.py`).**
Было: `set` + `processed_messages.clear()` при переполнении, сообщение
помечалось обработанным до записи в Sheets. При временной ошибке LLM/Sheets
повторная доставка update навсегда игнорировалась, а очистка сбрасывала всю
историю.
Стало: `collections.deque(maxlen=MAX_PROCESSED_MESSAGES)` с автоматическим FIFO-
вытеснением только старейшей записи. Ключ `(chat_id, message_id)` сохраняется,
`_mark_seen` вызывается только после успешного `append_lead`. Ошибка LLM или
Sheets оставляет сообщение неотмеченным, поэтому retry возможен.

**P1-2. Приватность логов (`handlers.py`, `llm.py`, `sheets.py`).**
Было: в логах присутствовали `chat_id` и `user_id`.
Стало: на каждый запрос генерируется `uuid4` `correlation_id`, который
передаётся через `extract_lead` и `append_lead`. В логи попадают только
`correlation_id`, длина сообщения, стадия обработки и тип ошибки. Текст
сообщения, Telegram-идентификаторы и извлечённые поля не логируются.
`tests/test_logging_privacy.py` проверяет это поведение.

**P1-3. Аудит зависимостей (pip-audit).**
Обнаружена уязвимость `PYSEC-2026-1845` / `CVE-2025-71176` в `pytest 7.4.3`.
`pytest` обновлён до `9.0.3`, `pytest-asyncio` — до `1.4.1.post1` (требуется
для совместимости с pytest 9). Повторный `pip-audit`: уязвимостей не найдено.
`pytest` — dev/CI-зависимость и в production-образ не входит.

**P1-4. Разделение runtime/dev-зависимостей.**
`requirements.txt` теперь содержит только runtime-пакеты. `pytest`, `ruff`,
`bandit`, `pip-audit` вынесены в `requirements-dev.txt`. Docker-образ
устанавливает только `requirements.txt`, поэтому dev-инструменты в него не
попадают.

### P2 — документация и полировка

- **P2-1.** Русские комментарии и docstring в исходниках переведены на английский.
- **P2-2.** `README.md`: формулировка об AI-assisted разработке приведена к
  корректному описанию роли автора без самоуничижения.
- **P2-3.** `LICENSE`: убрано слово «confidential», сохранено «All rights reserved».
- **P2-4.** `SECURITY.md`: добавлен явный перечень того, что не логируется.
- **P2-5.** `.gitleaksignore`: задокументированы false positive, чтобы
  `secrets-scan` не падал на тестовых строках.

## 4. Обоснование технических решений

- **`deque(maxlen=N)`** даёт O(1) append и детерминированное вытеснение
  старейшего элемента. Альтернатива с ручным `clear()` создавала окно, в
  котором вся история дедупликации терялась.
- **Отметка после успеха** выбрана сознательно: at-least-once важнее, чем
  at-most-once для заявок. Возможный дубль при редком сбое между записью в
  Sheets и отметкой предпочтительнее потери заявки.
- **`correlation_id` (uuid4)** не является персональными данными и позволяет
  связать стадии одного запроса без раскрытия Telegram-идентификаторов.
- **Разделение requirements** уменьшает production-образ и поверхность атаки;
  CI продолжает ставить dev-зависимости из `requirements-dev.txt`.
- **Обновление pytest вместе с pytest-asyncio** — вынужденное: старый
  `pytest-asyncio 0.23.2` несовместим с pytest 9 (`AttributeError: 'Package'
  object has no attribute 'obj'`).

## 5. Новые и изменённые тесты

- `tests/test_handlers.py`: FIFO-лимит кэша, вытеснение только старейшей
  записи, retry после `LLMRequestError`, retry после `SheetsError`,
  отсутствие повторной обработки после успеха, проверка `correlation_id`
  через `ANY`.
- `tests/test_logging_privacy.py` (новый, 204 строки): `correlation_id`
  логируется, `chat_id` и текст сообщения — нет; ID различаются между
  запросами.
- `tests/test_sheets.py`: вызовы переведены на `correlation_id`.
- Итог: **68 passed** (было 55).

## 6. Результаты локальных проверок

| Проверка | Команда | Результат | Статус |
|---|---|---|---|
| pytest | `.venv/bin/pytest --cov=. --cov-report=term-missing` | 68 passed, 10.58s | **VERIFIED** |
| Coverage | в составе pytest | 99.30% (порог 80%) | **VERIFIED** |
| Ruff check | `.venv/bin/ruff check .` | All checks passed, exit 0 | **VERIFIED** |
| Ruff format | `.venv/bin/ruff format --check .` | 15 files left unchanged, exit 0 | **VERIFIED** |
| Bandit | `.venv/bin/bandit -c pyproject.toml -r . -ll` | No issues; Medium/High = 0 | **VERIFIED** |
| pip-audit | `.venv/bin/pip-audit` | No known vulnerabilities found | **VERIFIED** |
| Docker config | `docker compose config -q` | OK | **VERIFIED** |
| Docker build | `docker compose build` | success, образ 221 MB | **VERIFIED** |
| Секреты | `git ls-files` на `.env` и `credentials/*.json` | совпадений нет | **VERIFIED** |

Покрытие 99.30%: единственная непокрытая строка — `main.py:94`
(`asyncio.run(main())` под `if __name__ == "__main__"`), что ожидаемо для
точки входа.

## 7. CI workflows

### `ci.yml`

- **Триггеры:** `push` в `main` и `feat/**`; `pull_request` в `main`.
- **Permissions:** `contents: read`.
- **Jobs:**
  - `test` — Python 3.12, `pytest --cov=. --cov-fail-under=80`, upload `coverage.xml`.
  - `lint` — Ruff check, Ruff format check, Bandit.
  - `docker-build` — `docker build`.

### `quality-gates.yml`

- **Триггеры:** `push` в `main`; `pull_request` в `main`.
- **Permissions:** `contents: read`.
- **Jobs:**
  - `secrets-scan` — Gitleaks (fetch-depth 0).
  - `bandit` — повторный Bandit (дублирует `ci.yml`).
  - `coverage-gate` — повторный pytest с порогом 80%.
  - `modularity` — лимиты 500 строк на файл и 50 строк на функцию.

### Замечания по условиям запуска

- **Наблюдение, не ошибка:** `ci.yml` не содержит `push` для `fix/**`.
  Ветка `fix/post-review-improvements` получает проверки через
  `pull_request` события открытого PR #2. Если такая ветка будет запушена
  без PR, CI на push не запустится. Для текущего workflow это допустимо,
  но при желании можно добавить `fix/**` в `push.branches`.
- **Дублирование:** Bandit и coverage выполняются дважды (`ci.yml` и
  `quality-gates.yml`). Это осознанное дублирование gates, не ошибка.
- **Ошибочных условий, блокирующих текущий PR, не обнаружено.**

## 8. GitHub Actions (PR #2)

Последний head SHA проверок: `c19a5048464fe8b32c2008b07bcc3021950303d2`.

| Workflow | Run | Статус |
|---|---|---|
| CI | https://github.com/alex-yorik/telegram-llm-sheets-bot/actions/runs/41578488847 | success |
| Quality Gates | https://github.com/alex-yorik/telegram-llm-sheets-bot/actions/runs/41578488858 | success |

Jobs:

| Check | Workflow | Результат |
|---|---|---|
| `test (3.12)` | CI | pass |
| `lint` | CI | pass |
| `docker-build` | CI | pass |
| `secrets-scan` | Quality Gates | pass |
| `bandit` | Quality Gates | pass |
| `coverage-gate` | Quality Gates | pass |
| `modularity` | Quality Gates | pass |

История: первые прогоны на commit `c19a504`-предшественнике падали
(`lint`/`secrets-scan`), причина устранена в `b3f85b1`. После этого все
прогоны зелёные; финальные — на `c19a504`.

## 9. Статусы по пунктам ТЗ

Точный текст пунктов 10–12 post-review ТЗ в репозитории отсутствует,
поэтому ниже зафиксировано сопоставление по формулировке текущей задачи.

| Пункт ТЗ | Что проверялось | Статус |
|---|---|---|
| 10. Проверка CI workflows | Триггеры, jobs, отсутствие ошибочных условий | **VERIFIED** (с замечанием про `fix/**` push) |
| 11. Локальный прогон всех проверок | pytest, coverage, ruff, bandit, pip-audit, docker compose build | **VERIFIED** |
| 12. Финальный отчёт | Этот документ со статусами и доказательствами | **VERIFIED** |
| P1-1 Дедупликация | Код + тесты + CI | **VERIFIED** |
| P1-2 Приватность логов | Код + тесты + CI | **VERIFIED** |
| P1-3 Аудит зависимостей | pip-audit after fix | **VERIFIED** |
| P1-4 Runtime/dev split | requirements + Dockerfile + CI | **VERIFIED** |
| P2-1…P2-5 Документация/полировка | Diff + CI | **VERIFIED** |
| Live E2E с реальными Telegram/LLM/Sheets | Не выполнялся в этой фазе | **NOT VERIFIED** |
| Production-нагрузка и лимиты Google Sheets | Не проверялись | **NOT APPLICABLE** для Level D |
| Merge в `main` | Выполняет только владелец | **NOT APPLICABLE** (намеренно не выполнялось) |

## 10. Оставшиеся проблемы и риски

1. **Live E2E не проверен на текущей ревизии.** Мокированные тесты
   подтверждают control flow и обработку ошибок, но не реальные права
   сервисного аккаунта, раскладку листа, квоты и задержки Google API.
2. **`ci.yml` не запускается на push в `fix/**` без PR.** С открытым PR это
   покрыто, но для будущих fix-веток без PR gate не сработает.
3. **Дедупликация in-memory.** При рестарте контейнера история теряется;
   возможен повторная запись уже сохранённой заявки. Очередь/БД не внедрялись.
4. **Нет lock-файла транзитивных зависимостей.** Docker-образ собирается из
   зафиксированных прямых версий; транзитивные пакеты могут разрешиться в
   новые версии при следующей сборке. Аудит нужно повторять.
5. **Нет healthcheck.** `restart: unless-stopped` реагирует только на выход
   процесса, но не на зависание. Осознанное решение для Level D.
6. **Дублирование gates** (Bandit, coverage) увеличивает время CI, но не
   влияет на корректность.
7. **Docstring в тестах остались на русском** (`tests/test_handlers.py`).
   На проверки не влияет; косметическое расхождение с P2-1.
8. **pip-audit отражает базу на 2026-11-03.** Новые advisory после этой даты
   не учтены.
9. **`.gitleaksignore` привязан к SHA коммитов** и тестовым строкам; при
   переписывании истории fingerprints нужно обновлять.

## 11. Рекомендации владельцу

1. Провести один контролируемый live E2E в тестовой таблице и с тестовым
   бот-токеном; зафиксировать результат как недостающую проверку.
2. Просмотреть diff PR #2 и смержить вручную после одобрения.
3. При желании добавить `fix/**` в `push.branches` в `ci.yml`.
4. Рассмотреть lock-файл (`pip-compile`/`uv lock`) и периодический
   `pip-audit` в CI.
5. Для перехода выше Level D — внешняя очередь/хранилище дедупликации,
   healthcheck с app-level probe и ограничение rate limit.
6. Ротировать credentials, если локальный `.env` когда-либо передавался.

## 12. Итог

**PASS для текущей фазы.** Все заявленные локальные проверки и CI jobs
проходят, P1/P2-исправления подтверждены тестами. Live E2E и
production-поведение остаются **NOT VERIFIED**; merge не выполнялся.
