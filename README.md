# Vacation Leave Ledger

A Flask app that calculates an employee's accrued vacation leave based on
length of service.

## Accrual rules

| Years of service | Accrual rate |
|---|---|
| 1–10 years | 28 days / year |
| 10+ years (year 11 onward) | 35 days / year |

The employee's current, in-progress year is **prorated**: e.g. someone
6 months into their first year has earned `28 × 0.5 = 14` days so far.
Once an employee crosses the 10-year mark, the higher 35-day rate applies
only to the portion of service after that point — years 1–10 are still
counted at 28 days/year.

**Leave does not accrue while an employee is on vacation leave.** Days
taken as leave pause the accrual clock — they don't count as time worked
for accrual purposes. Concretely:

- `active days = calendar days elapsed − leave days taken`
- Accrual (years of service, tier, and days earned) is calculated from
  `active days`, not raw calendar time.
- The result includes both figures: `calendar_years_of_service` (raw
  tenure since the start date) and `years_of_service` (the active,
  accrual-clock figure) — they diverge once leave is taken.
- Leave taken still also reduces the balance directly, since those days
  were spent. So taking leave has two effects: it's deducted from the
  balance, *and* it slows down how fast new leave is earned.
- It's invalid to report more leave taken than calendar days elapsed
  since the start date; the app returns a 400 error in that case.

## Project structure

```
vacation_leave_app/
├── app.py                 # Flask app: routes + calculation logic
├── requirements.txt
├── templates/
│   └── index.html         # Form + result UI
└── static/
    ├── style.css           # Ledger/bluebar-paper themed styling
    └── app.js               # Fetches /api/calculate and renders results
```

## Running it

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

## API

You can also call the calculation directly, e.g. for integration with
another system:

```
POST /api/calculate
Content-Type: application/json

{
  "start_date": "2013-01-01",
  "as_of_date": "2025-01-01",   // optional, defaults to today
  "leave_taken": 50               // optional, defaults to 0
}
```

Response:

```json
{
  "ok": true,
  "result": {
    "calendar_years_of_service": 12.0,
    "years_of_service": 10.63,
    "non_accruing_days": 500.0,
    "full_years_completed": 10,
    "current_tier": "10+ years (35 days/year)",
    "accrued_leave": 302.05,
    "leave_taken": 500.0,
    "balance": -197.95,
    "breakdown": [ { "year_number": 1, "rate_per_year": 28, "days_earned": 28, "status": "complete" }, ... ]
  }
}
```

On invalid input, it returns `{"ok": false, "error": "..."}` with a 400
status code.

## Notes / assumptions

- A year of service is calculated as `365.25` calendar days, to naturally
  account for leap years.
- The "as of" date defaults to today but can be set to any date at or
  after the start date — useful for calculating leave balance as of a
  past pay period, or a future date.
- If your organization's policy does *not* prorate the first partial
  year (i.e. no days accrue until the employee's first anniversary),
  that's a one-line change in `rate_for_year`/`calculate_vacation_leave`
  in `app.py` — happy to adjust if that's the actual rule.
