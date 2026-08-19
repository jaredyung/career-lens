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


st.sidebar.header("Filters")

title_filter = st.sidebar.text_input(
    "Job title contains",
    placeholder="e.g. data engineer"
)

company_options = ["All"] + sorted(
    jobs["company"].dropna().unique().tolist()
)

company_filter = st.sidebar.selectbox(
    "Company",
    company_options
)

location_filter = st.sidebar.text_input(
    "Location contains",
    placeholder="e.g. Chicago"
)

salary_filter = st.sidebar.number_input(
    "Minimum salary",
    min_value=0,
    value=0,
    step=5000
)



filtered_jobs = jobs.copy()

if title_filter:
    filtered_jobs = filtered_jobs[
        filtered_jobs["title"].str.contains(
            title_filter,
            case=False,
            na=False
        )
    ]

if company_filter != "All":
    filtered_jobs = filtered_jobs[
        filtered_jobs["company"] == company_filter
    ]

if location_filter:
    filtered_jobs = filtered_jobs[
        filtered_jobs["location"].str.contains(
            location_filter,
            case=False,
            na=False
        )
    ]

if salary_filter > 0:
    filtered_jobs = filtered_jobs[
        filtered_jobs["salary_max"].fillna(0) >= salary_filter
    ]



total_jobs = len(filtered_jobs)

total_companies = filtered_jobs["company"].nunique()

salary_df = filtered_jobs.dropna(
    subset=["salary_min", "salary_max"]
).copy()

if len(salary_df) > 0:
    salary_df["salary_midpoint"] = (
        salary_df["salary_min"] + salary_df["salary_max"]
    ) / 2

    avg_salary = salary_df["salary_midpoint"].mean()
else:
    avg_salary = 0


col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Jobs Analyzed",
        f"{total_jobs:,}"
    )

with col2:
    st.metric(
        "Companies",
        f"{total_companies:,}"
    )

with col3:
    if len(salary_df) > 0:
        st.metric(
            "Average Salary",
            f"${avg_salary:,.0f}"
        )
    else:
        st.metric(
            "Average Salary",
            "N/A"
        )



if filtered_jobs.empty:
    st.warning(
        "No jobs match the selected filters. Try adjusting your search."
    )
    st.stop()



st.divider()

st.subheader("Top Hiring Companies")

top_companies = (
    filtered_jobs
    .dropna(subset=["company"])
    .groupby("company")
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
    salary_distribution = salary_df[
        "salary_midpoint"
    ].value_counts(
        bins=10,
        sort=False
    )

    st.bar_chart(
        salary_distribution
    )

else:
    st.info(
        "Not enough salary data available for the selected jobs."
    )


st.divider()

st.subheader("Job Postings")

display_jobs = filtered_jobs[
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