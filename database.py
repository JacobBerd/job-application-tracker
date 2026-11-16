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
