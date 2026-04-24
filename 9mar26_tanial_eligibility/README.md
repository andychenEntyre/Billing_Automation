# Real-Time Eligibility Check (Tanial)

This folder contains a script that runs Stedi eligibility checks for each client and appends normalized results to a CSV output table.

Script:
- `9mar26_tanial_eligibility/multi_real_time_eligibility_check.py`

## What the script does

- Reads an input CSV (`user_excel_data` path in the script).
- For each client:
  - Uses `Client Mass Health Id` lookup when available.
  - Otherwise falls back to demographic lookup using first name, last name, DOB, and gender.
- Calls Stedi eligibility API (`/eligibility/v3`).
- Flattens `benefitsInformation` and appends rows to output CSV.
- Writes fallback rows with status metadata when no benefits are returned.

## Required input columns

Required:
- `Client First Name`
- `Client Last Name`

Needed for demographic fallback (when `Client Mass Health Id` is missing):
- `Client Birthdate`
- `Client Gender`

Optional but recommended:
- `Client Mass Health Id`
- `Client Public Id`
- `Most Recent Appointment Scheduled Date Time`

## Client Birthdate format

`Client Birthdate` now supports:
- `YYYY-MM-DD` (example: `2012-01-28`)
- `MM/DD/YYYY`
- `MM/DD/YY`

The script converts DOB to `YYYYMMDD` before sending to Stedi.

## Configure input and output

In the script, update:
- `user_excel_data = pd.read_csv("...")` for your input CSV path
- `out_path = "..."` for your output CSV path

## Run

From repo root:

```bash
python3 "/Users/Andy.Chen/Billing_Automation/9mar26_tanial_eligibility/multi_real_time_eligibility_check.py"
```

## Notes

- The script appends to `out_path` if it already exists.
- If `benefitsInformation` is empty, a fallback row is still written with status details.
- The script currently uses a hardcoded API authorization token in code.
