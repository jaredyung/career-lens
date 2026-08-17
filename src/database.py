from pathlib import Path

import duckdb
import pandas as pd


DB_PATH = Path("data/careerlens.duckdb")


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))


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
            job_url VARCHAR
        )
        """
    )


def insert_jobs(conn, df: pd.DataFrame):
    conn.register("jobs_df", df)

    conn.execute(
        """
        INSERT OR IGNORE INTO jobs
        SELECT
            CAST(job_id AS VARCHAR),
            title,
            company,
            location,
            description,
            CAST(created AS TIMESTAMP),
            salary_min,
            salary_max,
            category,
            job_url
        FROM jobs_df
        """
    )

    conn.unregister("jobs_df")


def get_job_count(conn):
    result = conn.execute(
        """
        SELECT COUNT(*)
        FROM jobs
        """
    ).fetchone()

    return result[0]