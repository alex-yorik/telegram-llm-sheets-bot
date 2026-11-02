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
- Personal data is not logged (only chat_id and message length)
- Google Sheets writes use `value_input_option='RAW'` to prevent formula injection
- Messages are deduplicated by message_id to prevent duplicate writes

## Known limitations

- No rate limiting per user (beyond Telegram's own limits)
- No encryption at rest for data in Google Sheets (depends on Google's security)
- LLM API calls transmit message content to third-party providers
- No GDPR/HIPAA compliance out of the box
