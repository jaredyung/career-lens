import re

from database import get_connection


SKILLS = {
    "Python": [r"\bpython\b"],
    "SQL": [r"\bsql\b"],
    "R": [r"\br programming\b", r"\br language\b"],
    "Java": [r"\bjava\b"],
    "C++": [r"\bc\+\+\b"],
    "AWS": [r"\baws\b", r"amazon web services"],
    "Azure": [r"\bazure\b"],
    "GCP": [r"\bgcp\b", r"google cloud"],
    "Spark": [r"\bspark\b", r"\bpyspark\b"],
    "Snowflake": [r"\bsnowflake\b"],
    "Databricks": [r"\bdatabricks\b"],
    "dbt": [r"\bdbt\b"],
    "Airflow": [r"\bairflow\b"],
    "Docker": [r"\bdocker\b"],
    "Kubernetes": [r"\bkubernetes\b"],
    "Tableau": [r"\btableau\b"],
    "Power BI": [r"\bpower\s*bi\b"],
    "Excel": [r"\bexcel\b"],
    "TensorFlow": [r"\btensorflow\b"],
    "PyTorch": [r"\bpytorch\b"],
    "scikit-learn": [r"\bscikit[- ]learn\b", r"\bsklearn\b"],
}


def extract_skills(description):
    if not description:
        return []

    found_skills = []

    for skill, patterns in SKILLS.items():
        for pattern in patterns:
            if re.search(pattern, description, flags=re.IGNORECASE):
                found_skills.append(skill)
                break

    return found_skills


def create_job_skills_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_skills (
            job_id VARCHAR,
            skill VARCHAR,
            PRIMARY KEY (job_id, skill)
        )
        """
    )


def populate_job_skills(conn):
    jobs = conn.execute(
        """
        SELECT job_id, description
        FROM jobs
        """
    ).fetchall()

    rows = []

    for job_id, description in jobs:
        skills = extract_skills(description)

        for skill in skills:
            rows.append((job_id, skill))

    conn.executemany(
        """
        INSERT OR IGNORE INTO job_skills
        VALUES (?, ?)
        """,
        rows,
    )

    return len(rows)


def show_top_skills(conn):
    return conn.execute(
        """
        SELECT
            skill,
            COUNT(*) AS job_count
        FROM job_skills
        GROUP BY skill
        ORDER BY job_count DESC
        """
    ).fetchdf()


if __name__ == "__main__":
    conn = get_connection()

    create_job_skills_table(conn)

    matches = populate_job_skills(conn)

    print(f"Processed {matches} job-skill matches.")
    print()
    print("Top skills:")
    print(show_top_skills(conn).head(20))

    conn.close()