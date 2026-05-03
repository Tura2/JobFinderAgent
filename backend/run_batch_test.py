#!/usr/bin/env python3
"""Run health check on all active companies and print results."""
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Load .env before app imports
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from sqlmodel import Session, select
from app.database import engine
from app.models.company import Company
from app.scheduler import fetch_jobs_for_company


async def main():
    results = []
    with Session(engine) as session:
        companies = list(session.exec(select(Company).where(Company.active == True)).all())
        print(f"Testing {len(companies)} active companies...\n")

        for company in companies:
            try:
                jobs = await fetch_jobs_for_company(company)
                count = len(jobs)
                passed = count >= 1
                company.last_test_at = datetime.now(timezone.utc)
                company.last_test_passed = int(passed)
                company.last_test_jobs_found = count
                session.add(company)
                session.commit()
                status = "PASS" if passed else "FAIL"
                print(f"[{status}] {company.name:40s}  {count:>4} jobs  (ats={company.ats_type})")
                results.append((company.name, passed, count, company.ats_type))
            except Exception as e:
                print(f"[ERR ] {company.name:40s}  {e}")
                results.append((company.name, False, 0, company.ats_type))

    print(f"\n--- Summary ---")
    passed_list = [r for r in results if r[1]]
    failed_list = [r for r in results if not r[1]]
    print(f"PASS: {len(passed_list)}/{len(results)}")
    print(f"FAIL: {len(failed_list)}/{len(results)}")
    if failed_list:
        print("\nFailed companies:")
        for name, _, count, ats in failed_list:
            print(f"  - {name} (ats={ats})")


if __name__ == "__main__":
    asyncio.run(main())
