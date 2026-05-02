# Open Source Release Plan

This document tracks all work required to publish JobFinderAgent as a public open source project.

---

## Status Legend
- [ ] Pending
- [x] Done
- 🔒 Requires manual action (cannot be automated)

---

## Phase 1 — Deploy Pending Code Fixes

These changes are already written and sitting as uncommitted modifications on branch `fix/job-pre-filter-and-model-update`.

| # | File | Change | Status |
|---|---|---|---|
| 1.1a | `backend/app/config.py` | Default model → `deepseek/deepseek-v4-flash`, add `SCAN_BATCH_SIZE=50` | [ ] |
| 1.1b | `backend/app/scheduler.py` | Apply `scan_batch_size` cap to unscored job recovery | [ ] |
| 1.1c | `backend/app/pipeline/matchmaker.py` | Respect `Retry-After` header on 429 before re-raising | [ ] |
| 1.1d | `frontend/src/pages/Settings.tsx` | Polling interval 2s → 5s; auto-resume scan UI on mount if already running | [ ] |

**Deploy steps:**
```bash
cd /home/ubuntu/JobFinderAgent
git add backend/app/config.py backend/app/scheduler.py backend/app/pipeline/matchmaker.py frontend/src/pages/Settings.tsx
git commit -m "fix: deepseek model default, batch cap, 429 Retry-After, settings poll 5s"
cd frontend && npm run build && cd ..
sudo systemctl restart jobfinder
sudo systemctl status jobfinder
```

---

## Phase 2 — Security & Open Source Blockers

> Must complete **before making the repository public**.

### 2.1 🔒 Rotate all live secrets
All secrets live only in the gitignored `backend/.env` — they were **never committed**. However they should be rotated before publishing as a precaution if the repo was ever accidentally exposed.

- [ ] Revoke and regenerate **OpenRouter API key** at openrouter.ai/settings
- [ ] Revoke and regenerate **Telegram bot token** via @BotFather (`/revoke`)
- [ ] Regenerate `PWA_ACCESS_TOKEN`: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Regenerate `SESSION_SECRET_KEY`: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Update `backend/.env` on the VM with new values
- [ ] `sudo systemctl restart jobfinder`

### 2.2 🔒 Scrub personal data from git history
`backend/user_profile.md` with real name, phone, and email was committed in the initial commits. `docs/deploy-guide.md` also contains email in one commit.

```bash
pip install git-filter-repo

# Option A — remove the file from all history (then re-add template as new commit)
git filter-repo --path backend/user_profile.md --invert-paths --force

# Option B — scrub only the personal data blobs in-place
git filter-repo --blob-callback '
  import re
  data = blob.data.decode("utf-8", errors="replace")
  data = re.sub(r"\+972[\d\s\-]+", "[PHONE]", data)
  data = re.sub(r"offir\.tura@gmail\.com", "[EMAIL]", data)
  data = re.sub(r"Offir Tura", "[YOUR NAME]", data)
  blob.data = data.encode("utf-8")
' --force

git push --force origin main
```

> After force-pushing, run `git pull --rebase` on the VM before the next deploy.

### 2.3 Replace `user_profile.md` with anonymized template
- [ ] Rewrite `backend/user_profile.md` as a fully-commented template with placeholder values
- [ ] All sections preserved (Summary, Contact, Skills, Experience, Preferences, etc.)
- [ ] Add header note: *"Fill in your actual profile. See `docs/onboarding-questionnaire.md` for guidance."*

### 2.4 Add `LICENSE` file
- [ ] Create `LICENSE` at repo root with standard MIT text (year 2026)

### 2.5 Update `backend/.env.example`
- [ ] `OPENROUTER_MODEL` → `deepseek/deepseek-v4-flash`
- [ ] Add `SCAN_BATCH_SIZE=50` with comment
- [ ] Add `LOW_MATCH_FLOOR=30` (in config but missing from example)
- [ ] Verify no real values or personal data remain

---

## Phase 3 — Code Quality

### 3.1 Login brute-force protection (`backend/app/routers/auth.py`)
Current state: only `asyncio.sleep(1)` on failed login — no rate limiting.

**Implementation:**
- In-process IP → failure timestamp list (`dict[str, list[float]]`)
- Threshold: 5 failures within 60 seconds → return `429 Too Many Requests` with `Retry-After: 60`
- On success: clear IP's counter
- Memory guard: clear dict if it exceeds 10,000 entries
- Update `backend/tests/test_api_auth.py` with rate-limit test cases

### 3.2 Pagination on list endpoints
Current state: `/matches`, `/matches/near-misses`, `/tracker` return all rows — could be thousands.

**Implementation:**
- Add `?page=1&limit=50` query params (max `limit=200`) to all three endpoints
- Apply `.offset((page - 1) * limit).limit(limit)` to each SQLModel query
- Add `X-Total-Count` response header (non-breaking — frontend keeps working as-is)
- Update tests in `test_api_matches.py` and `test_api_tracker.py`

---

## Phase 4 — Docs & Governance

| # | File | What | Status |
|---|---|---|---|
| 4.1 | `CLAUDE.md` | Update model table: `deepseek/deepseek-v4-flash` as recommended paid model; revise free-tier guidance | [ ] |
| 4.2 | `README.md` | Replace old model references (`openai/gpt-oss-120b:free`) with new default | [ ] |
| 4.3 | `CONTRIBUTING.md` | Fork/PR workflow, branch naming, test requirements, personal data warning, no-Alembic note | [ ] |
| 4.4 | `CHANGELOG.md` | v1.0.0 entry: Added / Changed / Fixed covering full pipeline + all release fixes | [ ] |
| 4.5 | `.github/SECURITY.md` | Vulnerability disclosure policy, supported versions, contact, scope | [ ] |

---

## Dependency Order

```
Phase 1 (deploy fixes)
  │
  ├── Phase 2.1 🔒 rotate secrets
  │       └── Phase 2.2 🔒 scrub git history
  │               └── Phase 2.3 anonymize user_profile.md
  │                       ├── Phase 2.5 update .env.example
  │                       ├── Phase 3.1 auth rate limiting
  │                       ├── Phase 3.2 pagination
  │                       └── Phase 4.3 CONTRIBUTING.md
  │
  ├── Phase 2.4 LICENSE          (independent)
  ├── Phase 4.1 CLAUDE.md        (after Phase 1)
  ├── Phase 4.2 README.md        (after Phase 1)
  └── Phase 4.5 SECURITY.md      (independent)

Phase 4.4 CHANGELOG.md           (last — after 3.1 + 3.2 complete)
```

---

## Summary

| Phase | Tasks | Owner | Effort |
|---|---|---|---|
| 1 — Deploy fixes | 4 files | You | S |
| 2 — Security | 5 items (2 manual) | You + Claude | M |
| 3 — Code quality | 2 features | Claude | M each |
| 4 — Docs | 5 files | Claude | S each |

**Your blockers before going public:** 2.1 (rotate secrets) + 2.2 (scrub git history).
Everything else can be done by Claude once you give the go-ahead per phase.
