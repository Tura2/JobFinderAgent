# JobFinderAgent

An AI-powered job hunting agent that monitors Israeli tech company job boards, scores each opening against your profile using an LLM, and sends a Telegram alert when a strong match appears.

![stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20React%20%2B%20SQLite-blue)
![license](https://img.shields.io/badge/license-MIT-green)

---

## How it works

```
APScheduler (every N hours)
  → Fetch jobs from 68+ Israeli tech companies (Greenhouse, Lever, Workday, custom, LinkedIn)
  → Normalize to a unified schema
  → Dedup by content hash (never re-scores a seen job)
  → AI matchmaker (OpenRouter LLM) → 5 weighted sub-scores → total 0–100
  → Score ≥ threshold → pick best CV variant → save match → Telegram notification
  → Score < threshold → saved as "near miss" (visible in PWA, no alert)
```

The sub-scores and their weights:

| Dimension | Max |
|---|---|
| Tech stack match | 30 |
| Role type fit | 25 |
| Domain relevance | 20 |
| Seniority alignment | 15 |
| Location | 10 |

---

## Features

- **PWA dashboard** — browse matches, near-misses, application tracker, company watchlist
- **Telegram alerts** — instant notification with job title, company, score, and reasoning
- **ATS pre-fill links** — one-click to open Greenhouse/Lever application form pre-filled with your info
- **CV variant selector** — automatically picks the most relevant CV version per job
- **Manual scan trigger** — don't want to wait for the scheduler? Hit the button
- **Company management** — add/remove/toggle companies from the watchlist via the PWA

---

## Tech stack

| Layer | Tech |
|---|---|
| Backend | FastAPI, SQLModel, APScheduler, Scrapling |
| AI | OpenRouter (default: `openai/gpt-oss-120b:free`) |
| Database | SQLite |
| Frontend | React 18, Vite, Tailwind CSS |
| Notifications | Telegram Bot API |
| Deploy | systemd on Oracle Cloud Ubuntu VM |

---

## Quick start (local)

**1. Clone and configure**

```bash
git clone https://github.com/Tura2/JobFinderAgent
cd JobFinderAgent
cp backend/.env.example backend/.env
# edit backend/.env — fill in your API keys and profile info
```

**2. Backend**

```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**3. Frontend**

```bash
cd frontend
cp .env.example .env.local
# set VITE_API_URL=http://localhost:8000 and VITE_ACCESS_TOKEN=<your token>
npm install && npm run dev
```

Open `http://localhost:5173` — the PWA proxies API calls to the backend.

---

## Configuration

All config lives in `backend/.env`:

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | Get one free at [openrouter.ai](https://openrouter.ai) |
| `OPENROUTER_MODEL` | LLM to use (default: `openai/gpt-oss-120b:free`) |
| `MATCH_THRESHOLD` | Minimum score to trigger an alert (default: 65) |
| `SCAN_INTERVAL_HOURS` | How often to scan (default: 4) |
| `TELEGRAM_BOT_TOKEN` | Create a bot via [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Your Telegram user or group ID |
| `PWA_ACCESS_TOKEN` | Any strong secret — used to auth the PWA |
| `APPLICANT_*` | Your name/email/LinkedIn for ATS pre-fill links |

---

## Candidate profile

Edit `backend/user_profile.md` to describe your skills, preferences, and hard stops. The matchmaker reads this file verbatim when scoring each job — the more specific you are, the better the scores.

Use `docs/onboarding-questionnaire.md` as a guide for filling it in.

---

## Adding companies

68 Israeli tech companies are pre-loaded. To seed them:

```bash
python scripts/seed_companies.py --dry-run   # preview
python scripts/seed_companies.py             # insert
```

To add more, either use the PWA company form or edit `scripts/companies_seed.json` and re-run the seeder. See `docs/company-research-prompt.md` for a Claude.ai prompt that auto-researches companies and outputs the correct JSON format.

---

## Deployment (Oracle Cloud VM)

See [docs/deploy-guide.md](docs/deploy-guide.md) for the full step-by-step guide including:
- Push to `main` and SSH deploy
- Environment setup
- DB migration for existing installs
- systemd service setup
- Company seeding on the VM
- Claude Code prompts to use on the VM for debugging

---

## Project structure

```
backend/
  app/
    ingestion/     # ATS fetchers (Greenhouse, Lever, Scrapling, LinkedIn)
    pipeline/      # Normalizer, dedup, matchmaker, CV selector
    routers/       # FastAPI route handlers
    models/        # SQLModel table definitions
    notifications/ # Telegram sender
  user_profile.md  # Your candidate profile (fill this in)
frontend/
  src/             # React PWA
scripts/
  seed_companies.py        # Bulk company importer
  companies_seed.json      # 68 pre-loaded Israeli tech companies
docs/
  deploy-guide.md          # VM deployment guide
  onboarding-questionnaire.md
  company-research-prompt.md
```

---

## License

MIT
