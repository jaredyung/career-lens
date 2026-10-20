"""Optional read-only CLI summary using the dashboard's salary definition."""

from database import get_connection, get_job_count


def main():
    with get_connection(read_only=True) as conn:
        print("\nTotal jobs:")
        print(get_job_count(conn))
        print("\nTop companies:")
        print(conn.execute(
            """
            SELECT company, COUNT(*) AS job_count
            FROM jobs
            WHERE company IS NOT NULL
            GROUP BY company
            ORDER BY job_count DESC
            LIMIT 10
            """
        ).fetchdf())
        print("\nEstimated salaries (range midpoints):")
        print(conn.execute(
            """
            SELECT
                ROUND(AVG((salary_min + salary_max) / 2), 2)
                    AS estimated_average_salary,
                ROUND(MEDIAN((salary_min + salary_max) / 2), 2)
                    AS estimated_median_salary
            FROM jobs
            WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL
            """
        ).fetchdf())


if __name__ == "__main__":
    main()
