# Technical Debt

This document tracks known limitations, trade-offs, and future improvements for the telegram-llm-sheets-bot project.

## Current state

This project is classified as **Level D (Demo / Portfolio)** per QUALITY_STANDARD.md v2.1. It is a demonstration prototype, not a production system.

## Known limitations

### 1. No persistent deduplication store
**Severity:** Low
**Impact:** Deduplication uses a bounded in-memory `deque` of `(chat_id, message_id)` keys (last 1000 entries). If the bot restarts, the deque is cleared, and under sustained load the oldest keys are evicted, so a very old duplicate could be processed again.
**Why not fixed:** Adding a database (Redis, SQLite) would significantly increase complexity for a demo project.
**Mitigation:** Documented in README. For production, add a persistent store.

### 2. No rate limiting per user
**Severity:** Low
**Impact:** A single user can send unlimited messages, incurring LLM API costs.
**Why not fixed:** python-telegram-bot has built-in rate limiting, but per-user quotas require additional state management.
**Mitigation:** For production, add a rate limiter (e.g., token bucket) with user-level quotas.

### 3. No encryption at rest for Google Sheets data
**Severity:** Medium (depends on deployment)
**Impact:** Data in Google Sheets is protected by Google's security, but the deployer is responsible for access controls.
**Why not fixed:** Out of scope for this project.
**Mitigation:** Documented in SECURITY.md. Deployer must configure Google Sheets sharing appropriately.

### 4. LLM API calls transmit message content to third parties
**Severity:** Medium
**Impact:** User messages are sent to OpenRouter (or other LLM provider). Privacy depends on the provider's policies.
**Why not fixed:** Fundamental to the architecture.
**Mitigation:** User is informed via `/start` notification. Deployer must choose a trustworthy LLM provider.

### 5. No GDPR/HIPAA compliance
**Severity:** N/A for demo
**Impact:** Project does not implement data subject rights, consent management, or audit trails required by GDPR/HIPAA.
**Why not fixed:** Out of scope for a demo project.
**Mitigation:** Documented in SECURITY.md. Do not use with real personal data without legal review.

### 6. Healthcheck removed
**Severity:** Low
**Impact:** Docker Compose does not verify bot health beyond process existence.
**Why not fixed:** A meaningful healthcheck would require an HTTP endpoint or Telegram API call, adding complexity.
**Mitigation:** Documented in README. For production, add a `/health` endpoint.

### 7. No retry logic for Google Sheets writes
**Severity:** Low
**Impact:** Transient Sheets API failures result in lost leads.
**Why not fixed:** Would require a queue or retry mechanism.
**Mitigation:** For production, add exponential backoff retry or a dead-letter queue.

### 8. Single worksheet support
**Severity:** Low
**Impact:** All leads go to one worksheet. No archiving or multi-sheet support.
**Why not fixed:** Out of scope for demo.
**Mitigation:** For production, add worksheet rotation or archival logic.

## Future improvements (if project evolves to production)

1. Add SQLite/PostgreSQL for persistent deduplication and lead storage
2. Add per-user rate limiting with configurable quotas
3. Add retry logic with exponential backoff for LLM and Sheets API calls
4. Add a `/health` endpoint for proper Docker healthcheck
5. Add metrics (Prometheus) for monitoring LLM calls, Sheets writes, errors
6. Add user consent flow before processing messages
7. Add data export/deletion endpoints for GDPR compliance
8. Add webhook mode instead of polling for better scalability
9. Add support for multiple languages with language detection
10. Add admin commands (/stats, /export, /clear)

## Refactoring opportunities

1. **handlers.py**: Extract response formatting into a separate module.
2. **llm.py**: Add structured output support for providers that offer it (e.g., OpenAI function calling).
3. **sheets.py**: Add batch writes for high-volume scenarios.

## Decision log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-09-07 | Remove healthcheck | False healthcheck (pgrep) is worse than no healthcheck. Proper healthcheck requires HTTP endpoint. |
| 2026-09-07 | In-memory deduplication | Database adds complexity; demo project prioritizes simplicity. |
| 2026-09-07 | No rate limiting | Telegram has own limits; demo project doesn't need per-user quotas. |
| 2026-09-07 | Keep Original Message column | Useful for debugging; can be disabled via configuration in future. |
