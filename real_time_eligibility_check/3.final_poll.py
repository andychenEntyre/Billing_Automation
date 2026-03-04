import requests
import pandas as pd
import json
from datetime import datetime
import re
import os

''' this script pulls the results from the batch eligibility check and formats into excel file for Sigma Dashboard'''


BASE_URL = "https://manager.us.stedi.com/2024-04-01/eligibility-manager/polling/batch-eligibility"
BATCH_ID = "019cb3fe-d505-7a22-a73b-6e791940c03c"

headers = {
    "Authorization": "RYnvhqL.0X6jgBc6ewt5N7v2ILnQtiGy",
    "Accept-Encoding": "gzip"  # Required when pageSize > 20
}

all_items = []
page_token = None
page_size = 200  # Max allowed

while True:
    params = {
        "batchId": BATCH_ID,
        "pageSize": page_size
    }

    if page_token:
        params["pageToken"] = page_token

    response = requests.get(BASE_URL, headers=headers, params=params)
    response.raise_for_status()

    data = response.json()

    items = data.get("items", [])
    all_items.extend(items)

    print(f"Pulled {len(items)} items this page. Total so far: {len(all_items)}")

    page_token = data.get("nextPageToken")
    if not page_token:
        break

print(f"\n✅ Finished. Total items retrieved: {len(all_items)}")

new_rows_df = pd.DataFrame()

# Stamp once for the whole run (consistent across all rows)
now = datetime.now()
run_date = now.strftime("%Y-%m-%d")
run_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

for i, eligibility_data in enumerate(all_items, start=1):
    subscriber = eligibility_data.get("subscriber", {})
    # print(subscriber.get("firstName", ""), subscriber.get("lastName", ""))
    # print("❓❓❓gender:", subscriber.get("gender", "No gender found"))

    # # check to find patients eligibility status
    # print("❓❓❓first status: ",
    #       eligibility_data.get("planStatus", [{}])[0].get("status", "No status found"))
     # Progress logging (avoid printing thousands of lines)
    if i % 100 == 0:
        print(f"Processed {i}/{len(all_items)} items...")

    benefits = eligibility_data.get("benefitsInformation", [])
    df = pd.json_normalize(
        benefits,
        sep=".",
        max_level=None
    )

    # If no benefits returned, or response shape is different, skip safely
    if df.empty:
        print(subscriber.get("firstName", ""), subscriber.get("lastName", ""))
        print("⚠️ No benefitsInformation rows returned")
        print("⚠️ errors:", eligibility_data.get("errors", []))
        continue

     # Optional: turn list-valued columns into pipe-joined strings for easier CSV/Excel viewing
    list_cols = [c for c in df.columns if df[c].apply(lambda x: isinstance(x, list)).any()]
    for c in list_cols:
        df[c] = df[c].apply(lambda x: "|".join(map(str, x)) if isinstance(x, list) else x)

    # 🔹 Build full name
    full_name = " ".join(
        filter(None, [
            subscriber.get("firstName"),
            subscriber.get("middleName"),
            subscriber.get("lastName")
        ])
    ).strip() or "No name found"

    df["run_date"] = run_date
    df["run_timestamp"] = run_timestamp

    # Append column and move to front
    df["patient_name"] = full_name
    df["submitterTransactionIdentifier"] = eligibility_data.get("submitterTransactionIdentifier", "")
    df["batchId"] = eligibility_data.get("batchId", "")
    df["eligibilitySearchId"] = eligibility_data.get("eligibilitySearchId", "")
    df["memberId"] = subscriber.get("memberId", "")
    df["gender"] = subscriber.get("gender", "")
    df["planStatus_0_status"] = eligibility_data.get("planStatus", [{}])[0].get("status", "")


    # Move key columns to front
    front = [
        "patient_name",
        "memberId",
        "submitterTransactionIdentifier",
        "batchId",
        "eligibilitySearchId",
        "gender",
        "planStatus_0_status",
        "run_date",
        "run_timestamp",
    ]
    df = df[front + [c for c in df.columns if c not in front]]

    # ✅ Only filter by code if the column exists
    if "code" in df.columns and "serviceTypeCodes" in df.columns:
        df = df[df["code"].astype(str).isin(["1", "2", "3", "4", "5"])]
        # removes rows where "serviceTypeCodes" contains "88"
        df = df[~df["serviceTypeCodes"].astype(str).str.contains("88", na=False)]
    else:
        print("⚠️ 'code' or 'serviceTypeCodes' column missing; available columns:", df.columns.tolist())
        print("⚠️ errors:", eligibility_data.get("errors", []))
        continue  # omit this if you want to keep unfiltered rows

     # Normalize types for consistent concatenation across runs
    # df = df.astype(str)
    df = df.fillna("").astype(str)  # Replace NaN with empty string for better CSV handling
    
    ''' for each patient after it pulls the benefitsInformation, it formats the data into a temp var 'df' and appends to 'new_rows_df'
    which is then concatenated with existing_df (the old csv) and written back to the csv'''
    new_rows_df = pd.concat([new_rows_df, df], ignore_index=True)

print("✅ new data final row count:", len(new_rows_df))

out_path = "MA_medicaid_eligibility_results.csv"

if os.path.exists(out_path):
    existing_df = pd.read_csv(out_path, dtype=str)  # dtype=str prevents type-mismatch issues
else:
    existing_df = pd.DataFrame()

# key columns to front
front = [
    "patient_name",
    "memberId",
    "submitterTransactionIdentifier",
    "batchId",
    "eligibilitySearchId",
    "gender",
    "planStatus_0_status",
    "run_date",
    "run_timestamp",
]
# 2) Then add all other columns in the order they appear in new_rows_df
remaining_cols = [c for c in new_rows_df.columns if c not in front]

# 3) Include any legacy columns from existing_df that aren't already included
legacy_cols = [c for c in existing_df.columns if c not in front + remaining_cols]
all_cols = front + remaining_cols + legacy_cols
existing_df = existing_df.reindex(columns=all_cols)
new_rows_df = new_rows_df.reindex(columns=all_cols)

final_df = pd.concat([existing_df, new_rows_df], ignore_index=True)

final_df.to_csv(out_path, index=False)

print(f"✅ existing datatable rows {len(existing_df)} rows.")
print(f"✅ Added {len(new_rows_df)} new rows.")
print(f"✅ Total rows now: {len(final_df)}")
print("✅ Wrote:", os.path.abspath(out_path))