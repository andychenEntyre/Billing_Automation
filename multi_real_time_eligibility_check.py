import json
import re
import warnings
warnings.filterwarnings(
    "ignore",
    message="urllib3 v2 only supports OpenSSL",
)

import requests
import pandas as pd
from datetime import datetime
import os


# user_excel_data = pd.read_csv('Ohio_UnitedHealth/howard_resubmit_UHC_ID.csv').to_dict(orient='records')
user_excel_data = pd.read_csv('Ohio_UnitedHealth/rebill_ohio_27Feb26 copy.csv').to_dict(orient='records')

out_path = "benefitsInformation_flat.csv"

if os.path.exists(out_path):
    existing_df = pd.read_csv(out_path, dtype=str)  # dtype=str prevents type-mismatch issues
else:
    existing_df = pd.DataFrame()

new_rows_df = pd.DataFrame()

for user in user_excel_data:
    print("\n\n")
    print("===================================")
    # print(user)
    # print(re.sub(r'[^A-Za-z0-9\- ]', '', str(user.get('user_Medicaid ID')).strip()))
    print("\n")
    url = "https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/eligibility/v3"
    #TODO need to automate this trading partner service id code input
    body = {
      "provider": {
        "npi": "1245675776",
        "organizationName": "ENTYRE CARE MASSACHUSETTS INC"
      },
      "subscriber": {
        "firstName": str(user.get('user_Name').split()[0]),
        "lastName": str(user.get('user_Name').split()[1]),
        #TODO
        "memberId": re.sub(r'[^A-Za-z0-9\- ]', '', str(user.get('Medicaid ID')).strip())
      },
      #TODO this if more Medicaid eligibility
      #MA medicaid= KWDBT
      #Ohio medicaid= SMZIL
      #UHC = KMQTZ
      #UHC Medicaid managed care entity= HSVNU
      "tradingPartnerServiceId": "SMZIL"
      # "tradingPartnerServiceId": str(user.get('response_tradingPartnerServiceId'))
    }
    response = requests.request("POST", url, json = body, headers = {
      "Authorization": "RYnvhqL.0X6jgBc6ewt5N7v2ILnQtiGy",
      "Content-Type": "application/json"
    })
    eligibility_data = response.json()
    # print(eligibility_data)
    # print(json.dumps(eligibility_data, indent=2))
    benefits = eligibility_data.get("benefitsInformation", [])

    print(user["user_Name"])
    print("❓❓❓gender:", eligibility_data.get("subscriber", {}).get("gender", "No gender found"))
    '''check to find patients eligibility status''' 
    print("❓❓❓first status: ", eligibility_data.get("planStatus", [{}])[0].get("status", "No status found"))

    df = pd.json_normalize(
        benefits,
        sep=".",
        max_level=None
    )
    # If no benefits returned, or response shape is different, skip safely
    if df.empty:
        print("⚠️ No benefitsInformation rows returned")
        print("⚠️ errors:", eligibility_data.get("errors", []))
        continue

    # Optional: turn list-valued columns into pipe-joined strings for easier CSV/Excel viewing
    list_cols = [c for c in df.columns if df[c].apply(lambda x: isinstance(x, list)).any()]
    for c in list_cols:
        df[c] = df[c].apply(lambda x: "|".join(map(str, x)) if isinstance(x, list) else x)

    # 🔹 Build full name
    subscriber = eligibility_data.get("subscriber", {})
    full_name = " ".join(
        filter(None, [
            subscriber.get("firstName"),
            subscriber.get("middleName"),
            subscriber.get("lastName")
        ])
    ).strip()
    if not full_name:
        full_name = "No name found"

    # Current datetime
    now = datetime.now()
    run_date = now.strftime("%Y-%m-%d")          # 2026-02-27
    run_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")  # 2026-02-27 14:32:08

    df["run_date"] = run_date
    df["run_timestamp"] = run_timestamp

    # Append column and move to front
    df["patient_name"] = full_name
    front = ["patient_name", "run_date", "run_timestamp"]
    df = df[front + [c for c in df.columns if c not in front]]

    df = df.astype(str)  # Ensure all data is string type for consistent CSV output

    # ✅ Only filter by code if the column exists
    if "code" in df.columns:
        df = df[df["code"].astype(str) == "1"]
    else:
        print("⚠️ 'code' column missing; available columns:", df.columns.tolist())
        print("⚠️ errors:", eligibility_data.get("errors", []))
        continue  # or omit this to export unfiltered rows
    
    # Normalize types for consistent concatenation across runs
    df = df.astype(str)

    new_rows_df = pd.concat([new_rows_df, df], ignore_index=True)

# Preserve column order:
# 1) Start with your preferred front columns
front = ["patient_name", "run_date", "run_timestamp"]

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