import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import database

APP_PATH = Path(__file__).resolve().parents[1] / "app" / "app.py"


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path_patch = patch.object(database, "DB_PATH", Path(self.folder.name) / "test.duckdb")
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)
        records = [
            ("1", "Data Scientist", "A", "Chicago", 100000, 140000),
            ("2", "Data Engineer", "B", "Austin", 80000, 100000),
            ("3", "Data Engineer", "A", "Chicago", 120000, 160000),
        ]
        frame = pd.DataFrame(records, columns=[
            "job_id", "title", "company", "location", "salary_min", "salary_max"
        ])
        frame["role_category"] = frame["title"]
        frame["description"] = "Example posting"
        frame["category"] = "IT Jobs"
        frame["created"] = pd.Timestamp("2026-10-18")
        frame["job_url"] = "https://example.com/posting"
        with database.get_connection() as conn:
            database.create_jobs_table(conn)
            database.insert_jobs(conn, frame)

    def test_filters_apply_to_comparisons_company_and_listings(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "3")
        app.selectbox(key="filter_company").select("A").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "2")
        self.assertEqual(app.metric[4].value, "1")
        self.assertEqual(app.metric[8].value, "1")
        self.assertEqual(app.selectbox(key="company_detail").options, ["A"])
        self.assertEqual(set(app.dataframe[-1].value.company), {"A"})
        app.selectbox(key="filter_role").select("Data Engineer").run()
        self.assertEqual(app.metric[4].value, "0")
        self.assertEqual(app.metric[8].value, "1")
        app.text_input(key="filter_location").set_value("Austin").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 0)
        app.button[0].click().run()
        app.number_input(key="filter_salary").set_value(150000).run()
        self.assertEqual(app.metric[0].value, "1")
        self.assertEqual(app.dataframe[-1].value.iloc[0].salary_max, 160000)
        app.text_input(key="filter_title").set_value("[").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.metric), 0)

    def test_refresh_and_missing_salary(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
        with database.get_connection() as conn:
            conn.execute("UPDATE jobs SET salary_min = NULL, salary_max = NULL")
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[2].value, "N/A")
        self.assertEqual(app.metric[3].value, "N/A")


if __name__ == "__main__":
    unittest.main()
