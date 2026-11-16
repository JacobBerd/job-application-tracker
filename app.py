"""Flask application for the Job Application Tracker."""

import os
import re
from datetime import date, datetime

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
    return render_template("company_detail.html", company=company)


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
