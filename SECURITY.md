# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Do NOT open a public issue for security vulnerabilities.**

Instead, contact the repository owner directly through GitHub's private vulnerability reporting feature:
- Go to the repository's Security tab
- Click "Report a vulnerability"
- Describe the issue in detail

## What to include in your report

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Response timeline

- Initial acknowledgment: within 7 days
- Status update: within 14 days
- Fix or mitigation: as soon as possible

## Security considerations

This project is a **demonstration prototype** (level D per QUALITY_STANDARD.md). It is NOT intended for production use with real personal data without additional security review.

Key security features:
- Secrets are managed via environment variables (never hardcoded)
- Service account credentials are mounted read-only in Docker
- Application logs never contain Telegram user/chat identifiers, message content, spreadsheet IDs, credential paths, or API keys (see below)
- Google Sheets writes use `value_input_option='RAW'` to prevent formula injection
- Messages are deduplicated by `(chat_id, message_id)` in a bounded in-memory deque (last 1000 entries) to prevent duplicate writes

## What is NOT logged

Application logs must not contain personal data or deployment secrets. In particular, the following are **never** written to logs:

- Telegram `chat_id`, `user_id` / `effective_user` (id, username, first/last name)
- Message text or any other message content
- Extracted lead fields (name, phone, service, date, time)
- The original message attached to a saved lead
- The Google Sheets `spreadsheet_id` or sheet URL
- The service account `credentials` file path or its contents
- API keys and bot tokens (including `TELEGRAM_BOT_TOKEN` and `LLM_API_KEY`)

Exception logging records only the exception class/type. Full tracebacks and exception messages are not emitted for LLM, Sheets, and message-processing failures, because third-party error payloads can embed request content, spreadsheet IDs, or credential paths.

Each incoming request gets a random `correlation_id` (`uuid4`, generated at the start of `handle_text`). That opaque value is passed through the call chain (`extract_lead`, `append_lead`) and included in log lines, so the stages of one request can be correlated without exposing who sent it. It is not derived from any Telegram identifier and is safe to use for diagnostics and support.

What **may** be logged: `correlation_id`, the fact that an event happened (message received, duplicate skipped, lead saved), `message_id` (used to detect duplicates), message length, processing stage, and error type/class.

## Known limitations

- No rate limiting per user (beyond Telegram's own limits)
- No encryption at rest for data in Google Sheets (depends on Google's security)
- LLM API calls transmit message content to third-party providers
- No GDPR/HIPAA compliance out of the box
