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


# ---------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------
CONTACT_FIELDS = (
    "company_id", "contact_name", "title", "email", "phone", "linkedin_url", "notes",
)
CONTACT_SELECT = """
    SELECT ct.*, c.company_name
    FROM contacts ct
    JOIN companies c ON c.company_id = ct.company_id
"""


def get_contacts(company_id=None, search=None):
    conditions, params = [], []
    if company_id:
        conditions.append("ct.company_id = %s")
        params.append(company_id)
    if search:
        conditions.append(
            "(ct.contact_name LIKE %s OR ct.title LIKE %s OR ct.email LIKE %s OR c.company_name LIKE %s)"
        )
        params += [f"%{search}%"] * 4
    sql = CONTACT_SELECT
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY ct.contact_name"
    return query_all(sql, tuple(params))


def get_contact(contact_id):
    return query_one(CONTACT_SELECT + " WHERE ct.contact_id = %s", (contact_id,))


def add_contact(data):
    return _insert("contacts", CONTACT_FIELDS, data)


def update_contact(contact_id, data):
    _update("contacts", "contact_id", contact_id, CONTACT_FIELDS, data)


def delete_contact(contact_id):
    execute("DELETE FROM contacts WHERE contact_id = %s", (contact_id,))


# ---------------------------------------------------------------
# Job Match
# ---------------------------------------------------------------
def calculate_match(user_skills, job_skills):
    """Compare a user's skills to a job's required skills (case-insensitive)."""
    user_lookup = {skill.lower() for skill in user_skills}
    matched = [skill for skill in job_skills if skill.lower() in user_lookup]
    missing = [skill for skill in job_skills if skill.lower() not in user_lookup]
    total = len(job_skills)
    return {
        "matched": matched,
        "missing": missing,
        "matched_count": len(matched),
        "total": total,
        # Round half up so 2.5% -> 3%, unlike Python's round() which rounds half to even.
        "percent": int(len(matched) * 100 / total + 0.5) if total else 0,
    }


def match_jobs(user_skills, min_percent=0, job_type=None):
    """Rank every job that lists required skills by how well user_skills cover them."""
    results = []
    for job in get_jobs(job_type=job_type):
        if not job["skills"]:
            continue
        match = calculate_match(user_skills, job["skills"])
        if match["percent"] >= min_percent:
            results.append({**job, **match})
    results.sort(key=lambda r: (-r["percent"], -r["matched_count"], r["job_title"].lower()))
    return results


def skills_to_learn(results, limit=5):
    """Most common missing skills across the matched jobs."""
    counts = {}
    for result in results:
        for skill in result["missing"]:
            key = skill.lower()
            name, count = counts.get(key, (skill, 0))
            counts[key] = (name, count + 1)
    ranked = sorted(counts.values(), key=lambda item: (-item[1], item[0].lower()))
    return [{"skill": name, "job_count": count} for name, count in ranked[:limit]]


def get_all_skills():
    """Every distinct skill listed in any job's requirements JSON."""
    rows = query_all("""
        SELECT DISTINCT s.skill
        FROM jobs j,
        JSON_TABLE(j.requirements, '$.skills[*]' COLUMNS (
            skill VARCHAR(50) PATH '$' NULL ON ERROR
        )) AS s
        WHERE s.skill IS NOT NULL
        ORDER BY s.skill
    """)
    return [row["skill"] for row in rows]


# ---------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------
def _percent(part, whole):
    return round(part * 100 / whole) if whole else 0


def get_dashboard_stats():
    counts = query_one("""
        SELECT (SELECT COUNT(*) FROM companies)    AS companies,
               (SELECT COUNT(*) FROM jobs)         AS jobs,
               (SELECT COUNT(*) FROM applications) AS applications,
               (SELECT COUNT(*) FROM contacts)     AS contacts
    """)

    by_status = {status: 0 for status in APPLICATION_STATUSES}
    for row in query_all("SELECT status, COUNT(*) AS total FROM applications GROUP BY status"):
        by_status[row["status"]] = row["total"]

    total = counts["applications"]
    heard_back = total - by_status["Applied"] - by_status["Withdrawn"]
    reached_interview = by_status["Interview"] + by_status["Offer"]
    active = by_status["Applied"] + by_status["Screening"] + by_status["Interview"]

    salary = query_one("""
        SELECT ROUND(AVG((salary_min + salary_max) / 2)) AS average_midpoint
        FROM jobs
        WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL
    """)

    upcoming_interviews = query_all("""
        SELECT a.application_id, j.job_title, c.company_name,
               r.interview_date, r.interview_type, r.interviewer
        FROM applications a
        JOIN jobs j ON j.job_id = a.job_id
        JOIN companies c ON c.company_id = j.company_id,
        JSON_TABLE(a.interview_data, '$.rounds[*]' COLUMNS (
            interview_date DATE         PATH '$.date'        NULL ON EMPTY NULL ON ERROR,
            interview_type VARCHAR(50)  PATH '$.type'        NULL ON EMPTY NULL ON ERROR,
            interviewer    VARCHAR(100) PATH '$.interviewer' NULL ON EMPTY NULL ON ERROR
        )) AS r
        WHERE r.interview_date >= CURDATE()
          AND a.status NOT IN ('Rejected', 'Withdrawn')
        ORDER BY r.interview_date
        LIMIT 5
    """)

    top_skills = query_all("""
        SELECT s.skill, COUNT(*) AS job_count
        FROM jobs j,
        JSON_TABLE(j.requirements, '$.skills[*]' COLUMNS (
            skill VARCHAR(50) PATH '$' NULL ON ERROR
        )) AS s
        WHERE s.skill IS NOT NULL
        GROUP BY s.skill
        ORDER BY job_count DESC, s.skill
        LIMIT 10
    """)

    recent_applications = [
        _with_interviews(a) for a in query_all(
            APPLICATION_SELECT + " ORDER BY a.application_date DESC, a.application_id DESC LIMIT 5"
        )
    ]

    return {
        "counts": counts,
        "by_status": by_status,
        "status_percent": {s: _percent(n, total) for s, n in by_status.items()},
        "active": active,
        "response_rate": _percent(heard_back, total),
        "interview_rate": _percent(reached_interview, total),
        "offers": by_status["Offer"],
        "average_salary": salary["average_midpoint"],
        "upcoming_interviews": upcoming_interviews,
        "top_skills": top_skills,
        "recent_applications": recent_applications,
    }
