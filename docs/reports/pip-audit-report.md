# Отчёт: аудит зависимостей pip-audit (Фаза 3)

**Дата проверки:** 2026-11-03
**Python:** 3.12.3
**ОС:** Linux (Docker/Ubuntu 24.04, venv `.venv`)
**pip-audit:** 2.10.1
**Ветка:** `fix/post-review-improvements`
**Автор проверки:** AI-assisted self-review, не независимый сторонний аудит.

## Команды

```bash
.venv/bin/pip-audit --format json > docs/reports/pip-audit-results.json
.venv/bin/pip-audit --format columns > docs/reports/pip-audit-results.txt
```

Проверялось установленное окружение `.venv` (65 пакетов), которое собирается из
`requirements.txt`. Полный машинный вывод — в `pip-audit-results.json`, текстовый —
в `pip-audit-results.txt`.

## Проверенные зависимости

Прямые зависимости из `requirements.txt`:

| Пакет | Версия до | Версия после |
|---|---|---|
| python-telegram-bot | 20.7 | 20.7 |
| pydantic | 2.5.0 | 2.5.0 |
| pydantic-settings | 2.1.0 | 2.1.0 |
| openai | 1.7.0 | 1.7.0 |
| gspread | 6.0.0 | 6.0.0 |
| google-auth | 2.25.0 | 2.25.0 |
| pytest | 7.4.3 | **9.0.3** |
| pytest-cov | 4.1.0 | 4.1.0 |
| pytest-asyncio | 0.23.2 | **1.4.1.post1** |
| ruff | 0.1.6 | 0.1.6 |
| bandit | 1.7.6 | 1.7.6 |

Транзитивные зависимости (всего 65 пакетов) также вошли в проверку, в том числе:
`anyio`, `certifi`, `charset-normalizer`, `coverage`, `google-auth-oauthlib`,
`httpx`, `idna`, `oauthlib`, `pydantic-core`, `requests`, `requests-oauthlib`,
`urllib3`, `rsa`, `pyasn1`, `setuptools`-цепочка и другие. Полный список — в
`pip-audit-results.json`.

## Найденные уязвимости

До обновления pip-audit нашёл 2 записи (дубликат одного и того же advisory) в 1 пакете:

| Пакет | Версия | ID | Fix Versions | Алиасы |
|---|---|---|---|---|
| pytest | 7.4.3 | PYSEC-2026-1845 | 9.0.3 | GHSA-6w46-j5rx-g56g, CVE-2025-71176 |

Описание: pytest до 9.0.2 на UNIX полагается на директории с шаблоном имени
`/tmp/pytest-of-{user}`, что позволяет локальному пользователю вызвать отказ в
обслуживании или, возможно, повысить привилегии.

Важно: pytest — dev/CI-зависимость. В production Docker-образ он **не входит**
(`Dockerfile` устанавливает `requirements.txt`, но приложение запускается как
`python main.py`; pytest в рантайме не используется).

## Выполненные исправления

- `pytest`: `7.4.3` → `9.0.3` — версия с исправлением PYSEC-2026-1845.
- `pytest-asyncio`: `0.23.2` → `1.4.1.post1` — вынужденное сопутствующее
  обновление. С `pytest 9.0.3` версия `0.23.2` падает с
  `AttributeError: 'Package' object has no attribute 'obj'` при сборе тестов.
- `pytest-cov`: без изменений (`4.1.0`), совместим с `pytest 9.0.3`.
- Остальные прямые зависимости не обновлялись.

## Проверка после обновления

- `pip-audit` (JSON и columns): **No known vulnerabilities found**, exit code `0`.
- `pytest`: **68 passed**.
- `pytest --cov=. --cov-report=term-missing --cov-fail-under=80`: **68 passed**,
  покрытие **99.30%** (порог 80% пройден).

## Оставшиеся риски

- Docker-образ собирается из `requirements.txt`, где зафиксированы только прямые
  зависимости. Транзитивные пакеты могут разрешиться в более новые версии при
  следующей сборке, поэтому аудит следует повторять в CI и/или фиксировать
  lock-файл (в рамках этой фазы не требовалось).
- Проверка отражает состояние базы уязвимостей pip-audit на 2026-11-03.
  Новые advisory после этой даты не учтены.
- Версии `ruff 0.1.6`, `bandit 1.7.6`, `pytest-cov 4.1.0` устарели, но
  известных уязвимостей на дату проверки по ним нет.

## Итоговый статус

**PASS** — известные уязвимости устранены, тесты и coverage-gate проходят.
