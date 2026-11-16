"""Flask application for the Job Application Tracker."""

import os
import re
from datetime import date

import mysql.connector
from flask import Flask, abort, flash, redirect, render_template, request, url_for

import database as db

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)


# ---------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------
@app.template_filter("money")
def money_filter(value):
    return "" if value is None else f"${value:,.0f}"


@app.template_filter("nice_date")
def nice_date_filter(value):
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime("%b %d, %Y")


# ---------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------
def clean(form, field):
    """Return a stripped form value, or None when it is blank."""
    value = form.get(field, "").strip()
    return value or None


def check_lengths(errors, data, limits):
    """limits maps field -> (label, max_length)."""
    for field, (label, max_len) in limits.items():
        value = data.get(field)
        if value and len(value) > max_len:
            errors.append(f"{label} must be {max_len} characters or fewer.")


def check_url(errors, label, value):
    if value and not URL_RE.match(value):
        errors.append(f"{label} must be a full URL starting with http:// or https://.")


def parse_int(errors, label, raw, minimum=0, maximum=10_000_000):
    """Parse an optional whole number; on failure record an error and return the raw text."""
    if raw is None:
        return None
    try:
        value = int(raw.replace(",", "").replace("$", ""))
    except ValueError:
        errors.append(f"{label} must be a whole number.")
        return raw
    if not minimum <= value <= maximum:
        errors.append(f"{label} must be between {minimum:,} and {maximum:,}.")
    return value


def parse_date(errors, label, raw, required=False):
    """Parse a YYYY-MM-DD date; on failure record an error and return the raw text."""
    if raw is None:
        if required:
            errors.append(f"{label} is required.")
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        errors.append(f"{label} must be a valid date (YYYY-MM-DD).")
        return raw


def parse_choice(errors, label, raw, choices, required=True):
    if raw is None:
        if required:
            errors.append(f"{label} is required.")
        return None
    if raw not in choices:
        errors.append(f"{label} must be one of: {', '.join(choices)}.")
    return raw


def parse_foreign_key(errors, label, raw, options, key):
    """Validate that raw is the id of one of the dropdown options."""
    if raw is None:
        errors.append(f"{label} is required.")
        return None
    valid_ids = {option[key] for option in options}
    if not raw.isdigit() or int(raw) not in valid_ids:
        errors.append(f"Please choose a valid {label.lower()}.")
        return raw
    return int(raw)


def get_or_404(fetch, record_id):
    record = fetch(record_id)
    if record is None:
        abort(404)
    return record


def show_errors(errors):
    for error in errors:
        flash(error, "danger")


# ---------------------------------------------------------------
# Companies
# ---------------------------------------------------------------
COMPANY_LIMITS = {
    "company_name": ("Company name", 100),
    "industry": ("Industry", 50),
    "website": ("Website", 200),
    "city": ("City", 50),
    "state": ("State", 50),
}


def validate_company(form):
    data = {field: clean(form, field) for field in db.COMPANY_FIELDS}
    errors = []
    if not data["company_name"]:
        errors.append("Company name is required.")
    check_lengths(errors, data, COMPANY_LIMITS)
    check_url(errors, "Website", data["website"])
    return data, errors


@app.route("/companies")
def companies():
    search = request.args.get("q", "").strip()
    return render_template(
        "companies.html", companies=db.get_companies(search), search=search
    )


@app.route("/companies/<int:company_id>")
def company_detail(company_id):
    company = get_or_404(db.get_company, company_id)
    return render_template(
        "company_detail.html", company=company, jobs=db.get_jobs(company_id=company_id)
    )


@app.route("/companies/add", methods=["GET", "POST"])
def add_company():
    form = {}
    if request.method == "POST":
        form, errors = validate_company(request.form)
        if not errors:
            company_id = db.add_company(form)
            flash(f"Company \"{form['company_name']}\" added.", "success")
            return redirect(url_for("company_detail", company_id=company_id))
        show_errors(errors)
    return render_template("company_form.html", form=form, company_id=None)


@app.route("/companies/<int:company_id>/edit", methods=["GET", "POST"])
def edit_company(company_id):
    form = get_or_404(db.get_company, company_id)
    if request.method == "POST":
        form, errors = validate_company(request.form)
        if not errors:
            db.update_company(company_id, form)
            flash(f"Company \"{form['company_name']}\" updated.", "success")
            return redirect(url_for("company_detail", company_id=company_id))
        show_errors(errors)
    return render_template("company_form.html", form=form, company_id=company_id)


@app.route("/companies/<int:company_id>/delete", methods=["POST"])
def delete_company(company_id):
    company = get_or_404(db.get_company, company_id)
    db.delete_company(company_id)
    flash(f"Company \"{company['company_name']}\" and its related records were deleted.", "success")
    return redirect(url_for("companies"))


# ---------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------
def validate_job(form, company_options):
    errors = []
    data = {
        "company_id": parse_foreign_key(
            errors, "Company", clean(form, "company_id"), company_options, "company_id"
        ),
        "job_title": clean(form, "job_title"),
        "job_type": parse_choice(errors, "Job type", clean(form, "job_type"), db.JOB_TYPES),
        "salary_min": parse_int(errors, "Minimum salary", clean(form, "salary_min")),
        "salary_max": parse_int(errors, "Maximum salary", clean(form, "salary_max")),
        "job_url": clean(form, "job_url"),
        "date_posted": parse_date(errors, "Date posted", clean(form, "date_posted")),
        "skills_text": clean(form, "skills_text"),
        "experience_years": parse_int(
            errors, "Years of experience", clean(form, "experience_years"), maximum=50
        ),
        "education": clean(form, "education"),
    }
    if not data["job_title"]:
        errors.append("Job title is required.")
    check_lengths(errors, data, {
        "job_title": ("Job title", 100),
        "job_url": ("Job URL", 300),
        "education": ("Education", 100),
    })
    check_url(errors, "Job URL", data["job_url"])
    if (isinstance(data["salary_min"], int) and isinstance(data["salary_max"], int)
            and data["salary_min"] > data["salary_max"]):
        errors.append("Minimum salary cannot be greater than maximum salary.")

    skills = db.split_skills(data["skills_text"])
    if any(len(skill) > 50 for skill in skills):
        errors.append("Each skill must be 50 characters or fewer.")
    requirements = {"skills": skills}
    if isinstance(data["experience_years"], int):
        requirements["experience_years"] = data["experience_years"]
    if data["education"]:
        requirements["education"] = data["education"]
    data["requirements"] = requirements
    return data, errors


def job_to_form(job):
    """Flatten a job's requirements JSON into the separate form fields."""
    requirements = job["requirements"]
    return {
        **job,
        "skills_text": ", ".join(job["skills"]),
        "experience_years": requirements.get("experience_years"),
        "education": requirements.get("education"),
    }


@app.route("/jobs")
def jobs():
    filters = {
        "search": request.args.get("q", "").strip(),
        "job_type": request.args.get("type", "").strip(),
        "company_id": request.args.get("company", type=int),
    }
    return render_template(
        "jobs.html",
        jobs=db.get_jobs(**filters),
        filters=filters,
        job_types=db.JOB_TYPES,
        companies=db.get_company_options(),
    )


@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    job = get_or_404(db.get_job, job_id)
    return render_template(
        "job_detail.html", job=job, applications=db.get_applications(job_id=job_id)
    )


@app.route("/jobs/add", methods=["GET", "POST"])
def add_job():
    company_options = db.get_company_options()
    form = {"company_id": request.args.get("company_id", type=int), "job_type": "Full-time"}
    if request.method == "POST":
        form, errors = validate_job(request.form, company_options)
        if not errors:
            job_id = db.add_job(form)
            flash(f"Job \"{form['job_title']}\" added.", "success")
            return redirect(url_for("job_detail", job_id=job_id))
        show_errors(errors)
    return render_template(
        "job_form.html", form=form, job_id=None,
        companies=company_options, job_types=db.JOB_TYPES,
    )


@app.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
def edit_job(job_id):
    form = job_to_form(get_or_404(db.get_job, job_id))
    company_options = db.get_company_options()
    if request.method == "POST":
        form, errors = validate_job(request.form, company_options)
        if not errors:
            db.update_job(job_id, form)
            flash(f"Job \"{form['job_title']}\" updated.", "success")
            return redirect(url_for("job_detail", job_id=job_id))
        show_errors(errors)
    return render_template(
        "job_form.html", form=form, job_id=job_id,
        companies=company_options, job_types=db.JOB_TYPES,
    )


@app.route("/jobs/<int:job_id>/delete", methods=["POST"])
def delete_job(job_id):
    job = get_or_404(db.get_job, job_id)
    db.delete_job(job_id)
    flash(f"Job \"{job['job_title']}\" and its applications were deleted.", "success")
    return redirect(url_for("jobs"))


# ---------------------------------------------------------------
# Applications
# ---------------------------------------------------------------
INTERVIEW_TYPES = (
    "Phone Screen", "Video", "Technical", "Behavioral", "Onsite", "Panel", "Final", "Other",
)


def parse_interview_rounds(form, errors):
    """Collect the repeated round_* form fields into a list of interview round dicts."""
    rows = zip(
        form.getlist("round_date"),
        form.getlist("round_type"),
        form.getlist("round_interviewer"),
        form.getlist("round_notes"),
    )
    rounds = []
    for number, (raw_date, raw_type, interviewer, notes) in enumerate(rows, start=1):
        interview = {
            "date": raw_date.strip(),
            "type": raw_type.strip(),
            "interviewer": interviewer.strip(),
            "notes": notes.strip(),
        }
        if not any(interview.values()):
            continue
        label = f"Interview round {number}"
        parse_date(errors, f"{label} date", interview["date"] or None, required=True)
        if not interview["type"]:
            errors.append(f"{label} type is required.")
        elif len(interview["type"]) > 50:
            errors.append(f"{label} type must be 50 characters or fewer.")
        if len(interview["interviewer"]) > 100:
            errors.append(f"{label} interviewer must be 100 characters or fewer.")
        rounds.append(interview)
    rounds.sort(key=lambda r: r["date"])
    return rounds


def validate_application(form, job_options):
    errors = []
    data = {
        "job_id": parse_foreign_key(errors, "Job", clean(form, "job_id"), job_options, "job_id"),
        "application_date": parse_date(
            errors, "Application date", clean(form, "application_date"), required=True
        ),
        "status": parse_choice(errors, "Status", clean(form, "status"), db.APPLICATION_STATUSES),
        "resume_version": clean(form, "resume_version"),
        "cover_letter_sent": form.get("cover_letter_sent") == "on",
    }
    check_lengths(errors, data, {"resume_version": ("Resume version", 50)})
    data["rounds"] = parse_interview_rounds(form, errors)
    data["interview_data"] = {"rounds": data["rounds"]} if data["rounds"] else None
    return data, errors


def render_application_form(form, application_id):
    return render_template(
        "application_form.html",
        form=form,
        application_id=application_id,
        jobs=db.get_job_options(),
        statuses=db.APPLICATION_STATUSES,
        interview_types=INTERVIEW_TYPES,
    )


@app.route("/applications")
def applications():
    filters = {
        "search": request.args.get("q", "").strip(),
        "status": request.args.get("status", "").strip(),
    }
    return render_template(
        "applications.html",
        applications=db.get_applications(**filters),
        filters=filters,
        statuses=db.APPLICATION_STATUSES,
    )


@app.route("/applications/<int:application_id>")
def application_detail(application_id):
    application = get_or_404(db.get_application, application_id)
    return render_template("application_detail.html", application=application)


@app.route("/applications/add", methods=["GET", "POST"])
def add_application():
    form = {
        "job_id": request.args.get("job_id", type=int),
        "application_date": date.today().isoformat(),
        "status": "Applied",
    }
    if request.method == "POST":
        form, errors = validate_application(request.form, db.get_job_options())
        if not errors:
            application_id = db.add_application(form)
            flash("Application added.", "success")
            return redirect(url_for("application_detail", application_id=application_id))
        show_errors(errors)
    return render_application_form(form, None)


@app.route("/applications/<int:application_id>/edit", methods=["GET", "POST"])
def edit_application(application_id):
    form = get_or_404(db.get_application, application_id)
    if request.method == "POST":
        form, errors = validate_application(request.form, db.get_job_options())
        if not errors:
            db.update_application(application_id, form)
            flash("Application updated.", "success")
            return redirect(url_for("application_detail", application_id=application_id))
        show_errors(errors)
    return render_application_form(form, application_id)


@app.route("/applications/<int:application_id>/delete", methods=["POST"])
def delete_application(application_id):
    application = get_or_404(db.get_application, application_id)
    db.delete_application(application_id)
    flash(
        f"Application for \"{application['job_title']}\" at {application['company_name']} was deleted.",
        "success",
    )
    return redirect(url_for("applications"))


# ---------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------
@app.route("/")
def dashboard():
    return redirect(url_for("companies"))


# ---------------------------------------------------------------
# Error pages
# ---------------------------------------------------------------
@app.errorhandler(404)
def not_found(_error):
    return render_template(
        "error.html",
        title="Page not found",
        message="The page or record you were looking for does not exist.",
    ), 404


@app.errorhandler(mysql.connector.Error)
def database_error(error):
    app.logger.exception("Database error")
    return render_template(
        "error.html",
        title="Database error",
        message="Something went wrong talking to MySQL. Check that the server is running "
        "and that the settings in your .env file are correct.",
        detail=str(error),
    ), 500


if __name__ == "__main__":
    app.run(debug=True)
