from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st


DB_PATH = Path("data/careerlens.duckdb")


@st.cache_data
def load_jobs():
    conn = duckdb.connect(str(DB_PATH), read_only=True)

    df = conn.execute(
        """
        SELECT
            job_id,
            title,
            company,
            location,
            created,
            salary_min,
            salary_max,
            category,
            job_url
        FROM jobs
        ORDER BY created DESC
        """
    ).fetchdf()

    conn.close()

    return df


st.set_page_config(
    page_title="CareerLens",
    page_icon="🔎",
    layout="wide",
)

st.title("CareerLens")
st.caption("Explore the data job market using real job posting data.")

jobs = load_jobs()

total_jobs = len(jobs)
total_companies = jobs["company"].nunique()

salary_df = jobs.dropna(subset=["salary_min", "salary_max"]).copy()

if len(salary_df) > 0:
    salary_df["salary_midpoint"] = (
        salary_df["salary_min"] + salary_df["salary_max"]
    ) / 2

    avg_salary = salary_df["salary_midpoint"].mean()
else:
    avg_salary = 0


col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Jobs Analyzed", f"{total_jobs:,}")

with col2:
    st.metric("Companies", f"{total_companies:,}")

with col3:
    st.metric("Average Salary", f"${avg_salary:,.0f}")


st.divider()

st.subheader("Top Hiring Companies")

top_companies = (
    jobs.groupby("company")
    .size()
    .reset_index(name="job_count")
    .sort_values("job_count", ascending=False)
    .head(10)
)

st.bar_chart(
    top_companies,
    x="company",
    y="job_count",
)


st.divider()

st.subheader("Salary Distribution")

if len(salary_df) > 0:
    st.bar_chart(
        salary_df["salary_midpoint"].value_counts(
            bins=10,
            sort=False
        )
    )
else:
    st.info("Not enough salary data available yet.")


st.divider()

st.subheader("Recent Job Postings")

display_jobs = jobs[
    [
        "title",
        "company",
        "location",
        "created",
        "salary_min",
        "salary_max",
        "job_url",
    ]
].copy()

st.dataframe(
    display_jobs,
    use_container_width=True,
    hide_index=True,
)