"""
Vacation Leave Ledger
----------------------
A small Flask app that calculates accrued vacation leave for an employee
based on their length of service.

Accrual rules:
    - Years 1 through 10 of service: 28 days per year
    - Year 11 onward:                35 days per year

The current (in-progress) year of service is prorated based on how much
of that year has elapsed as of the "as of" date.

Leave does not accrue while an employee is on vacation leave. Days taken
as leave pause the accrual clock: they are subtracted from the elapsed
calendar time before that time is converted into "years of service" for
accrual purposes. This means taking leave has two effects:
    1. It consumes days from the accrued balance (as always).
    2. It delays how much is earned going forward, since the days spent
       on leave don't count toward the service clock.
"""

from datetime import date, datetime

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

DAYS_PER_YEAR_TIER_1 = 28   # years 1-10
DAYS_PER_YEAR_TIER_2 = 35   # year 11+
TIER_BREAKPOINT_YEARS = 10  # years of completed service before rate increases
DAYS_IN_YEAR = 365.25


class ValidationError(Exception):
    """Raised when request input fails validation."""


def parse_date(value, field_name):
    if not value:
        raise ValidationError(f"{field_name} is required.")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(f"{field_name} must be a valid date (YYYY-MM-DD).")


def rate_for_year(year_number):
    """Return the daily accrual rate that applies to a given year of service.

    year_number is 1-indexed: year_number=1 is the employee's first year,
    year_number=11 is their eleventh year, etc.
    """
    if year_number > TIER_BREAKPOINT_YEARS:
        return DAYS_PER_YEAR_TIER_2
    return DAYS_PER_YEAR_TIER_1


def calculate_vacation_leave(start_date, as_of_date, leave_taken=0.0):
    """Calculate accrued vacation leave between start_date and as_of_date.

    Leave does not accrue while an employee is on vacation leave, so
    `leave_taken` (total days of leave taken to date) is subtracted from
    elapsed calendar time before that time is converted into years of
    service for accrual purposes. This "active service" clock is what
    drives both the accrual rate tier and how much has been earned.

    Returns a dict with calendar tenure, active (accrual-clock) service,
    a year-by-year breakdown (for display / visualization), total
    accrued leave, leave taken, and remaining balance.
    """
    if as_of_date < start_date:
        raise ValidationError("'As of' date cannot be before the start date.")
    if leave_taken < 0:
        raise ValidationError("Leave taken cannot be negative.")

    total_calendar_days = (as_of_date - start_date).days

    if leave_taken > total_calendar_days:
        raise ValidationError(
            "Leave taken cannot exceed the number of days elapsed since the start date."
        )

    # Days actually spent accruing leave: calendar time minus time spent
    # on leave (which pauses accrual).
    active_days = total_calendar_days - leave_taken

    calendar_years_of_service = total_calendar_days / DAYS_IN_YEAR
    active_years_of_service = active_days / DAYS_IN_YEAR

    full_years_completed = int(active_years_of_service)
    remainder_fraction = active_years_of_service - full_years_completed

    breakdown = []
    accrued = 0.0

    for year_number in range(1, full_years_completed + 1):
        rate = rate_for_year(year_number)
        breakdown.append({
            "year_number": year_number,
            "rate_per_year": rate,
            "days_earned": rate,
            "status": "complete",
        })
        accrued += rate

    if remainder_fraction > 0 or full_years_completed == 0:
        current_year_number = full_years_completed + 1
        rate = rate_for_year(current_year_number)
        days_earned = round(rate * remainder_fraction, 2)
        breakdown.append({
            "year_number": current_year_number,
            "rate_per_year": rate,
            "days_earned": days_earned,
            "status": "in_progress",
            "percent_complete": round(remainder_fraction * 100, 1),
        })
        accrued += days_earned

    accrued = round(accrued, 2)
    balance = round(accrued - leave_taken, 2)

    return {
        "start_date": start_date.isoformat(),
        "as_of_date": as_of_date.isoformat(),
        "calendar_years_of_service": round(calendar_years_of_service, 2),
        "years_of_service": round(active_years_of_service, 2),
        "non_accruing_days": round(leave_taken, 2),
        "full_years_completed": full_years_completed,
        "current_tier": (
            "10+ years (35 days/year)"
            if full_years_completed >= TIER_BREAKPOINT_YEARS
            else "1-10 years (28 days/year)"
        ),
        "breakdown": breakdown,
        "accrued_leave": accrued,
        "leave_taken": round(leave_taken, 2),
        "balance": balance,
    }


@app.route("/")
def index():
    today = date.today().isoformat()
    return render_template("index.html", today=today)


@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    payload = request.get_json(silent=True) or request.form

    try:
        start_date = parse_date(payload.get("start_date"), "Start date")

        as_of_raw = payload.get("as_of_date")
        as_of_date = parse_date(as_of_raw, "As of date") if as_of_raw else date.today()

        leave_taken_raw = payload.get("leave_taken", 0) or 0
        try:
            leave_taken = float(leave_taken_raw)
        except (TypeError, ValueError):
            raise ValidationError("Leave taken must be a number.")

        result = calculate_vacation_leave(start_date, as_of_date, leave_taken)
        return jsonify({"ok": True, "result": result})

    except ValidationError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host="0.0.0.0", port=port)

