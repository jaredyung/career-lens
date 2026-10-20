"""Title-based classification; run directly only to reclassify stored postings."""

from database import create_jobs_table, get_connection

ROLES = [
    "Data Scientist",
    "Data Engineer",
    "Data Analyst",
    "Machine Learning Engineer",
    "Analytics Engineer",
]


def classify_role(title):
    if not title:
        return "Other"

    title = title.lower()

    if (
        "machine learning engineer" in title
        or "ml engineer" in title
        or "ai engineer" in title
    ):
        return "Machine Learning Engineer"

    if (
        "analytics engineer" in title
        or "analytic engineer" in title
    ):
        return "Analytics Engineer"

    if (
        "data engineer" in title
        or "data engineering" in title
    ):
        return "Data Engineer"

    if (
        "data scientist" in title
        or "data science" in title
        or "ml scientist" in title
    ):
        return "Data Scientist"

    if (
        "data analyst" in title
        or "business intelligence analyst" in title
        or "bi analyst" in title
        or "analytics analyst" in title
    ):
        return "Data Analyst"

    return "Other"


def update_existing_roles():
    """Apply current rules to existing rows without changing job URLs."""
    with get_connection() as conn:
        create_jobs_table(conn)
        jobs = conn.execute("SELECT job_id, title FROM jobs").fetchall()
        conn.begin()
        try:
            for job_id, title in jobs:
                conn.execute(
                    "UPDATE jobs SET role_category = ? WHERE job_id = ?",
                    [classify_role(title), job_id],
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


if __name__ == "__main__":
    update_existing_roles()
    print("Role categories updated.")
