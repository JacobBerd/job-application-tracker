# Job Application Tracker

A full-stack web application for tracking a job search: the companies you're interested in, the jobs they post, the applications you submit (including interview rounds), and the people you meet along the way. A **Job Match** feature ranks jobs by how well your skills match their requirements.

Built with **MySQL**, **Python / Flask**, and **HTML / CSS (Bootstrap 5)**.

**Demo video:** [Download the project walkthrough (MP4)](https://github.com/JacobBerd/job-application-tracker/releases/download/v1.0/Job-aplication-tracker.mp4), which shows the client, server, and database. It's also listed on the [v1.0 release page](https://github.com/JacobBerd/job-application-tracker/releases/tag/v1.0).

## Quick start (about 5 minutes)

You need **Python 3.10+** and a running **MySQL 8.0+** server. Run these commands from a terminal:

```bash
git clone https://github.com/JacobBerd/job-application-tracker.git
cd job-application-tracker
pip install -r requirements.txt
python setup_db.py
python app.py
```

Then open **http://127.0.0.1:5000**.

`setup_db.py` asks for your MySQL username and password (typing is hidden), saves them to a local `.env` file that git ignores, and creates the `job_tracker` database with sample data. You don't need the `mysql` command-line tool or Workbench. If anything goes wrong, see [Troubleshooting](#troubleshooting). The detailed steps below explain the manual alternative.

## Features

- **Dashboard**: record counts, applications by status, response and interview rates, offers, average salary, upcoming interviews, recent applications, and the most requested skills.
- **Full CRUD for all four tables** (companies, jobs, applications, contacts):
  - List pages with search and filters
  - Detail pages showing related records (for example, a company's jobs and contacts)
  - Add and edit forms with server-side validation (required fields, ENUM values, salary range, email, phone, URLs, dates)
  - Delete with a confirmation dialog (deletes are POST-only)
- **JSON columns**:
  - `jobs.requirements` stores skills, years of experience, and education.
  - `applications.interview_data` stores a list of interview rounds, which you can add and remove in the form.
  - The dashboard reads both columns with MySQL's `JSON_TABLE`.
- **Job Match**: enter your skills to see jobs ranked by match percentage, for example `Software Developer at TechCorp - 100% (3/3 skills)`. Each result lists matched and missing skills. You can filter by minimum match or job type, and the page suggests skills to learn next.

## Tech stack

| Layer    | Technology                                    |
|----------|-----------------------------------------------|
| Database | MySQL 8.0+                                    |
| Backend  | Python 3.10+, Flask, mysql-connector-python   |
| Frontend | Jinja2 templates, Bootstrap 5, custom CSS     |

## Project structure

```
job-application-tracker/
├── app.py              # Flask routes, validation, error handling
├── database.py         # MySQL connection and all SQL queries
├── schema.sql          # Creates the job_tracker database, tables, and sample data
├── setup_db.py         # One-step setup: saves credentials to .env and runs schema.sql
├── requirements.txt    # Python dependencies
├── .env.example        # Template for database credentials
├── templates/          # HTML templates (Jinja2)
│   ├── base.html               # Shared layout, navbar, delete modal
│   ├── _macros.html            # Reusable template snippets
│   ├── dashboard.html
│   ├── companies.html   company_form.html   company_detail.html
│   ├── jobs.html        job_form.html       job_detail.html
│   ├── applications.html application_form.html application_detail.html
│   ├── contacts.html    contact_form.html   contact_detail.html
│   ├── job_match.html
│   └── error.html
└── static/
    ├── style.css       # Custom styles on top of Bootstrap
    └── app.js          # Delete-confirmation modal
```

## Database schema

```
companies (company_id PK)
  ├── jobs (job_id PK, company_id FK -> companies)      requirements JSON
  │     └── applications (application_id PK, job_id FK -> jobs)   interview_data JSON
  └── contacts (contact_id PK, company_id FK -> companies)
```

Foreign keys use `ON DELETE CASCADE`: deleting a company also deletes its jobs, contacts, and those jobs' applications. A `CHECK` constraint ensures `salary_min <= salary_max`.

## Setup instructions

### 1. Prerequisites

- [Python 3.10+](https://www.python.org/downloads/)
- [MySQL Server 8.0+](https://dev.mysql.com/downloads/mysql/), running locally, plus your MySQL root password (or another user's credentials)
- Git

### 2. Clone the repository

```bash
git clone https://github.com/JacobBerd/job-application-tracker.git
cd job-application-tracker
```

### 3. Install dependencies

Using a virtual environment is optional but recommended:

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Set up the database

**Option A (recommended): run the setup script.**

```bash
python setup_db.py
```

The script:
1. Asks for your MySQL username (default `root`) and password, and retries if they're wrong.
2. Saves them to `.env`. That file is in `.gitignore`, so passwords are never committed.
3. Runs `schema.sql` to create the `job_tracker` database, its four tables, and the sample data.

If `job_tracker` already exists, it asks before resetting it. Use `python setup_db.py --yes` to skip the question.

**Option B: set it up manually.**

1. Run `schema.sql`, either in **MySQL Workbench** (open the file, then click the lightning bolt **Execute** button) or from a terminal:

   ```bash
   mysql -u root -p < schema.sql
   ```

   In Windows PowerShell, `<` isn't supported and `mysql` is often not on the PATH. Use this instead:

   ```powershell
   Get-Content schema.sql -Raw | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
   ```

2. Copy `.env.example` to `.env` (Windows: `copy .env.example .env`, macOS/Linux: `cp .env.example .env`). Then set `DB_PASSWORD` (and `DB_USER`, if you don't use `root`):

   ```
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_mysql_password
   DB_NAME=job_tracker
   SECRET_KEY=any-random-string
   ```

**Warning:** `schema.sql` starts with `DROP DATABASE IF EXISTS job_tracker`, so re-running it, by either option, resets the database to the sample data.

### 5. Run the application

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser. If something is misconfigured, the page explains what to fix.

## Using the app

1. **Dashboard** (`/`): overview statistics. Click any card or status to jump to the filtered list.
2. **Companies** (`/companies`): add a company first. Jobs and contacts belong to a company.
3. **Jobs** (`/jobs`): add jobs with a salary range and required skills (comma-separated). Skills are saved to the `requirements` JSON column.
4. **Applications** (`/applications`): log an application for a job. Set its status, resume version, and cover letter, and add interview rounds.
5. **Contacts** (`/contacts`): save recruiters and hiring managers for each company.
6. **Job Match** (`/job-match`): type skills such as `Python, SQL, Flask`, or click the suggested skill chips, then press **Match**.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Access denied for user 'root'@'localhost'` | The MySQL password in `.env` is wrong. Run `python setup_db.py` again to re-enter it, then restart the app. |
| `Unknown database 'job_tracker'` | Run `python setup_db.py` (or `schema.sql`, step 4). |
| `Can't connect to MySQL server` | Start the MySQL service (Windows: Services, then **MySQL80**, then Start; macOS: `brew services start mysql`). |
| `ModuleNotFoundError: No module named 'flask'` (or `'mysql'`) | Run `pip install -r requirements.txt` (with the virtual environment activated, if you made one). |
| `'pip' is not recognized` | Use `python -m pip install -r requirements.txt`. On macOS/Linux, try `python3` / `pip3`. |
| `'mysql' is not recognized` (Windows) | Use `python setup_db.py` instead, or the full path shown in step 4. |
| Port 5000 is already in use (common on macOS because of AirPlay) | Run `flask --app app run --port 5001` and open http://127.0.0.1:5001. |
