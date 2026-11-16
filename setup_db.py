"""One-step setup: saves MySQL credentials to .env and builds the job_tracker database.

Usage:
    python setup_db.py          # asks before resetting an existing job_tracker database
    python setup_db.py --yes    # reset without asking
"""

import getpass
import secrets
import sys
from pathlib import Path

import mysql.connector
from mysql.connector import errorcode

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
SCHEMA_PATH = BASE_DIR / "schema.sql"

DEFAULTS = {
    "DB_HOST": "localhost",
    "DB_PORT": "3306",
    "DB_USER": "root",
    "DB_PASSWORD": "",
    "DB_NAME": "job_tracker",
}


def read_env():
    settings = dict(DEFAULTS)
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                settings[key.strip()] = value.strip()
    if settings.get("DB_PASSWORD") == "your_mysql_password":
        settings["DB_PASSWORD"] = ""
    if settings.get("SECRET_KEY") in (None, "", "change-me"):
        settings["SECRET_KEY"] = secrets.token_hex(16)
    return settings


def write_env(settings):
    lines = [
        "# Created by setup_db.py. This file is git-ignored; do not commit it.",
        *(f"{key}={settings[key]}" for key in (*DEFAULTS, "SECRET_KEY")),
    ]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def connect(settings):
    """Connect to the MySQL server (not a specific database)."""
    return mysql.connector.connect(
        host=settings["DB_HOST"],
        port=int(settings["DB_PORT"]),
        user=settings["DB_USER"],
        password=settings["DB_PASSWORD"],
    )


def connect_with_prompt(settings):
    """Try the saved credentials, asking for a new user/password until they work."""
    while True:
        try:
            return connect(settings)
        except mysql.connector.Error as error:
            if error.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print(f"\nMySQL rejected user '{settings['DB_USER']}' with that password.")
                user = input(f"MySQL username [{settings['DB_USER']}]: ").strip()
                settings["DB_USER"] = user or settings["DB_USER"]
                settings["DB_PASSWORD"] = getpass.getpass("MySQL password (typing is hidden): ")
            elif error.errno == 2003:
                sys.exit(
                    f"\nCould not reach MySQL at {settings['DB_HOST']}:{settings['DB_PORT']}.\n"
                    "Start the MySQL server (Windows: Services > MySQL80 > Start) and run this again."
                )
            else:
                sys.exit(f"\nMySQL error: {error}")


def schema_statements():
    """Split schema.sql into individual statements, skipping comment lines."""
    statements, current = [], []
    for line in SCHEMA_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("--"):
            continue
        current.append(line)
        if line.rstrip().endswith(";"):
            statement = "\n".join(current).strip().rstrip(";")
            if statement:
                statements.append(statement)
            current = []
    return statements


def database_exists(conn, name):
    cursor = conn.cursor()
    cursor.execute("SHOW DATABASES LIKE %s", (name,))
    return cursor.fetchone() is not None


def main():
    print("Job Application Tracker - database setup\n")
    settings = read_env()
    conn = connect_with_prompt(settings)
    print(f"Connected to MySQL as '{settings['DB_USER']}'.")

    if settings["DB_NAME"] != "job_tracker":
        sys.exit("schema.sql creates a database named job_tracker; set DB_NAME=job_tracker in .env.")

    if database_exists(conn, "job_tracker") and "--yes" not in sys.argv:
        answer = input(
            "\nThe job_tracker database already exists. Reset it to the sample data? "
            "This deletes your current records. [y/N]: "
        )
        if answer.strip().lower() not in ("y", "yes"):
            write_env(settings)
            conn.close()
            print("\nKept the existing database. Saved credentials to .env.")
            print("Start the app with:  python app.py")
            return

    cursor = conn.cursor()
    for statement in schema_statements():
        cursor.execute(statement)
    conn.commit()

    cursor.execute("""
        SELECT (SELECT COUNT(*) FROM companies), (SELECT COUNT(*) FROM jobs),
               (SELECT COUNT(*) FROM applications), (SELECT COUNT(*) FROM contacts)
    """)
    companies, jobs, applications, contacts = cursor.fetchone()
    conn.close()
    write_env(settings)

    print("\nDatabase job_tracker created with sample data:")
    print(f"  {companies} companies, {jobs} jobs, {applications} applications, {contacts} contacts")
    print(f"Saved credentials to {ENV_PATH.name}.")
    print("\nStart the app with:  python app.py")
    print("Then open:           http://127.0.0.1:5000")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nSetup cancelled.")
