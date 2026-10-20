import os
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import duckdb
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import ingest
from database import create_jobs_table, get_job_count, insert_jobs
from roles import ROLES, classify_role, update_existing_roles


class IngestionTests(unittest.TestCase):
    def test_ten_page_limit_and_short_page_stop(self):
        with patch.object(ingest, "fetch_jobs", return_value=[{}] * 50) as fetch:
            with redirect_stdout(StringIO()):
                result = ingest.fetch_multiple_pages("data engineer")
            self.assertEqual(len(result), 500)
            self.assertEqual(fetch.call_count, 10)
            self.assertEqual([c.args[3] for c in fetch.call_args_list], list(range(1, 11)))
        with patch.object(ingest, "fetch_jobs", side_effect=[[{}] * 50, [{}]]) as fetch:
            with redirect_stdout(StringIO()):
                self.assertEqual(len(ingest.fetch_multiple_pages("data engineer")), 51)
            self.assertEqual(fetch.call_count, 2)

    def test_normalization_to_database_preserves_role_url_and_source_id(self):
        job = {
            "id": "123", "title": "Senior Data Engineer", "company": None,
            "location": {"display_name": "Chicago"}, "category": None,
            "created": "2026-10-18T12:00:00Z",
            "redirect_url": "https://example.com/jobs/123",
        }
        with duckdb.connect(":memory:") as conn:
            create_jobs_table(conn)
            insert_jobs(conn, ingest.jobs_to_dataframe([]))
            self.assertEqual(get_job_count(conn), 0)
            insert_jobs(conn, ingest.jobs_to_dataframe([job, job]))
            self.assertEqual(conn.execute(
                "SELECT job_id, role_category, job_url FROM jobs"
            ).fetchall(), [("123", "Data Engineer", "https://example.com/jobs/123")])

    def test_classification(self):
        for role in ROLES:
            self.assertEqual(classify_role("Senior " + role), role)
        self.assertEqual(classify_role(None), "Other")
        self.assertEqual(classify_role("Product Manager"), "Other")
        self.assertEqual(classify_role("ML Engineer"), "Machine Learning Engineer")
        self.assertEqual(classify_role("BI Analyst"), "Data Analyst")

    def test_request_failures_hide_credential_urls(self):
        with patch.dict(os.environ, {"ADZUNA_APP_ID": "test", "ADZUNA_APP_KEY": "test"}):
            with patch.object(ingest.requests, "get", side_effect=requests.HTTPError("SECRET_URL")):
                with self.assertRaises(RuntimeError) as caught:
                    ingest.fetch_jobs()
                self.assertNotIn("SECRET_URL", str(caught.exception))
                self.assertTrue(caught.exception.__suppress_context__)

    def test_reclassification_keeps_urls(self):
        from tempfile import TemporaryDirectory
        import database

        with TemporaryDirectory() as folder:
            with patch.object(database, "DB_PATH", Path(folder) / "jobs.duckdb"):
                with database.get_connection() as conn:
                    create_jobs_table(conn)
                    conn.execute("""
                        INSERT INTO jobs (job_id, title, role_category, job_url)
                        VALUES ('1', 'Data Scientist', 'Other', 'https://example.com/1')
                    """)
                update_existing_roles()
                with database.get_connection(read_only=True) as conn:
                    self.assertEqual(conn.execute(
                        "SELECT role_category, job_url FROM jobs"
                    ).fetchone(), ("Data Scientist", "https://example.com/1"))


if __name__ == "__main__":
    unittest.main()
