"""
Bulk-insert companies from scripts/companies_seed.json into the JobFinderAgent API.

Usage:
    cd backend && source venv/Scripts/activate
    python ../scripts/seed_companies.py [--url http://localhost:8000] [--token YOUR_TOKEN]

Or set env vars:
    API_URL=http://localhost:8000
    PWA_ACCESS_TOKEN=yourtoken
"""
import json
import os
import sys
import argparse
import httpx

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SEED_FILE = os.path.join(SCRIPT_DIR, "companies_seed.json")


def load_seed(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Seed file must be a JSON array")
    return data


def insert_company(client: httpx.Client, base_url: str, token: str, company: dict) -> tuple[bool, str]:
    payload = {
        "name": company["name"],
        "website": company.get("website"),
        "ats_type": company["ats_type"],
        "ats_slug": company.get("ats_slug"),
        "linkedin_url": company.get("linkedin_url"),
        "career_page_url": company.get("career_page_url"),
    }
    try:
        resp = client.post(
            f"{base_url}/companies",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        if resp.status_code == 201:
            return True, f"✓  {company['name']}"
        else:
            return False, f"✗  {company['name']} — HTTP {resp.status_code}: {resp.text[:120]}"
    except Exception as e:
        return False, f"✗  {company['name']} — {e}"


def main():
    parser = argparse.ArgumentParser(description="Seed companies into JobFinderAgent")
    parser.add_argument("--url", default=os.getenv("API_URL", "http://localhost:8000"), help="API base URL")
    parser.add_argument("--token", default=os.getenv("PWA_ACCESS_TOKEN", ""), help="Bearer token")
    parser.add_argument("--file", default=DEFAULT_SEED_FILE, help="Path to companies_seed.json")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be inserted without calling the API")
    args = parser.parse_args()

    if not args.token and not args.dry_run:
        # Try to load from backend/.env
        env_path = os.path.join(SCRIPT_DIR, "..", "backend", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("PWA_ACCESS_TOKEN="):
                        args.token = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break

    if not args.token and not args.dry_run:
        print("ERROR: No token. Set PWA_ACCESS_TOKEN env var or pass --token.")
        sys.exit(1)

    try:
        companies = load_seed(args.file)
    except FileNotFoundError:
        print(f"ERROR: Seed file not found: {args.file}")
        print("Run the research prompt in Claude.ai and save the output to scripts/companies_seed.json")
        sys.exit(1)

    print(f"Loaded {len(companies)} companies from {args.file}")
    print(f"Target API: {args.url}")
    print()

    if args.dry_run:
        for c in companies:
            print(f"  {c.get('city', '?'):15}  {c['ats_type']:10}  {c['name']}")
        return

    ok_count = 0
    fail_count = 0
    with httpx.Client() as client:
        for company in companies:
            success, msg = insert_company(client, args.url, args.token, company)
            print(msg)
            if success:
                ok_count += 1
            else:
                fail_count += 1

    print()
    print(f"Done — {ok_count} inserted, {fail_count} failed.")
    if fail_count > 0:
        print("Failed companies may already exist (duplicate name) or had an API error.")


if __name__ == "__main__":
    main()
