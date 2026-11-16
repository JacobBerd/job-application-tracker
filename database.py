"""Database connection and query functions for the Job Application Tracker."""

import json
import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_db():
    """Open a new connection to the job_tracker database using settings from .env."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "job_tracker"),
    )


def query_all(sql, params=()):
    """Run a SELECT and return every row as a dict."""
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        conn.close()


def query_one(sql, params=()):
    """Run a SELECT and return the first row as a dict, or None."""
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    """Run an INSERT/UPDATE/DELETE, commit it, and return the new row id (for inserts)."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def parse_json(value, default=None):
    """Convert a JSON column value (str, bytes, or already-parsed) into Python data."""
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def to_json(data):
    """Serialize Python data for a JSON column (None stays NULL)."""
    return None if data is None else json.dumps(data)


def split_skills(text):
    """Turn 'Python, SQL\\nFlask' into ['Python', 'SQL', 'Flask'], dropping blanks and duplicates."""
    skills, seen = [], set()
    for part in (text or "").replace("\n", ",").split(","):
        skill = part.strip()
        if skill and skill.lower() not in seen:
            seen.add(skill.lower())
            skills.append(skill)
    return skills


def _insert(table, fields, data):
    """Insert the given whitelisted fields from data into table; return the new id."""
    columns = ", ".join(fields)
    placeholders = ", ".join(["%s"] * len(fields))
    values = tuple(data.get(field) for field in fields)
    return execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values)


def _update(table, key, key_value, fields, data):
    """Update the given whitelisted fields of one row identified by key."""
    assignments = ", ".join(f"{field} = %s" for field in fields)
    values = tuple(data.get(field) for field in fields) + (key_value,)
    execute(f"UPDATE {table} SET {assignments} WHERE {key} = %s", values)


# ---------------------------------------------------------------
# Companies
# ---------------------------------------------------------------
COMPANY_FIELDS = ("company_name", "industry", "website", "city", "state", "notes")


def get_companies(search=None):
    """All companies with their job and contact counts, optionally filtered by a search term."""
    sql = """
        SELECT c.*,
               (SELECT COUNT(*) FROM jobs j WHERE j.company_id = c.company_id) AS job_count,
               (SELECT COUNT(*) FROM contacts ct WHERE ct.company_id = c.company_id) AS contact_count
        FROM companies c
    """
    params = ()
    if search:
        sql += """ WHERE c.company_name LIKE %s OR c.industry LIKE %s
                   OR c.city LIKE %s OR c.state LIKE %s"""
        params = (f"%{search}%",) * 4
    sql += " ORDER BY c.company_name"
    return query_all(sql, params)


def get_company(company_id):
    return query_one("SELECT * FROM companies WHERE company_id = %s", (company_id,))


def get_company_options():
    """Minimal id/name list for dropdown menus."""
    return query_all("SELECT company_id, company_name FROM companies ORDER BY company_name")


def add_company(data):
    return _insert("companies", COMPANY_FIELDS, data)


def update_company(company_id, data):
    _update("companies", "company_id", company_id, COMPANY_FIELDS, data)


def delete_company(company_id):
    execute("DELETE FROM companies WHERE company_id = %s", (company_id,))


# ---------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------
JOB_TYPES = ("Full-time", "Part-time", "Contract", "Internship")
JOB_FIELDS = (
    "company_id", "job_title", "job_type", "salary_min", "salary_max",
    "job_url", "date_posted", "requirements",
)
JOB_SELECT = """
    SELECT j.*, c.company_name,
           (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS application_count
    FROM jobs j
    JOIN companies c ON c.company_id = j.company_id
"""


def _with_requirements(job):
    """Parse the requirements JSON and expose its skills list as job['skills']."""
    requirements = parse_json(job.get("requirements"), {})
    if not isinstance(requirements, dict):
        requirements = {}
    skills = requirements.get("skills")
    job["requirements"] = requirements
    job["skills"] = [str(s) for s in skills] if isinstance(skills, list) else []
    return job


def _job_values(data):
    return {**data, "requirements": to_json(data.get("requirements"))}


def get_jobs(company_id=None, job_type=None, search=None):
    conditions, params = [], []
    if company_id:
        conditions.append("j.company_id = %s")
        params.append(company_id)
    if job_type:
        conditions.append("j.job_type = %s")
        params.append(job_type)
    if search:
        conditions.append("(j.job_title LIKE %s OR c.company_name LIKE %s)")
        params += [f"%{search}%"] * 2
    sql = JOB_SELECT
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY j.date_posted DESC, j.job_title"
    return [_with_requirements(job) for job in query_all(sql, tuple(params))]


def get_job(job_id):
    job = query_one(JOB_SELECT + " WHERE j.job_id = %s", (job_id,))
    return _with_requirements(job) if job else None


def get_job_options():
    """Minimal list for dropdowns, labelled 'Title @ Company'."""
    return query_all("""
        SELECT j.job_id, j.job_title, c.company_name
        FROM jobs j JOIN companies c ON c.company_id = j.company_id
        ORDER BY c.company_name, j.job_title
    """)


def add_job(data):
    return _insert("jobs", JOB_FIELDS, _job_values(data))


def update_job(job_id, data):
    _update("jobs", "job_id", job_id, JOB_FIELDS, _job_values(data))


def delete_job(job_id):
    execute("DELETE FROM jobs WHERE job_id = %s", (job_id,))


# ---------------------------------------------------------------
# Applications
# ---------------------------------------------------------------
APPLICATION_STATUSES = ("Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn")
APPLICATION_FIELDS = (
    "job_id", "application_date", "status", "resume_version",
    "cover_letter_sent", "interview_data",
)
APPLICATION_SELECT = """
    SELECT a.*, j.job_title, j.company_id, c.company_name
    FROM applications a
    JOIN jobs j ON j.job_id = a.job_id
    JOIN companies c ON c.company_id = j.company_id
"""


def _with_interviews(application):
    """Parse interview_data JSON and expose its rounds list as application['rounds']."""
    interview_data = parse_json(application.get("interview_data"), {})
    if not isinstance(interview_data, dict):
        interview_data = {}
    rounds = interview_data.get("rounds")
    application["interview_data"] = interview_data
    application["rounds"] = rounds if isinstance(rounds, list) else []
    application["cover_letter_sent"] = bool(application.get("cover_letter_sent"))
    return application


def _application_values(data):
    return {**data, "interview_data": to_json(data.get("interview_data"))}


def get_applications(status=None, job_id=None, search=None):
    conditions, params = [], []
    if status:
        conditions.append("a.status = %s")
        params.append(status)
    if job_id:
        conditions.append("a.job_id = %s")
        params.append(job_id)
    if search:
        conditions.append("(j.job_title LIKE %s OR c.company_name LIKE %s)")
        params += [f"%{search}%"] * 2
    sql = APPLICATION_SELECT
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY a.application_date DESC, a.application_id DESC"
    return [_with_interviews(a) for a in query_all(sql, tuple(params))]


def get_application(application_id):
    application = query_one(APPLICATION_SELECT + " WHERE a.application_id = %s", (application_id,))
    return _with_interviews(application) if application else None


def add_application(data):
    return _insert("applications", APPLICATION_FIELDS, _application_values(data))


def update_application(application_id, data):
    _update(
        "applications", "application_id", application_id,
        APPLICATION_FIELDS, _application_values(data),
    )


def delete_application(application_id):
    execute("DELETE FROM applications WHERE application_id = %s", (application_id,))
