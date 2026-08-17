import os

import pandas as pd
import requests
from dotenv import load_dotenv

from database import create_jobs_table, get_connection, get_job_count, insert_jobs

load_dotenv()

APP_ID = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")

BASE_URL = "https://api.adzuna.com/v1/api/jobs/us/search"


def fetch_jobs(search_term="data scientist", location="United States", results_per_page=50, page=1,):
    url = f"{BASE_URL}/{page}"
    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "results_per_page": results_per_page,
        "what": search_term,
        "where": location,
        "content-type": "application/json",
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()

    return data["results"]

def fetch_multiple_pages(search_term, location="United States", pages=3, results_per_page=50,):
    all_jobs = []

    for page in range(1, pages + 1):
        print(f"Fetching {search_term} - page {page}...")

        jobs = fetch_jobs(
            search_term=search_term,
            location=location,
            results_per_page=results_per_page,
            page=page,
        )

        all_jobs.extend(jobs)

    return all_jobs


def jobs_to_dataframe(jobs):
    records = []

    for job in jobs:
        records.append(
            {
                "job_id": job.get("id"),
                "title": job.get("title"),
                "company": job.get("company", {}).get("display_name"),
                "location": job.get("location", {}).get("display_name"),
                "description": job.get("description"),
                "created": job.get("created"),
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "category": job.get("category", {}).get("label"),
                "job_url": job.get("redirect_url"),
            }
        )

    return pd.DataFrame(records)


if __name__ == "__main__":
    search_terms = [
        "data scientist",
        "data engineer",
        "machine learning engineer",
        "data analyst",
        "machine learning engineer",
        "analytics engineer",
    ]
    all_jobs = []

    for search_term in search_terms:
        jobs = fetch_multiple_pages(search_term, pages=3, results_per_page=50,)
        all_jobs.extend(jobs)

    df = jobs_to_dataframe(all_jobs)

    print()
    print(df.head())
    print()
    print(f"Downloaded {len(df)} jobs before database deduplication.")

    conn = get_connection()

    create_jobs_table(conn)
    insert_jobs(conn, df)

    total_jobs = get_job_count(conn)

    print(f"Database now contains {total_jobs} unique jobs.")

    conn.close()