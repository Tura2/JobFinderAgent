# Security Policy

## Supported versions

Only the latest commit on `master` is actively maintained.

## Reporting a vulnerability

If you discover a security vulnerability, please **do not** open a public GitHub issue.

Instead, report it by emailing the repository owner (see the GitHub profile linked in the repo). Include:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fix (optional)

You can expect an acknowledgement within 72 hours and a resolution or status update within 14 days.

## Scope

This project is a self-hosted personal tool. The relevant attack surface is:

- The login endpoint (`POST /auth/login`) — brute-force protection is in place (5 failures / 60s per IP)
- The session cookie — HMAC-signed, `httponly`, `samesite=strict`
- The `SESSION_SECRET_KEY` env var — must be a strong random secret (32+ bytes); never commit it
- The `PWA_ACCESS_TOKEN` env var — the login password; rotate if exposed

## Out of scope

- Vulnerabilities in OpenRouter, Telegram, or other third-party services
- Issues that require physical access to the host machine
- Rate limiting on non-auth endpoints (this is a single-user personal tool)
