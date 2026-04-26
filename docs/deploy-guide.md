# Deployment Guide — JobFinderAgent → Oracle Cloud VM

## Prerequisites (local machine)

- Git remote `origin` points to your GitHub repo
- You have SSH access to the Oracle Cloud Ubuntu VM
- VM has Python 3.11+, Node 18+, git installed

---

## Step 1 — Push to `main`

```bash
# You are on master — merge to main and push
git checkout main
git merge master
git push origin main
git checkout master
```

---

## Step 2 — First-time VM setup (skip if already deployed)

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
- Install Python deps into `backend/venv`
- Build the React frontend (`npm install && npm run build`)
- Copy the systemd service file and enable it

---

## Step 3 — Configure environment variables

```bash
cd ~/JobFinderAgent/backend
cp .env.example .env
nano .env
```

Fill in every value:

```
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=openai/gpt-oss-120b:free
MATCH_THRESHOLD=65
SCAN_INTERVAL_HOURS=4
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
PWA_ACCESS_TOKEN=<pick a strong random token>
PWA_BASE_URL=http://<VM_IP>:8000
DATABASE_URL=sqlite:///./jobfinder.db
APPLICANT_FIRST_NAME=Offir
APPLICANT_LAST_NAME=Tura
APPLICANT_EMAIL=offir.tura@gmail.com
APPLICANT_LINKEDIN_URL=https://linkedin.com/in/<your-handle>
APPLICANT_PORTFOLIO_URL=https://<your-portfolio>
```

---

## Step 4 — Migrate existing DB (if DB already exists)

If `backend/jobfinder.db` already exists from a previous deploy, add the new column:

```bash
cd ~/JobFinderAgent/backend
sqlite3 jobfinder.db "ALTER TABLE matches ADD COLUMN score_breakdown TEXT DEFAULT NULL;"
```

If the DB is fresh (first deploy), skip this — SQLModel creates the schema automatically on startup.

---

## Step 5 — Start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable jobfinder
sudo systemctl start jobfinder
sudo systemctl status jobfinder
```

Watch logs:

```bash
sudo journalctl -u jobfinder -f
```

---

## Step 6 — Seed the 68 companies

Wait for the service to be running (health check passes), then:

```bash
cd ~/JobFinderAgent/backend
source venv/bin/activate
cd ..
python scripts/seed_companies.py --dry-run   # preview first
python scripts/seed_companies.py             # insert for real
```

---

## Step 7 — Verify

```bash
# Health check
curl http://localhost:8000/health

# List companies (replace TOKEN with your PWA_ACCESS_TOKEN)
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/companies

# Trigger a manual scan
curl -X POST -H "Authorization: Bearer TOKEN" http://localhost:8000/trigger-scan

# Watch scan logs
sudo journalctl -u jobfinder -f
```

Open the PWA in your browser: `http://<VM_IP>:8000`

---

## Subsequent deploys (after first setup)

```bash
# Local: push new commits to main (repo: https://github.com/Tura2/JobFinderAgent)
git checkout main && git merge master && git push origin main && git checkout master

# On VM:
ssh ubuntu@<VM_IP>
cd ~/JobFinderAgent && bash scripts/deploy.sh
sudo systemctl restart jobfinder
```

---

## Prompts for Claude Code on the VM

If you SSH into the VM and run `claude` there, paste these prompts as needed:

### Check service health and logs

```
The jobfinder systemd service is running on this Ubuntu VM.
Check: sudo systemctl status jobfinder and show me the last 50 lines of journalctl -u jobfinder.
Tell me if there are any errors in the logs.
```

### Debug a failing scan

```
The jobfinder scan is failing. The service is at ~/JobFinderAgent.
Backend is FastAPI + APScheduler. Ingestion code is in backend/app/ingestion/.
Check the logs (journalctl -u jobfinder -n 100) and read the relevant ingestion file.
Tell me what's failing and fix it.
```

### Add a new company manually

```
I need to add a new company to the jobfinder watchlist.
The REST API runs on localhost:8000.
PWA_ACCESS_TOKEN is in ~/JobFinderAgent/backend/.env.
Add this company via POST /companies:
  name: "..."
  ats_type: "greenhouse" | "lever" | "workday" | "custom" | "linkedin"
  ats_slug: "..." (only for greenhouse/lever, else null)
  career_page_url: "..."
  linkedin_url: "..."
Show me the response.
```

### Seed companies from updated JSON

```
I have an updated scripts/companies_seed.json in ~/JobFinderAgent.
Run: cd ~/JobFinderAgent && source backend/venv/bin/activate && python scripts/seed_companies.py --dry-run
Then if it looks good, run without --dry-run.
Show me the output.
```

### Update the user profile for better matching

```
I want to update my job matching profile.
The file is ~/JobFinderAgent/backend/user_profile.md.
Read it and then ask me questions to update the sections that feel stale.
After I answer, rewrite the file with my updated preferences.
```

### Check match scores and breakdown

```
The jobfinder SQLite DB is at ~/JobFinderAgent/backend/jobfinder.db.
Show me the 10 most recent matches with their score, score_breakdown (JSON), and job title + company.
Query: SELECT m.id, m.score, m.score_breakdown, j.title, c.name FROM matches m JOIN jobs j ON m.job_id=j.id JOIN companies c ON j.company_id=c.id ORDER BY m.created_at DESC LIMIT 10;
```
