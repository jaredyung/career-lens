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


from database import get_connection, create_jobs_table


def update_existing_roles():
    conn = get_connection()

    create_jobs_table(conn)

    jobs = conn.execute(
        """
        SELECT job_id, title
        FROM jobs
        """
    ).fetchall()

    for job_id, title in jobs:
        role = classify_role(title)

        conn.execute(
            """
            UPDATE jobs
            SET role_category = ?
            WHERE job_id = ?
            """,
            [role, job_id],
        )

    conn.close()


if __name__ == "__main__":
    update_existing_roles()
    print("Role categories updated.")