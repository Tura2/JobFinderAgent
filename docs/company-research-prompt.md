# Company Research Prompt

Paste this into **Claude.ai** (with Projects / web search enabled) or **OPENCLAW with browsing**.
It will return a JSON array ready to drop into `scripts/companies_seed.json`.

---

## Prompt (copy everything below this line)

---

I'm building a job-hunting agent that monitors tech companies' job boards and alerts me when a relevant role opens. I need you to research Israeli tech companies for me and return the results in a specific JSON format.

### My target geography
Companies with offices or HQ in any of these cities:
- Tel Aviv, Herzliya, Ra'anana, Netanya, Ramat Gan, Petah Tikva, Kfar Saba, Hod HaSharon, Bnei Brak, Givatayim, Even Yehuda, Hadera

### What I'm looking for
Tech companies (software, SaaS, AI, fintech, cybersecurity, developer tools, data, adtech) that:
- Have an active engineering team in Israel
- Are actively hiring (or likely to hire in the near future)
- Are not pure consulting / outsourcing shops

Skip: non-tech companies, pure consultancies, staffing agencies.

### Research task
For each company you find, visit their careers page and detect their ATS (Applicant Tracking System):

**ATS detection rules:**
- **greenhouse** → careers page contains `boards.greenhouse.io/{slug}` or `greenhouse.io`. Slug is the part after the last `/` in that URL.
- **lever** → careers page contains `jobs.lever.co/{slug}`. Slug is the part after the last `/`.
- **workday** → careers page contains `myworkdayjobs.com` or `/wday/`.
- **custom** → any proprietary careers page (company's own site, SmartRecruiters, Comeet, Taleo, iCIMS, etc.)
- **linkedin** → company only posts jobs on LinkedIn, no dedicated ATS.

### Output format
Return a JSON array. Each object must have these exact keys:

```json
[
  {
    "name": "Company Name",
    "city": "Tel Aviv",
    "website": "https://company.com",
    "ats_type": "greenhouse",
    "ats_slug": "companyslug",
    "linkedin_url": "https://www.linkedin.com/company/company-name",
    "career_page_url": "https://boards.greenhouse.io/companyslug"
  }
]
```

Rules:
- `ats_type` must be exactly one of: `greenhouse`, `lever`, `workday`, `custom`, `linkedin`
- `ats_slug` — fill in only for `greenhouse` and `lever` (it's the identifier in the API URL). Set to `null` for workday/custom/linkedin.
- `career_page_url` — the direct URL to their job listings page.
- `linkedin_url` — their LinkedIn company page (format: `https://www.linkedin.com/company/{slug}`)
- `city` — the Israeli city where their main engineering office is. Include this even though the app doesn't store it — I'll use it to filter.
- If you can't verify the ATS type with confidence, set `ats_type` to `"custom"` and leave `ats_slug` as `null`.

### Prioritization
Sort the results by desirability for a Full-Stack / AI Engineer (junior–mid level). Put companies most likely to have relevant open roles first.

Companies I especially want (include these if you find them active):
- Monday.com, Wix, Fiverr, Taboola, AppsFlyer, WalkMe, Outbrain, Kaltura, SentinelOne
- Jfrog, Snyk, Cloudinary, Skai (Kenshoo), Perion, IronSource (Unity), Gong, ClickSoftware (Salesforce)
- Any AI/LLM startups or fintech startups based in the listed cities

Return ONLY the JSON array. No explanation, no markdown wrapper around the JSON — just the raw array starting with `[`.

---

## After you get the JSON

1. Save the output to `scripts/companies_seed.json`
2. Run:
   ```bash
   cd backend && source venv/Scripts/activate
   python scripts/seed_companies.py
   ```
