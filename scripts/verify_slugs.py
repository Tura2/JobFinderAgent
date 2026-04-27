#!/usr/bin/env python3
"""
Checks all active companies' Greenhouse/Lever ATS slugs by hitting their public API.
Prints a report of broken slugs (HTTP != 200).

Usage (from repo root, with backend venv active):
  python scripts/verify_slugs.py           # read-only report
  python scripts/verify_slugs.py --fix     # interactive: enter correct slug for each broken one
"""
import asyncio
import os
import sys
from pathlib import Path

# Set working dir to backend so .env and DB path resolve correctly
os.chdir(Path(__file__).parent.parent / "backend")
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

import httpx
from sqlmodel import Session, create_engine, select

from app.models.company import Company
from app.config import settings

FIX_MODE = "--fix" in sys.argv

engine = create_engine(settings.database_url, echo=False)


async def check_slug(client: httpx.AsyncClient, company: Company) -> dict:
    if company.ats_type == "greenhouse" and company.ats_slug:
        url = f"https://boards.greenhouse.io/{company.ats_slug}/jobs"
    elif company.ats_type == "lever" and company.ats_slug:
        url = f"https://api.lever.co/v0/postings/{company.ats_slug}"
    else:
        return {"company": company.name, "status": "skip", "url": None, "ok": True}

    try:
        resp = await client.get(url, timeout=10.0, follow_redirects=True)
        return {
            "company": company.name,
            "id": company.id,
            "slug": company.ats_slug,
            "ats_type": company.ats_type,
            "status": resp.status_code,
            "ok": resp.status_code == 200,
            "url": url,
        }
    except Exception as e:
        return {
            "company": company.name,
            "id": company.id,
            "slug": company.ats_slug,
            "ats_type": company.ats_type,
            "status": "error",
            "ok": False,
            "url": url,
            "error": str(e),
        }


async def main():
    with Session(engine) as session:
        companies = list(session.exec(
            select(Company)
            .where(Company.active == True)
            .where(Company.ats_type.in_(["greenhouse", "lever"]))
        ).all())

    print(f"Checking {len(companies)} Greenhouse/Lever companies...\n")

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[check_slug(client, c) for c in companies])

    broken = []
    for r in sorted(results, key=lambda x: (x.get("ok", True), x["company"])):
        if r["status"] == "skip":
            continue
        icon = "✅" if r.get("ok") else "❌"
        err = f"  ({r.get('error', '')})" if not r.get("ok") and "error" in r else ""
        print(f"{icon}  {r['company']:<30}  {r['ats_type']:<12}  slug={r['slug']:<25}  HTTP {r['status']}{err}")
        if not r.get("ok"):
            broken.append(r)

    print(f"\n{len(broken)} broken slug(s) out of {len(results)} checked.\n")

    if not FIX_MODE or not broken:
        if broken:
            print("Re-run with --fix to interactively update slugs.")
        return

    print("--- Fix mode: enter the correct slug for each broken company ---")
    print("(Find the real slug at: boards.greenhouse.io/<slug>/jobs or api.lever.co/v0/postings/<slug>)\n")

    with Session(engine) as session:
        for r in broken:
            new_slug = input(f"New slug for {r['company']} (current: {r['slug']}, Enter to skip): ").strip()
            if new_slug:
                company = session.get(Company, r["id"])
                company.ats_slug = new_slug
                session.add(company)
                session.commit()
                print(f"  → Updated {r['company']} slug to: {new_slug}")

    print("\nDone. Re-run without --fix to verify.")


asyncio.run(main())
