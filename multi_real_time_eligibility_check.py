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
user_excel_data = pd.read_csv('Ohio_UnitedHealth/rebill_ohio_27Feb26.csv').to_dict(orient='records')

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
    )

    # Current datetime
    now = datetime.now()
    # Format however you prefer
    run_date = now.strftime("%Y-%m-%d")          # 2026-02-27
    run_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")  # 2026-02-27 14:32:08

    df["run_date"] = run_date
    df["run_timestamp"] = run_timestamp

    # Append column and move to front
    df["patient_name"] = full_name
    df = df[["patient_name", "run_date", "run_timestamp"] + [c for c in df.columns if c != "patient_name"]]


    # ✅ Only filter by code if the column exists
    if "code" in df.columns:
        df = df[df["code"].astype(str) == "1"]
    else:
        print("⚠️ 'code' column missing; available columns:", df.columns.tolist())
        print("⚠️ errors:", eligibility_data.get("errors", []))
        continue  # or omit this to export unfiltered rows

    # Append to CSV instead of overwriting
    out_path = "benefitsInformation_flat.csv"
    write_header = not os.path.exists(out_path)


    df.to_csv(out_path,
            index=False,
            mode='a',
            header=write_header)
    # if eligibility_data.get("planStatus", [{}])[0].get("status", "No status found") != "Inactive":
    #     print("✅ Success Medicaid eligibility found")
       