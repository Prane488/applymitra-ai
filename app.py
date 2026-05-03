import streamlit as st
import pandas as pd
import json
import requests
import os
import re
from datetime import datetime

JOBS_FILE = "jobs.csv"
TRACKER_FILE = "tracker.csv"
REJECTED_FILE = "rejected.csv"
MIN_SCORE = 60

CORE_SKILLS = [
    "kafka", "spark", "aws", "databricks", "python", "sql",
    "airflow", "etl", "pipeline", "streaming", "real-time",
    "snowflake", "glue", "s3", "lambda", "hadoop", "hive"
]


def safe_read_csv(file):
    if os.path.exists(file) and os.path.getsize(file) > 0:
        return pd.read_csv(file)
    return pd.DataFrame()


def row_text(job):
    return " ".join(str(x) for x in job.values()).lower()


def load_profile():
    with open("profile.json", "r", encoding="utf-8") as f:
        return json.load(f)


def extract_job_info(text):
    text_lower = text.lower()
    title = "Data Engineer"
    company = "Unknown"

    patterns = [
        r"company[:\-]\s*([A-Za-z0-9 .&-]+)",
        r"at\s+([A-Za-z0-9 .&-]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            company = match.group(1).strip()[:50]
            break

    location = "Remote"
    if "bengaluru" in text_lower or "bangalore" in text_lower:
        location = "Bengaluru"
    elif "hyderabad" in text_lower:
        location = "Hyderabad"
    elif "india" in text_lower:
        location = "India"

    return company, title, location


def fetch_remoteok_jobs():
    jobs = []
    try:
        res = requests.get("https://remoteok.com/api", timeout=15)
        data = res.json()

        for job in data[1:]:
            jobs.append({
                "company": job.get("company", "Unknown"),
                "title": job.get("position", ""),
                "location": job.get("location", "Remote"),
                "experience": "2-4",
                "salary": "15-25",
                "description": " ".join(job.get("tags", [])),
                "link": job.get("url", ""),
                "source": "RemoteOK"
            })
    except Exception:
        pass

    return pd.DataFrame(jobs)


def load_jobs():
    live_jobs = fetch_remoteok_jobs()
    csv_jobs = safe_read_csv(JOBS_FILE)

    if not csv_jobs.empty and "source" not in csv_jobs.columns:
        csv_jobs["source"] = "Manual"

    jobs = pd.concat([live_jobs, csv_jobs], ignore_index=True)

    if jobs.empty:
        return jobs

    return jobs.drop_duplicates(subset=["company", "title", "link"], keep="first")


def strict_filter(job):
    title = str(job.get("title", "")).lower()
    text = row_text(job)

    blocked_title_words = [
        "senior", "sr.", "sr ", "staff", "principal", "lead",
        "manager", "analyst", "scientist", "intern", "fresher"
    ]

    blocked_text_words = [
        "5+ years", "6+ years", "7+ years", "8+ years",
        "minimum 5 years", "minimum 6 years", "minimum 7 years",
        "java backend", "frontend", "full stack"
    ]

    if "data engineer" not in title:
        return False

    if any(word in title for word in blocked_title_words):
        return False

    if any(word in text for word in blocked_text_words):
        return False

    return True


def get_skill_matches(job):
    text = row_text(job)
    matched = [skill for skill in CORE_SKILLS if skill in text]
    missing = [skill for skill in CORE_SKILLS if skill not in text]
    return matched, missing


def score_job(job):
    text = row_text(job)
    score = 0

    if "data engineer" in text:
        score += 40
    if "kafka" in text:
        score += 20
    if "spark" in text:
        score += 20
    if "aws" in text:
        score += 10
    if "databricks" in text:
        score += 10
    if "streaming" in text or "real-time" in text:
        score += 10
    if "python" in text:
        score += 5
    if "sql" in text:
        score += 5

    return min(score, 100)


def generate_message(job, profile):
    matched, _ = get_skill_matches(job)
    top_skills = ", ".join(matched[:6]) if matched else "data pipelines, SQL, Python"

    return f"""Hi,

I’m {profile['name']}, a Data Engineer with 3+ years of experience building batch and real-time data pipelines.

I noticed this role at {job['company']} involves {top_skills}. My experience aligns well with this because I have worked on Kafka/Spark-based healthcare data pipelines, AWS cloud workflows, and analytics-ready datasets processing {profile['impact']}.

I’m interested in the {job['title']} role and would be happy to share my resume for review.

Thanks,
{profile['name']}
"""


def generate_fit_summary(job):
    matched, missing = get_skill_matches(job)

    return f"""Fit Summary:
- Strong matches: {", ".join(matched[:8]) if matched else "Data Engineer fundamentals"}
- Skills to prepare before interview: {", ".join(missing[:5]) if missing else "None"}
- Best positioning: Real-time healthcare pipeline + Kafka/Spark/AWS + 10M+ records/day
"""


def generate_resume_bullets(job):
    matched, _ = get_skill_matches(job)
    skill_text = ", ".join(matched[:5]) if matched else "Kafka, Spark, AWS, Python, SQL"

    return f"""Resume bullets to emphasize for this job:

• Built scalable batch and real-time data pipelines using {skill_text}, supporting analytics and machine learning use cases.
• Processed high-volume healthcare datasets exceeding 10M+ records/day with focus on data quality, validation, and low-latency performance.
• Designed analytics-ready data models and curated datasets for KPI reporting, BI dashboards, and downstream ML workflows.
• Implemented data validation, schema checks, and error-handling patterns to improve production pipeline reliability.
"""


def save_job(job):
    df = safe_read_csv(JOBS_FILE)
    df = pd.concat([df, pd.DataFrame([job])], ignore_index=True)
    df.to_csv(JOBS_FILE, index=False)


def save_tracker(job, file, status):
    data = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "company": job.get("company", ""),
        "title": job.get("title", ""),
        "location": job.get("location", ""),
        "score": job.get("score", ""),
        "link": job.get("link", ""),
        "status": status
    }

    df = safe_read_csv(file)
    df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
    df.to_csv(file, index=False)


st.set_page_config(page_title="ApplyMitra AI", layout="wide")
st.title("ApplyMitra AI - Data Engineer Job Copilot")

profile = load_profile()

st.sidebar.header("Paste LinkedIn / Naukri / Instahyre Job")

jd = st.sidebar.text_area("Paste full job description")
job_link = st.sidebar.text_input("Job link")

if st.sidebar.button("Add Job"):
    if jd.strip():
        company, title, location = extract_job_info(jd)

        new_job = {
            "company": company,
            "title": title,
            "location": location,
            "experience": "2-4",
            "salary": "15-25",
            "description": jd,
            "link": job_link if job_link else f"manual-{datetime.now().timestamp()}",
            "source": "Manual"
        }

        save_job(new_job)
        st.sidebar.success("Job added. Refresh page.")
    else:
        st.sidebar.error("Paste job description first.")

jobs = load_jobs()

if jobs.empty:
    st.warning("No jobs found. Paste a job description from LinkedIn/Naukri.")
    st.stop()

applied_df = safe_read_csv(TRACKER_FILE)
rejected_df = safe_read_csv(REJECTED_FILE)

applied_links = applied_df["link"].astype(str).tolist() if not applied_df.empty and "link" in applied_df.columns else []
rejected_links = rejected_df["link"].astype(str).tolist() if not rejected_df.empty and "link" in rejected_df.columns else []

results = []

for _, row in jobs.iterrows():
    job = row.to_dict()

    if str(job.get("link", "")) in applied_links or str(job.get("link", "")) in rejected_links:
        continue

    if strict_filter(job):
        job["score"] = score_job(job)

        if job["score"] >= MIN_SCORE:
            results.append(job)

df = pd.DataFrame(results)

if df.empty:
    st.warning("No matching Data Engineer jobs found with score 60+. Paste better job descriptions or lower filters later.")
else:
    df = df.sort_values(by="score", ascending=False)

    st.subheader("Best Matches")

    for _, row in df.iterrows():
        job = row.to_dict()

        with st.expander(f"{job['company']} - {job['title']} | Score: {job['score']}"):
            st.write("Location:", job.get("location", ""))
            st.write("Source:", job.get("source", ""))
            st.write("Link:", job.get("link", ""))

            matched, missing = get_skill_matches(job)

            st.markdown("### Skill Match")
            st.write("Matched:", ", ".join(matched[:10]) if matched else "No strong skill match")
            st.write("Prepare:", ", ".join(missing[:6]))

            st.markdown("### Tailored Recruiter Message")
            message = generate_message(job, profile)
            st.code(message)

            st.markdown(f"[👉 Open Job Application]({job.get('link', '')})")

            st.markdown("### Fit Summary")
            st.code(generate_fit_summary(job))

            st.markdown("### Resume Bullets for This Job")
            st.code(generate_resume_bullets(job))

            col1, col2, col3 = st.columns(3)

            with col1:
                st.text_area("Copy Message", message, height=120, key="msg_" + str(job.get("link", "")))

            with col2:
                if st.button("Mark Applied", key="apply_" + str(job.get("link", ""))):
                    save_tracker(job, TRACKER_FILE, "Applied")
                    st.success("Saved. Refresh page.")

            with col3:
                if st.button("Reject", key="reject_" + str(job.get("link", ""))):
                    save_tracker(job, REJECTED_FILE, "Rejected")
                    st.success("Rejected. Refresh page.")

st.subheader("Applied Jobs Tracker")
if applied_df.empty:
    st.info("No applications saved yet.")
else:
    st.dataframe(applied_df, use_container_width=True)

st.subheader("Rejected Jobs")
if rejected_df.empty:
    st.info("No rejected jobs yet.")
else:
    st.dataframe(rejected_df, use_container_width=True)