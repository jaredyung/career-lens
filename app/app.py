import sys
from html import escape
from pathlib import Path
from urllib.parse import urlparse

import altair as alt
import streamlit as st


# Support `streamlit run /path/to/app/app.py` from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from database import DB_PATH, get_connection
from roles import ROLES


@st.cache_data
def load_jobs(database_modified_ns):
    """Cache by database modification time so ingestion invalidates old results."""
    with get_connection(read_only=True) as conn:
        return conn.execute(
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


# UI helpers keep presentation separate from the source data and calculations.
ACCENT = "#28776D"


def apply_styles():
    # Prefer stable Streamlit test IDs and native bordered containers over
    # generated CSS class names. No external fonts or frontend assets required.
    st.markdown("""
    <style>
    .stApp { background: #F6F8FA; color: #172B3A; }
    .block-container { max-width: 1440px; padding-top: 4rem; padding-bottom: 3rem; }
    [data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E2E8EE; }
    h1, h2, h3 { letter-spacing: -.035em; color: #172B3A; }
    h1 { font-size: 2.8rem !important; font-weight: 750 !important; }
    h2 { font-size: 1.55rem !important; }
    h3 { font-size: 1.1rem !important; }
    [class*="st-key-panel_"] {
        background: #FFFFFF; border-color: #E2E8EE !important; border-radius: 14px;
    }
    [data-testid="stMetric"] { padding: .35rem .15rem; }
    [data-testid="stMetricValue"] { font-size: clamp(1.5rem, 2.2vw, 2.2rem); font-weight: 650; }
    [data-testid="stMetricLabel"] { color: #566775; }
    .eyebrow { color: #28776D; font-size: .73rem; font-weight: 750;
        letter-spacing: .13em; text-transform: uppercase; margin-bottom: .45rem; }
    .hero-subtitle { color: #566775; font-size: 1.05rem; max-width: 740px; }
    .source-badge { display: inline-block; background: #E8F2EF; color: #245E56;
        padding: .35rem .7rem; border-radius: 6px; font-size: .75rem; font-weight: 600; }
    .section-heading { margin-top: 1.9rem; margin-bottom: .15rem; }
    .comparison-title { font-size: 1.35rem; font-weight: 700; margin: .5rem 0 1rem; }
    [data-testid="stCaptionContainer"] { color: #60717E; }
    /* The table toolbar extends above its frame; keep it visible. */
    [data-testid="stDataFrame"] { border-radius: 10px; overflow: visible; }
    [data-testid="stDataFrame"] [data-testid="stElementToolbar"] {
        opacity: 1; z-index: 10;
    }
    @media (max-width: 700px) {
        .block-container { padding-top: 4rem; }
        h1 { font-size: 2.2rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)


def section(title, subtitle):
    st.markdown(f'<h2 class="section-heading">{escape(title)}</h2>', unsafe_allow_html=True)
    st.caption(subtitle)


def salary_data(frame):
    result = frame.dropna(subset=["salary_min", "salary_max"]).copy()
    result["salary_midpoint"] = (result["salary_min"] + result["salary_max"]) / 2
    return result


def money(value):
    return "N/A" if value is None else f"${value:,.0f}"


def get_job_summary(frame):
    salaries = salary_data(frame)
    return (
        len(frame), frame["company"].nunique(),
        None if salaries.empty else salaries["salary_midpoint"].mean(),
        None if salaries.empty else salaries["salary_midpoint"].median(),
    )


def metric_cards(items):
    for column, (label, value, note) in zip(st.columns(len(items)), items):
        with column, st.container(border=True, key=f"panel_metric_{label}"):
            st.metric(label, value)
            st.caption(note)


def count_chart(frame, field, label, limit=None):
    counts = (frame.dropna(subset=[field]).groupby(field).size()
              .reset_index(name="job_count").sort_values("job_count", ascending=False))
    if limit:
        counts = counts.head(limit)
    if counts.empty:
        st.info(f"No {label.lower()} data available for this selection.")
        return
    chart = alt.Chart(counts).mark_bar(color=ACCENT, cornerRadiusEnd=3, size=18).encode(
        x=alt.X("job_count:Q", title="Sampled postings", axis=alt.Axis(tickMinStep=1)),
        y=alt.Y(f"{field}:N", title=None, sort="-x", axis=alt.Axis(labelLimit=210)),
        tooltip=[alt.Tooltip(f"{field}:N", title=label),
                 alt.Tooltip("job_count:Q", title="Postings", format=",")],
    ).properties(height=max(220, len(counts) * 30)).configure_view(strokeWidth=0)
    st.altair_chart(chart, width="stretch")


def valid_job_url(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = urlparse(value)
        return value if parsed.scheme in ("http", "https") and parsed.netloc else None
    except ValueError:
        return None


def job_table(frame, key):
    columns = ["title", "company", "location", "role_category", "created",
               "salary_min", "salary_max", "job_url"]
    display = frame[columns].copy()
    # Invalid historical links are shown as missing, never as broken navigation.
    display["job_url"] = display["job_url"].map(valid_job_url)
    st.dataframe(
        display, key=key, width="stretch", hide_index=True,
        height=min(480, 40 + 35 * len(display)),
        column_config={
            "title": st.column_config.TextColumn("Job title", width="large"),
            "company": st.column_config.TextColumn("Company", width="medium"),
            "location": st.column_config.TextColumn("Location", width="medium"),
            "role_category": "Career path",
            "created": st.column_config.DatetimeColumn("Posted", format="MMM D, YYYY"),
            "salary_min": st.column_config.NumberColumn("Estimated salary · min", format="$%d"),
            "salary_max": st.column_config.NumberColumn("Estimated salary · max", format="$%d"),
            "job_url": st.column_config.LinkColumn("Posting", display_text="View posting ↗"),
        },
    )
    missing = display["job_url"].isna().sum()
    if missing:
        st.caption(f"Original posting links are unavailable for {missing:,} rows in this view.")


def reset_filters():
    for key, value in {"filter_title": "", "filter_company": "All",
                       "filter_location": "", "filter_role": "All", "filter_salary": 0}.items():
        st.session_state[key] = value


def methodology():
    st.caption("Adzuna sample · These postings are not a complete census of the labor market.")
    with st.expander("About the Data · Methodology"):
        st.markdown("""
        - CareerLens analyzes a sampled set of job postings retrieved through the Adzuna API.
        - Career paths use title-based classification rules.
        - Salaries are estimates and may not represent employer-posted compensation.
          Average and median salaries use the midpoint of each available salary range;
          postings missing either endpoint are excluded from these calculations.
        - Duplicate source records are prevented using Adzuna job IDs.
        - Postings with different source IDs are retained, even when their content is similar.
        - All analytics on this page respect the sidebar filters, including role comparisons
          and company intelligence. Counts describe this sample, not total market demand.
        """)


def main():
    st.set_page_config(page_title="CareerLens · Labor Market Intelligence", page_icon="🔎", layout="wide")
    apply_styles()
    if not DB_PATH.exists():
        st.info("Run python src/ingest.py from the project folder to create the dataset.")
        return
    jobs = load_jobs(DB_PATH.stat().st_mtime_ns)

    with st.sidebar:
        st.markdown('<div class="eyebrow">CareerLens / Explore</div>', unsafe_allow_html=True)
        st.header("Refine your view")
        st.caption("Filters apply to every section.")
        title_filter = st.text_input("Job title contains", placeholder="e.g. data engineer", key="filter_title")
        company_options = ["All"] + sorted(jobs["company"].dropna().unique().tolist())
        company_filter = st.selectbox("Company", company_options, key="filter_company")
        location_filter = st.text_input("Location contains", placeholder="e.g. Chicago", key="filter_location")
        role_filter = st.selectbox("Role", ["All"] + ROLES + ["Other"], key="filter_role")
        salary_filter = st.number_input("Minimum salary", min_value=0, step=5000,
                                       key="filter_salary", help="Keeps postings whose estimated maximum salary meets this amount.")
        st.button("Reset filters", on_click=reset_filters, width="stretch")
        st.divider()
        st.caption("SOURCE / ADZUNA")
        st.caption("A snapshot of data careers. Sampled postings, estimated salaries, practical comparisons.")

    filtered_jobs = jobs.copy()
    if title_filter:
        filtered_jobs = filtered_jobs[filtered_jobs["title"].str.contains(title_filter, case=False, na=False, regex=False)]
    if company_filter != "All":
        filtered_jobs = filtered_jobs[filtered_jobs["company"] == company_filter]
    if location_filter:
        filtered_jobs = filtered_jobs[filtered_jobs["location"].str.contains(location_filter, case=False, na=False, regex=False)]
    if role_filter != "All":
        filtered_jobs = filtered_jobs[filtered_jobs["role_category"] == role_filter]
    if salary_filter > 0:
        filtered_jobs = filtered_jobs[filtered_jobs["salary_max"].fillna(0) >= salary_filter]

    st.markdown('<div class="eyebrow">Labor-market intelligence / Data careers</div>', unsafe_allow_html=True)
    st.title("CareerLens")
    st.markdown('<p class="hero-subtitle">Explore the roles, employers, and estimated salaries shaping your next career move.</p>', unsafe_allow_html=True)
    st.markdown('<span class="source-badge">SAMPLED ADZUNA DATASET</span>', unsafe_allow_html=True)
    st.caption(f"{len(filtered_jobs):,} of {len(jobs):,} sampled postings in view · All sections follow your filters")
    if filtered_jobs.empty:
        st.info("No postings match your filters. Broaden your search or reset the filters to explore the sample.")
        methodology()
        return

    total, companies, average, median = get_job_summary(filtered_jobs)
    salaries = salary_data(filtered_jobs)
    section("Market overview", "A focused snapshot of the postings in your current view.")
    metric_cards([
        ("Jobs Analyzed", f"{total:,}", "Sampled postings in view"),
        ("Companies", f"{companies:,}", "Distinct hiring employers"),
        ("Estimated Average Salary", money(average), f"Based on {len(salaries):,} salary ranges"),
        ("Estimated Median Salary", money(median), "Midpoint of available ranges"),
    ])
    left, right = st.columns(2)
    with left, st.container(border=True, key="panel_roles"):
        st.subheader("Career paths in the sample")
        st.caption("Role mix in sampled postings")
        count_chart(filtered_jobs, "role_category", "Career path")
    with right, st.container(border=True, key="panel_employers"):
        st.subheader("Top hiring companies")
        st.caption("Ten employers with the most postings in this view")
        count_chart(filtered_jobs, "company", "Company", 10)

    section("Role comparison", "Compare career paths within your filtered sample. A role excluded by your filters will show no postings.")
    for index, column in enumerate(st.columns(2)):
        with column, st.container(border=True, key=f"panel_compare_{index}"):
            role = st.selectbox("First role" if index == 0 else "Second role", ROLES, index=index, key=f"compare_{index}")
            st.markdown(f'<div class="comparison-title">{escape(role)}</div>', unsafe_allow_html=True)
            role_jobs = filtered_jobs[filtered_jobs["role_category"] == role]
            count, employers, avg, med = get_job_summary(role_jobs)
            a, b = st.columns(2)
            a.metric("Job Postings", f"{count:,}")
            b.metric("Hiring Companies", f"{employers:,}")
            st.divider()
            a, b = st.columns(2)
            a.metric("Estimated Average Salary", money(avg))
            b.metric("Estimated Median Salary", money(med))
            st.caption(f"{len(salary_data(role_jobs)):,} postings with complete salary ranges" if count else "No postings for this role match the current filters.")

    section("Company intelligence", "A closer look at an employer’s presence in your filtered sample.")
    with st.container(border=True, key="panel_company"):
        options = sorted(filtered_jobs["company"].dropna().unique().tolist())
        if not options:
            st.info("No company names are available in this selection.")
        else:
            if st.session_state.get("company_detail") not in options:
                st.session_state["company_detail"] = options[0]
            selected = st.selectbox("Select a company", options, key="company_detail")
            company_jobs = filtered_jobs[filtered_jobs["company"] == selected]
            count, _, avg, med = get_job_summary(company_jobs)
            for col, label, value in zip(st.columns(3), ["Job Postings", "Role Categories", "Locations"],
                                         [count, company_jobs["role_category"].nunique(), company_jobs["location"].nunique()]):
                col.metric(label, f"{value:,}")
            a, b = st.columns(2)
            a.metric("Estimated Average Salary", money(avg))
            b.metric("Estimated Median Salary", money(med))
            st.divider()
            a, b = st.columns(2)
            with a:
                st.subheader("Role mix in sampled postings")
                count_chart(company_jobs, "role_category", "Career path")
            with b:
                st.subheader("Top hiring locations")
                count_chart(company_jobs, "location", "Location", 10)
            with st.expander(f"Explore {len(company_jobs):,} company postings"):
                job_table(company_jobs, "company_jobs")

    section("Salary analysis", "Estimated compensation across the postings in your view.")
    a, b = st.columns([2, 1])
    with a, st.container(border=True, key="panel_salary"):
        st.subheader("Salary distribution")
        if salaries.empty:
            st.info("No complete salary ranges are available for these filters.")
        else:
            # Group salary midpoints into ten equal-width bins.
            bins = salaries["salary_midpoint"].value_counts(bins=10, sort=False)
            distribution = bins.rename_axis("range").reset_index(name="postings")
            distribution["lower"] = distribution["range"].map(lambda x: x.left).astype(float)
            distribution["upper"] = distribution["range"].map(lambda x: x.right).astype(float)
            chart = alt.Chart(distribution).mark_bar(color=ACCENT, binSpacing=2).encode(
                x=alt.X("lower:Q", bin="binned", title="Estimated salary midpoint", axis=alt.Axis(format="$~s")),
                x2="upper:Q", y=alt.Y("postings:Q", title="Sampled postings", axis=alt.Axis(tickMinStep=1)),
                tooltip=[alt.Tooltip("lower:Q", title="From", format="$,.0f"),
                         alt.Tooltip("upper:Q", title="To", format="$,.0f"), alt.Tooltip("postings:Q", title="Postings")],
            ).properties(height=260).configure_view(strokeWidth=0)
            st.altair_chart(chart, width="stretch")
    with b, st.container(border=True, key="panel_salary_notes"):
        st.subheader("Reading these estimates")
        st.metric("Postings with salary ranges", f"{len(salaries):,} / {total:,}")
        st.caption(f"{len(salaries) / total:.0%} of the current view has both salary endpoints.")
        st.markdown("Each posting contributes the midpoint of its estimated minimum and maximum salary.")
        st.caption("These figures describe the selected sample. They may differ from employer-posted compensation.")

    section("Job explorer", "Browse matching postings, compare estimated ranges, and open the original listing.")
    with st.container(border=True, key="panel_jobs"):
        st.subheader(f"{total:,} matching postings")
        st.caption("Most recent first · Click a column heading to sort")
        job_table(filtered_jobs, "all_jobs")
    st.divider()
    methodology()


if __name__ == "__main__":
    main()
