# Contributing to JobFinderAgent

Thanks for your interest in contributing!

## Before you start

**Personal data warning:** `backend/user_profile.md` is your private candidate profile. The file committed to this repo is an anonymized template — never commit your real name, phone, or email. The file is not gitignored so that the template ships with the repo; it's your responsibility to keep personal data out of commits.

## How to contribute

1. Fork the repository
2. Create a branch from `master`: `git checkout -b feat/your-feature` or `fix/your-bugfix`
3. Make your changes (see guidelines below)
4. Run tests: `cd backend && pytest`
5. Run linting: `ruff check app/ tests/ && ruff format app/ tests/`
6. Open a pull request against `master`

## Branch naming

| Prefix | Use for |
|---|---|
| `feat/` | New features |
| `fix/` | Bug fixes |
| `docs/` | Documentation only |
| `chore/` | Tooling, dependencies, config |
| `refactor/` | Code restructuring with no behavior change |

## Code guidelines

- **No Alembic.** The project uses manual SQLite migrations (`ALTER TABLE`). If you add a column, document the migration SQL in your PR description.
- **Tests required** for any new API endpoint or pipeline change. The `client` fixture in `conftest.py` handles auth automatically — no need to set cookies in individual tests.
- **New required env vars** must be added to `conftest.py` via `os.environ.setdefault` before app import, or tests will fail with a `ValidationError` at import time.
- **Frontend changes**: run `npx vitest run` before submitting.
- **No secrets in commits.** Use `.env` (gitignored) for all secrets. Never commit real API keys, tokens, or personal data.

## Running tests locally

```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
pytest
```

Frontend unit tests:

```bash
cd frontend
npm install
npx vitest run
```

## Questions?

Open an issue — happy to help.
