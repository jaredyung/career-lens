"""Shared database location, schema, and explicit job insertion mapping."""

from pathlib import Path

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "careerlens.duckdb"


def get_connection(*, read_only=False):
    if not read_only:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def create_jobs_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            job_id VARCHAR PRIMARY KEY,
            title VARCHAR,
            company VARCHAR,
            location VARCHAR,
            description VARCHAR,
            created TIMESTAMP,
            salary_min DOUBLE,
            salary_max DOUBLE,
            category VARCHAR,
            job_url VARCHAR,
            role_category VARCHAR
        )
        """
    )
    # Support databases created before title-based role classification.
    conn.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS role_category VARCHAR")


def insert_jobs(conn, df: pd.DataFrame):
    """Keep the first record for each Adzuna ID; map columns explicitly."""
    if df.empty:
        return

    conn.register("jobs_df", df)
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO jobs (
                job_id, title, company, location, description, created,
                salary_min, salary_max, category, job_url, role_category
            )
            SELECT
                CAST(job_id AS VARCHAR), title, company, location, description,
                CAST(created AS TIMESTAMP), salary_min, salary_max, category,
                job_url, role_category
            FROM jobs_df
            """
        )
    finally:
        conn.unregister("jobs_df")


def get_job_count(conn):
    return conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
