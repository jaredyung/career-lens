from database import get_connection


def main():
    conn = get_connection()

    print("\nTotal jobs:")
    print(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM jobs
            """
        ).fetchone()[0]
    )

    print("\nTop companies:")
    print(
        conn.execute(
            """
            SELECT
                company,
                COUNT(*) AS job_count
            FROM jobs
            GROUP BY company
            ORDER BY job_count DESC
            LIMIT 10
            """
        ).fetchdf()
    )

    print("\nAverage salary:")
    print(
        conn.execute(
            """
            SELECT
                ROUND(AVG(salary_min), 2) AS avg_salary_min,
                ROUND(AVG(salary_max), 2) AS avg_salary_max
            FROM jobs
            WHERE salary_min IS NOT NULL
              AND salary_max IS NOT NULL
            """
        ).fetchdf()
    )

    conn.close()


if __name__ == "__main__":
    main()