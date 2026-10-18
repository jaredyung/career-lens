from pathlib import Path

import duckdb
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "careerlens.duckdb"


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
            description,
            created,
            salary_min,
            salary_max,
            category,
            role_category,
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
st.caption(
    "Explore salary, hiring company, and role-level insights from Adzuna job postings."
)


# -------------------------
# Load Data
# -------------------------

jobs = load_jobs()


# -------------------------
# Sidebar Filters
# -------------------------

st.sidebar.header("Filters")

title_filter = st.sidebar.text_input(
    "Job title contains",
    placeholder="e.g. data engineer",
)

company_options = ["All"] + sorted(
    jobs["company"]
    .dropna()
    .unique()
    .tolist()
)

company_filter = st.sidebar.selectbox(
    "Company",
    company_options,
)

location_filter = st.sidebar.text_input(
    "Location contains",
    placeholder="e.g. Chicago",
)

role_options = [
    "All",
    "Data Scientist",
    "Data Engineer",
    "Data Analyst",
    "Machine Learning Engineer",
    "Analytics Engineer",
    "Other",
]

role_filter = st.sidebar.selectbox(
    "Role",
    role_options,
)

salary_filter = st.sidebar.number_input(
    "Minimum salary",
    min_value=0,
    value=0,
    step=5000,
)


# -------------------------
# Apply Filters
# -------------------------

filtered_jobs = jobs.copy()

if title_filter:
    filtered_jobs = filtered_jobs[
        filtered_jobs["title"].str.contains(
            title_filter,
            case=False,
            na=False,
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
            na=False,
        )
    ]

if role_filter != "All":
    filtered_jobs = filtered_jobs[
        filtered_jobs["role_category"] == role_filter
    ]

if salary_filter > 0:
    filtered_jobs = filtered_jobs[
        filtered_jobs["salary_max"].fillna(0) >= salary_filter
    ]


# -------------------------
# Handle Empty Results
# -------------------------

if filtered_jobs.empty:
    st.warning(
        "No jobs match the selected filters. Try adjusting your search."
    )
    st.stop()


# -------------------------
# Summary Metrics
# -------------------------

total_jobs = len(filtered_jobs)

total_companies = filtered_jobs["company"].nunique()

salary_df = filtered_jobs.dropna(
    subset=["salary_min", "salary_max"]
).copy()

if not salary_df.empty:
    salary_df["salary_midpoint"] = (
        salary_df["salary_min"]
        + salary_df["salary_max"]
    ) / 2

    avg_salary = salary_df["salary_midpoint"].mean()
    median_salary = salary_df["salary_midpoint"].median()
else:
    avg_salary = None
    median_salary = None


col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Jobs Analyzed",
        f"{total_jobs:,}",
    )

with col2:
    st.metric(
        "Companies",
        f"{total_companies:,}",
    )

with col3:
    if avg_salary is not None:
        st.metric(
            "Estimated Average Salary",
            f"${avg_salary:,.0f}",
        )
    else:
        st.metric(
            "Estimated Average Salary",
            "N/A",
        )

with col4:
    if median_salary is not None:
        st.metric(
            "Estimated Median Salary",
            f"${median_salary:,.0f}",
        )
    else:
        st.metric(
            "Estimated Median Salary",
            "N/A",
        )


# -------------------------
# Dataset Composition
# -------------------------

st.divider()

st.subheader("Dataset Composition")

role_distribution = (
    filtered_jobs
    .dropna(subset=["role_category"])
    .groupby("role_category")
    .size()
    .reset_index(name="job_count")
    .sort_values(
        "job_count",
        ascending=False,
    )
)

if not role_distribution.empty:
    st.bar_chart(
        role_distribution,
        x="role_category",
        y="job_count",
    )
else:
    st.info(
        "No role classification data available."
    )


# -------------------------
# Top Hiring Companies
# -------------------------

st.divider()

st.subheader("Top Hiring Companies")

top_companies = (
    filtered_jobs
    .dropna(subset=["company"])
    .groupby("company")
    .size()
    .reset_index(name="job_count")
    .sort_values(
        "job_count",
        ascending=False,
    )
    .head(10)
)

if not top_companies.empty:
    st.bar_chart(
        top_companies,
        x="company",
        y="job_count",
    )
else:
    st.info(
        "No company data available for the selected jobs."
    )


# -------------------------
# Role Comparison
# -------------------------

st.divider()

st.subheader("Compare Roles")

comparison_roles = [
    "Data Scientist",
    "Data Engineer",
    "Data Analyst",
    "Machine Learning Engineer",
    "Analytics Engineer",
]

compare_col1, compare_col2 = st.columns(2)

with compare_col1:
    role_1 = st.selectbox(
        "First role",
        comparison_roles,
        index=0,
    )

with compare_col2:
    role_2 = st.selectbox(
        "Second role",
        comparison_roles,
        index=1,
    )


def get_role_jobs(role_name):
    return jobs[
        jobs["role_category"] == role_name
    ].copy()


def get_role_summary(role_jobs):
    job_count = len(role_jobs)
    company_count = role_jobs["company"].nunique()

    salary_data = role_jobs.dropna(
        subset=["salary_min", "salary_max"]
    ).copy()

    if not salary_data.empty:
        salary_data["salary_midpoint"] = (
            salary_data["salary_min"]
            + salary_data["salary_max"]
        ) / 2

        avg_salary = salary_data["salary_midpoint"].mean()
        median_salary = salary_data["salary_midpoint"].median()
    else:
        avg_salary = None
        median_salary = None

    return (
        job_count,
        company_count,
        avg_salary,
        median_salary,
    )


role_1_jobs = get_role_jobs(role_1)
role_2_jobs = get_role_jobs(role_2)

(
    role_1_count,
    role_1_companies,
    role_1_avg_salary,
    role_1_median_salary,
) = get_role_summary(role_1_jobs)

(
    role_2_count,
    role_2_companies,
    role_2_avg_salary,
    role_2_median_salary,
) = get_role_summary(role_2_jobs)


metric_col1, metric_col2 = st.columns(2)

with metric_col1:
    st.markdown(f"### {role_1}")

    st.metric(
        "Job Postings",
        f"{role_1_count:,}",
    )

    st.metric(
        "Hiring Companies",
        f"{role_1_companies:,}",
    )

    if role_1_avg_salary is not None:
        st.metric(
            "Average Salary",
            f"${role_1_avg_salary:,.0f}",
        )
    else:
        st.metric(
            "Average Salary",
            "N/A",
        )

    if role_1_median_salary is not None:
        st.metric(
            "Median Salary",
            f"${role_1_median_salary:,.0f}",
        )
    else:
        st.metric(
            "Median Salary",
            "N/A",
        )

with metric_col2:
    st.markdown(f"### {role_2}")

    st.metric(
        "Job Postings",
        f"{role_2_count:,}",
    )

    st.metric(
        "Hiring Companies",
        f"{role_2_companies:,}",
    )

    if role_2_avg_salary is not None:
        st.metric(
            "Average Salary",
            f"${role_2_avg_salary:,.0f}",
        )
    else:
        st.metric(
            "Average Salary",
            "N/A",
        )

    if role_2_median_salary is not None:
        st.metric(
            "Median Salary",
            f"${role_2_median_salary:,.0f}",
        )
    else:
        st.metric(
            "Median Salary",
            "N/A",
        )


# -------------------------
# Company Intelligence
# -------------------------

st.divider()

st.subheader("Company Intelligence")

st.caption(
    "Explore hiring patterns, role mix, locations, and estimated compensation by company."
)

company_intelligence_options = sorted(
    jobs["company"]
    .dropna()
    .unique()
    .tolist()
)

selected_company = st.selectbox(
    "Select a company",
    company_intelligence_options,
)

company_jobs = jobs[
    jobs["company"] == selected_company
].copy()


# -------------------------
# Company Summary Metrics
# -------------------------

company_job_count = len(company_jobs)

company_role_count = (
    company_jobs["role_category"]
    .dropna()
    .nunique()
)

company_location_count = (
    company_jobs["location"]
    .dropna()
    .nunique()
)

company_salary_data = company_jobs.dropna(
    subset=["salary_min", "salary_max"]
).copy()

if not company_salary_data.empty:
    company_salary_data["salary_midpoint"] = (
        company_salary_data["salary_min"]
        + company_salary_data["salary_max"]
    ) / 2

    company_avg_salary = (
        company_salary_data["salary_midpoint"].mean()
    )

    company_median_salary = (
        company_salary_data["salary_midpoint"].median()
    )
else:
    company_avg_salary = None
    company_median_salary = None


company_col1, company_col2, company_col3, company_col4 = st.columns(4)

with company_col1:
    st.metric(
        "Job Postings",
        f"{company_job_count:,}",
    )

with company_col2:
    st.metric(
        "Role Categories",
        f"{company_role_count:,}",
    )

with company_col3:
    st.metric(
        "Locations",
        f"{company_location_count:,}",
    )

with company_col4:
    if company_avg_salary is not None:
        st.metric(
            "Estimated Average Salary",
            f"${company_avg_salary:,.0f}",
        )
    else:
        st.metric(
            "Estimated Average Salary",
            "N/A",
        )


# -------------------------
# Company Role Mix
# -------------------------

company_left, company_right = st.columns(2)

with company_left:
    st.markdown("#### Role Mix")

    company_roles = (
        company_jobs
        .dropna(subset=["role_category"])
        .groupby("role_category")
        .size()
        .reset_index(name="job_count")
        .sort_values(
            "job_count",
            ascending=False,
        )
    )

    if not company_roles.empty:
        st.bar_chart(
            company_roles,
            x="role_category",
            y="job_count",
        )
    else:
        st.info(
            "No role data available for this company."
        )


# -------------------------
# Company Locations
# -------------------------

with company_right:
    st.markdown("#### Top Hiring Locations")

    company_locations = (
        company_jobs
        .dropna(subset=["location"])
        .groupby("location")
        .size()
        .reset_index(name="job_count")
        .sort_values(
            "job_count",
            ascending=False,
        )
        .head(10)
    )

    if not company_locations.empty:
        st.bar_chart(
            company_locations,
            x="location",
            y="job_count",
        )
    else:
        st.info(
            "No location data available for this company."
        )


# -------------------------
# Company Salary Details
# -------------------------

st.markdown("#### Compensation")

salary_col1, salary_col2 = st.columns(2)

with salary_col1:
    if company_avg_salary is not None:
        st.metric(
            "Estimated Average Salary",
            f"${company_avg_salary:,.0f}",
        )
    else:
        st.metric(
            "Estimated Average Salary",
            "N/A",
        )

with salary_col2:
    if company_median_salary is not None:
        st.metric(
            "Estimated Median Salary",
            f"${company_median_salary:,.0f}",
        )
    else:
        st.metric(
            "Estimated Median Salary",
            "N/A",
        )


# -------------------------
# Company Job Listings
# -------------------------

with st.expander(
    f"View {selected_company} job postings"
):
    company_display_jobs = company_jobs[
        [
            "title",
            "role_category",
            "location",
            "created",
            "salary_min",
            "salary_max",
            "job_url",
        ]
    ].copy()

    company_display_jobs = company_display_jobs.rename(
        columns={
            "title": "Title",
            "role_category": "Role",
            "location": "Location",
            "created": "Posted",
            "salary_min": "Minimum Salary",
            "salary_max": "Maximum Salary",
            "job_url": "Job Link",
        }
    )

    st.dataframe(
        company_display_jobs,
        width="stretch",
        hide_index=True,
        column_config={
            "Minimum Salary": st.column_config.NumberColumn(
                format="$%.0f"
            ),
            "Maximum Salary": st.column_config.NumberColumn(
                format="$%.0f"
            ),
            "Job Link": st.column_config.LinkColumn(
                "Job Link",
                display_text="View Posting",
            ),
        },
    )

# -------------------------
# Salary Distribution
# -------------------------

st.divider()

st.subheader("Salary Distribution")

if not salary_df.empty:
    salary_distribution = (
        salary_df["salary_midpoint"]
        .value_counts(
            bins=10,
            sort=False,
        )
    )

    st.bar_chart(
        salary_distribution
    )
else:
    st.info(
        "Not enough salary data available for the selected jobs."
    )


# -------------------------
# About the Data
# -------------------------

st.divider()

st.subheader("About the Data")

st.markdown(
    """
    CareerLens analyzes a sampled set of job postings retrieved through the Adzuna API.

    - Job postings are classified into data career categories using title-based rules.
    - Salary values are treated as estimates and may not always represent employer-posted compensation.
    - The dataset is a sample of available postings, not a complete census of the labor market.
    - Duplicate source records are prevented using Adzuna job IDs.
    - Similar postings with different IDs are retained when their descriptions or compensation differ.
    """
)

# -------------------------
# Job Postings Table
# -------------------------

st.divider()

st.subheader("Job Postings")

display_jobs = filtered_jobs[
    [
        "title",
        "company",
        "location",
        "role_category",
        "created",
        "salary_min",
        "salary_max",
        "job_url",
    ]
].copy()

display_jobs = display_jobs.rename(
    columns={
        "title": "Title",
        "company": "Company",
        "location": "Location",
        "role_category": "Role",
        "created": "Posted",
        "salary_min": "Minimum Salary",
        "salary_max": "Maximum Salary",
        "job_url": "Job Link",
    }
)

st.dataframe(
    display_jobs,
    width="stretch",
    hide_index=True,
    column_config={
        "Minimum Salary": st.column_config.NumberColumn(
            format="$%.0f"
        ),
        "Maximum Salary": st.column_config.NumberColumn(
            format="$%.0f"
        ),
        "Job Link": st.column_config.LinkColumn(
            "Job Link",
            display_text="View Posting",
        ),
    },
)