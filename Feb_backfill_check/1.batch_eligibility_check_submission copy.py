
import os
import pandas as pd
import time
import json
import requests
from datetime import datetime

'''this file comes from Databricks MA client pull'''

file_path = "real_time_eligibility_check/02March26_MA_clients.csv"
df = pd.read_csv(file_path)

# --- Config ---
URL = "https://manager.us.stedi.com/2024-04-01/eligibility-manager/batch-eligibility"
API_KEY = "RYnvhqL.0X6jgBc6ewt5N7v2ILnQtiGy"
if not API_KEY:
    raise ValueError("Missing STEDI_API_KEY env var. Set it before running.")

HEADERS = {
    "Authorization": API_KEY,
    "Content-Type": "application/json",
}

LOG_PATH = "Feb_backfill_check/Feb_eligibility_batch_log.csv"

# Optional: create log header if file doesn't exist yet
if not os.path.exists(LOG_PATH):
    pd.DataFrame(columns=["day", "batch_name", "batch_id", "submitted_at", "status_code"]).to_csv(
        LOG_PATH, index=False
    )

# --- Helper: build full items list once (no day inside yet) ---
base_items = []
for _, row in df.iterrows():
    base_items.append({
        "provider": {
            "npi": "1245675776",
            "organizationName": "ENTYRE CARE MASSACHUSETTS INC"
        },
        "submitterTransactionIdentifier": str(row["public_id"]),
        "subscriber": {
            "firstName": str(row["first_name"]),
            "lastName": str(row["last_name"]),
            "memberId": str(row["medicaid_id"])
        },
        "tradingPartnerServiceId": "KWDBT"
    })

# --- Submit 28 batches, one per day ---
for day in range(1, 29):
    dos = f"202602{day:02d}"  # 20260201 ... 20260230
    # create day-specific items (add encounter.dateOfService)
    items = []
    for item in base_items:
        item_with_dos = dict(item)
        item_with_dos = {
            "encounter": {"dateOfService": dos},
            **item
            }
        print(item_with_dos)
        items.append(item_with_dos)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_name = f"eligibility-batch-{timestamp}-FEB{day:02d}"

    body = {
        "items": items,
        "name": batch_name
    }

    # simple retry loop for transient failures
    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.post(URL, json=body, headers=HEADERS, timeout=30)
            # If API returns non-JSON on error, this avoids crashing
            resp_json = {}
            try:
                resp_json = resp.json()
            except Exception:
                resp_json = {}
            print(f"Day {day:02d} -> status {resp.status_code}: {resp.text[:300]}")

             # log result
            log_row = {
                "day": f"{day:02d}",
                "batch_name": batch_name,
                "batch_id": resp_json.get("batchId"),
                "submitted_at": resp_json.get("submittedAt"),
                "status_code": resp.status_code,
            }
            pd.DataFrame([log_row]).to_csv(LOG_PATH, mode="a", header=False, index=False)

            # break retry loop on success or client error (4xx)
            if resp.status_code < 500:
                break
        
        except requests.RequestException as e:
            print(f"Day {day:02d} attempt {attempt}/{max_attempts} error: {e}")

        # backoff before retrying
        if attempt < max_attempts:
            time.sleep(2 * attempt)

    time.sleep(0.5)





