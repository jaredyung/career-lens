from database import get_connection


def calculate_market_coverage(target_role, user_skills,):
    conn = get_connection()

    role_jobs = conn.execute(
        """
        SELECT job_id
        FROM jobs
        WHERE role_category = ?
        """,
        [target_role],
    ).fetchdf()

    if role_jobs.empty:
        conn.close()

        return {
            "total_jobs": 0,
            "current_coverage": 0,
            "recommendations": [],
        }

    role_job_ids = role_jobs["job_id"].tolist()

    placeholders = ",".join(
        ["?"] * len(role_job_ids)
    )

    job_skills = conn.execute(
        f"""
        SELECT
            job_id,
            skill
        FROM job_skills
        WHERE job_id IN ({placeholders})
        """,
        role_job_ids,
    ).fetchdf()

    conn.close()

    if job_skills.empty:
        return {
            "total_jobs": len(role_jobs),
            "current_coverage": 0,
            "recommendations": [],
        }

    user_skills_lower = {
        skill.lower()
        for skill in user_skills
    }

    skills_by_job = (
        job_skills
        .groupby("job_id")["skill"]
        .apply(set)
        .to_dict()
    )

    total_jobs = len(role_jobs)

    covered_jobs = set()

    for job_id, required_skills in skills_by_job.items():
        required_skills_lower = {
            skill.lower()
            for skill in required_skills
        }

        if user_skills_lower.intersection(required_skills_lower):
            covered_jobs.add(job_id)

    current_coverage = (
        len(covered_jobs) / total_jobs * 100
    )

    all_skills = sorted(
        job_skills["skill"].unique()
    )

    recommendations = []

    for skill in all_skills:
        if skill.lower() in user_skills_lower:
            continue

        new_skill_set = user_skills_lower | {
            skill.lower()
        }

        newly_covered_jobs = set()

        for job_id, required_skills in skills_by_job.items():
            required_skills_lower = {
                required_skill.lower()
                for required_skill in required_skills
            }

            if new_skill_set.intersection(required_skills_lower):
                newly_covered_jobs.add(job_id)

        new_coverage = (
            len(newly_covered_jobs)
            / total_jobs
            * 100
        )

        gain = new_coverage - current_coverage

        recommendations.append(
            {
                "skill": skill,
                "new_coverage": new_coverage,
                "coverage_gain": gain,
            }
        )

    recommendations.sort(
        key=lambda x: x["coverage_gain"],
        reverse=True,
    )

    return {
        "total_jobs": total_jobs,
        "current_coverage": current_coverage,
        "recommendations": recommendations[:10],
    }


if __name__ == "__main__":
    result = calculate_market_coverage(
        target_role="Data Engineer",
        user_skills=[
            "Python",
            "SQL",
            "Snowflake",
        ],
    )

    print(
        f"Jobs analyzed: {result['total_jobs']}"
    )

    print(
        f"Current coverage: "
        f"{result['current_coverage']:.1f}%"
    )

    print()

    print("Best skills to learn next:")

    for recommendation in result[
        "recommendations"
    ]:
        print(
            f"{recommendation['skill']}: "
            f"+{recommendation['coverage_gain']:.1f} points "
            f"→ {recommendation['new_coverage']:.1f}%"
        )