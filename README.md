# Job Application Tracker

A full-stack web application for tracking a job search: the companies you're interested in, the jobs they post, the applications you submit (including interview rounds), and the people you meet along the way. A **Job Match** feature ranks jobs by how well your skills match their requirements.

Built with **MySQL**, **Python / Flask**, and **HTML / CSS (Bootstrap 5)**.

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

### 3. Create the database

From the project folder, run `schema.sql`. It creates the `job_tracker` database and its four tables, and loads sample data.

```bash
mysql -u root -p < schema.sql
```

> **Windows (PowerShell):** `<` redirection isn't supported, and `mysql` may not be on your PATH. Use:
>
> ```powershell
> Get-Content schema.sql -Raw | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
> ```
>
> Or open `schema.sql` in **MySQL Workbench** and click **Execute** (the lightning bolt icon).

**Warning:** `schema.sql` starts with `DROP DATABASE IF EXISTS job_tracker`, so re-running it resets the database to the sample data.

### 4. Create a virtual environment and install dependencies

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 5. Configure database credentials

Copy the example environment file and enter your MySQL password:

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

Then edit `.env`:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=job_tracker
SECRET_KEY=any-random-string
```

`.env` is listed in `.gitignore`, so your password is never committed.

### 6. Run the application

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

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
| `Database error ... Access denied for user 'root'@'localhost'` | The password in `.env` is wrong. Fix `DB_PASSWORD` and restart the app. |
| `Unknown database 'job_tracker'` | Run `schema.sql` (step 3). |
| `Can't connect to MySQL server` | Start the MySQL service (Windows: Services, then **MySQL80**, then Start). |
| `ModuleNotFoundError: No module named 'flask'` | Activate the virtual environment and run `pip install -r requirements.txt`. |
| `'mysql' is not recognized` (Windows) | Use the full path shown in step 3, or run the script from MySQL Workbench. |
