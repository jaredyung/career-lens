"""Fetch an Adzuna sample, normalize postings, and insert unseen source IDs."""

import os

import pandas as pd
import requests
from dotenv import load_dotenv

from database import (
    PROJECT_ROOT,
    create_jobs_table,
    get_connection,
    get_job_count,
    insert_jobs,
)
from roles import ROLES, classify_role

BASE_URL = "https://api.adzuna.com/v1/api/jobs/us/search"
SEARCH_TERMS = [role.lower() for role in ROLES]
PAGES_PER_SEARCH = 10
RESULTS_PER_PAGE = 50
DEFAULT_LOCATION = "United States"


def fetch_jobs(
    search_term="data scientist",
    location=DEFAULT_LOCATION,
    results_per_page=RESULTS_PER_PAGE,
    page=1,
):
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        raise RuntimeError("Set ADZUNA_APP_ID and ADZUNA_APP_KEY before ingestion.")

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": results_per_page,
        "what": search_term,
        "where": location,
        "content-type": "application/json",
    }
    try:
        response = requests.get(f"{BASE_URL}/{page}", params=params, timeout=30)
        response.raise_for_status()
        return response.json()["results"]
    except (requests.RequestException, ValueError, KeyError):
        # Request exceptions can include the full URL and credential query params.
        raise RuntimeError(
            f"Adzuna request failed for {search_term!r}, page {page}. "
            "Check credentials, connectivity, and API availability."
        ) from None


def fetch_multiple_pages(
    search_term,
    location=DEFAULT_LOCATION,
    pages=PAGES_PER_SEARCH,
    results_per_page=RESULTS_PER_PAGE,
):
    all_jobs = []
    for page in range(1, pages + 1):
        print(f"Fetching {search_term} - page {page}/{pages}...")
        jobs = fetch_jobs(search_term, location, results_per_page, page)
        all_jobs.extend(jobs)
        if len(jobs) < results_per_page:
            print(f"Reached the final available page for {search_term}.")
            break
    return all_jobs


def jobs_to_dataframe(jobs):
    records = []
    for job in jobs:
        title = job.get("title")
        records.append({
            "job_id": job.get("id"),
            "title": title,
            "company": (job.get("company") or {}).get("display_name"),
            "location": (job.get("location") or {}).get("display_name"),
            "description": job.get("description"),
            "created": job.get("created"),
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            "category": (job.get("category") or {}).get("label"),
            "job_url": job.get("redirect_url"),
            "role_category": classify_role(title),
        })
    return pd.DataFrame(records)


def main():
    # Load credentials only when running ingestion, never as an import side effect.
    load_dotenv(PROJECT_ROOT / ".env")
    all_jobs = []
    for search_term in SEARCH_TERMS:
        all_jobs.extend(fetch_multiple_pages(search_term))
    df = jobs_to_dataframe(all_jobs)
    print(f"Downloaded {len(df)} jobs before database deduplication.")
    with get_connection() as conn:
        create_jobs_table(conn)
        insert_jobs(conn, df)
        print(f"Database now contains {get_job_count(conn)} unique jobs.")


if __name__ == "__main__":
    main()
