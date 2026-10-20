import sys
import unittest
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from database import create_jobs_table, insert_jobs


class InsertJobsTests(unittest.TestCase):
    def test_role_and_url_mapping_and_duplicate_handling(self):
        # Cover both a fresh database and the schema before roles were added.
        for legacy_schema in (False, True):
            with self.subTest(legacy_schema=legacy_schema):
                conn = duckdb.connect(":memory:")
                try:
                    if legacy_schema:
                        conn.execute("""
                            CREATE TABLE jobs (
                                job_id VARCHAR PRIMARY KEY, title VARCHAR,
                                company VARCHAR, location VARCHAR,
                                description VARCHAR, created TIMESTAMP,
                                salary_min DOUBLE, salary_max DOUBLE,
                                category VARCHAR, job_url VARCHAR
                            )
                        """)
                    create_jobs_table(conn)
                    record = {
                        "job_id": "123", "title": "Data Engineer",
                        "company": "Example", "location": "Chicago",
                        "description": "Python and SQL", "created": "2026-10-17",
                        "salary_min": 100000, "salary_max": 150000,
                        "category": "IT Jobs", "role_category": "Data Engineer",
                        "job_url": "https://example.com/jobs/123",
                    }
                    # Input DataFrame order should not affect the mapping either.
                    df = pd.DataFrame([record])[list(reversed(record))]
                    insert_jobs(conn, df)
                    insert_jobs(conn, df)
                    self.assertEqual(
                        conn.execute(
                            "SELECT job_id, role_category, job_url FROM jobs"
                        ).fetchall(),
                        [("123", "Data Engineer", "https://example.com/jobs/123")],
                    )
                finally:
                    conn.close()


if __name__ == "__main__":
    unittest.main()
