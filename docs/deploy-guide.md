# Deployment Guide — JobFinderAgent → Oracle Cloud VM

## Prerequisites (local machine)

- Git remote `origin` points to your GitHub repo
- SSH access to the Oracle Cloud Ubuntu VM
- VM has Python 3.11+, Node 18+, git installed

---

## Push local changes to production

Always push `master → main` before deploying. The deploy script pulls from `main`.

```bash
git checkout main
git merge master
git push origin main
git checkout master
```

---

## First-time VM setup

SSH into the VM:

```bash
ssh ubuntu@<VM_IP>
```

Then on the VM:

```bash
git clone https://github.com/Tura2/JobFinderAgent ~/JobFinderAgent
cd ~/JobFinderAgent
bash scripts/deploy.sh
```

`deploy.sh` will:
- Pull latest `main`
- Create `backend/venv` and install Python deps
- Build the React frontend (`npm install && npm run build`)
- Copy and enable the systemd service

---

## Configure environment variables

```bash
cd ~/JobFinderAgent/backend
cp .env.example .env
nano .env
```

Fill in every value:

```env
# LLM
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=openai/gpt-oss-120b:free

# Pipeline
MATCH_THRESHOLD=65
LOW_MATCH_FLOOR=30
SCAN_INTERVAL_HOURS=6

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# Auth — session cookies (replaces old Bearer token)
PWA_ACCESS_TOKEN=<pick a strong random password>
SESSION_SECRET_KEY=<generate: python3 -c "import secrets; print(secrets.token_hex(32))">
SESSION_MAX_AGE_DAYS=30

# App
PWA_BASE_URL=http://<VM_IP>:8000

# Database
DATABASE_URL=sqlite:///./jobfinder.db

# Applicant info for ATS pre-fill
APPLICANT_FIRST_NAME=Offir
APPLICANT_LAST_NAME=Tura
APPLICANT_EMAIL=offir.tura@gmail.com
APPLICANT_LINKEDIN_URL=https://linkedin.com/in/<your-handle>
APPLICANT_PORTFOLIO_URL=https://<your-portfolio>
```

> **SESSION_SECRET_KEY is required.** The service won't start without it.
> Generate one: `python3 -c "import secrets; print(secrets.token_hex(32))"`

---

## DB migrations (run once on existing databases)

If `backend/jobfinder.db` already exists from a previous deploy, run these:

```bash
cd ~/JobFinderAgent/backend

# Add score_breakdown column (added 2026-04)
sqlite3 jobfinder.db "ALTER TABLE matches ADD COLUMN score_breakdown TEXT DEFAULT NULL;"

# Add unique constraint on Match.job_id (added 2026-04-27)
sqlite3 jobfinder.db "CREATE UNIQUE INDEX IF NOT EXISTS uq_matches_job_id ON matches(job_id);"
```

Fresh DB (first deploy)? Skip — SQLModel creates the schema automatically on startup.

---

## Install Playwright (required for Workday / custom career pages)

Playwright Chromium must be installed inside the venv for companies that use Workday or custom career pages (Microsoft, Palo Alto, NICE, Check Point, etc.).

```bash
cd ~/JobFinderAgent/backend
source venv/bin/activate
playwright install chromium
```

Expected output ends with:

```text
Chromium ... downloaded to /home/ubuntu/.cache/ms-playwright/chromium-XXXX/chrome-linux/chrome
```

---

## Start / restart the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable jobfinder
sudo systemctl start jobfinder
sudo systemctl status jobfinder
```

Watch live logs:

```bash
sudo journalctl -u jobfinder -f
```

---

## Seed the companies watchlist

Wait until the service is running (health check passes), then:

```bash
cd ~/JobFinderAgent
source backend/venv/bin/activate
python scripts/seed_companies.py --dry-run   # preview first
python scripts/seed_companies.py             # insert for real
```

---

## Fix broken Greenhouse / Lever slugs

After seeding, many companies may have wrong ATS slugs (returning 404).
Run the verification script to find and fix them:

```bash
cd ~/JobFinderAgent
source backend/venv/bin/activate

python scripts/verify_slugs.py           # see which slugs are broken
python scripts/verify_slugs.py --fix     # interactively fix each one
```

For each broken company, look up the correct slug at:

- Greenhouse: `https://boards.greenhouse.io/<slug>/jobs`
- Lever: `https://api.lever.co/v0/postings/<slug>`

---

## Verify the deployment

```bash
# Health check
curl http://localhost:8000/health

# Open the PWA in your browser
http://<VM_IP>:8000
# → You'll see the login page. Enter your PWA_ACCESS_TOKEN as the password.
```

---

## Subsequent deploys

```bash
# Local: push to main
git checkout main && git merge master && git push origin main && git checkout master

# On VM:
ssh ubuntu@<VM_IP>
cd ~/JobFinderAgent && bash scripts/deploy.sh
sudo systemctl restart jobfinder
```

---

## Auth model (session cookies)

The app uses **HMAC-signed session cookies** (not Bearer tokens).

- Visit `http://<VM_IP>:8000` → redirected to `/login`
- Enter `PWA_ACCESS_TOKEN` as the password → sets a `session` cookie
- Cookie is valid for `SESSION_MAX_AGE_DAYS` days (default 30)
- All API routes return `401 JSON` for API clients, `302 → /login` for browsers
- Public paths (no auth needed): `/login`, `/auth/login`, `/auth/logout`, `/health`, `/config`

---

## Useful VM commands

```bash
# Service management
sudo systemctl status jobfinder
sudo systemctl restart jobfinder
sudo journalctl -u jobfinder -f          # live logs
sudo journalctl -u jobfinder -n 100      # last 100 lines

# Manual scan trigger (from VM, while service is running)
curl -X POST http://localhost:8000/trigger-scan \
  -b "session=<paste cookie value from browser devtools>"

# DB — recent matches
sqlite3 backend/jobfinder.db \
  "SELECT m.score, j.title, c.name FROM matches m \
   JOIN jobs j ON m.job_id=j.id \
   JOIN companies c ON j.company_id=c.id \
   ORDER BY m.matched_at DESC LIMIT 10;"

# DB — count jobs per company
sqlite3 backend/jobfinder.db \
  "SELECT c.name, COUNT(j.id) FROM companies c \
   LEFT JOIN jobs j ON j.company_id=c.id \
   GROUP BY c.id ORDER BY COUNT(j.id) DESC;"
```

---

## Claude Code prompts for the VM

### Check service health

```
The jobfinder systemd service is running on this Ubuntu VM at ~/JobFinderAgent.
Run: sudo systemctl status jobfinder and show the last 50 lines of journalctl -u jobfinder.
Tell me if there are errors.
```

### Debug a failing scan

```
The jobfinder scan is failing. Service is at ~/JobFinderAgent.
Backend is FastAPI + APScheduler. Ingestion code is in backend/app/ingestion/.
Check journalctl -u jobfinder -n 100 and the relevant ingestion file.
Tell me what's failing and fix it.
```

### Add a company manually

```
I need to add a new company to the jobfinder watchlist.
The REST API runs on localhost:8000. Get the session cookie from the browser
or log in via: curl -X POST http://localhost:8000/auth/login -d '{"password":"<PWA_ACCESS_TOKEN>"}' -c cookies.txt
Then POST /companies with: name, ats_type (greenhouse|lever|workday|custom|linkedin), ats_slug, career_page_url.
```

### Update the user profile

```
I want to update my job matching profile.
The file is ~/JobFinderAgent/backend/user_profile.md.
Read it, ask me questions about any stale sections, then rewrite it with my answers.
```

### Check match scores

```text
The SQLite DB is at ~/JobFinderAgent/backend/jobfinder.db.
Show me the 10 most recent matches with score, score_breakdown (JSON), job title, and company name.
```
