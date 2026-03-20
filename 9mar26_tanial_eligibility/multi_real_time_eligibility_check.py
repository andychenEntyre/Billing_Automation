import json
import re
from tkinter.font import names
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
# user_excel_data = pd.read_csv('Ohio_UnitedHealth/rebill_ohio_27Feb26.csv').to_dict(orient='records')
user_excel_data = pd.read_csv('/Users/Andy.Chen/Billing_Automation/9mar26_tanial_eligibility/MA Lost in App with Most Recent Appointment.csv').to_dict(orient='records')

#POC with Ohio UHC people
# out_path = "benefitsInformation_flat.csv"

out_path = "/Users/Andy.Chen/Billing_Automation/9mar26_tanial_eligibility/MA_lost_in_app_eligibility.csv"

if os.path.exists(out_path):
    existing_df = pd.read_csv(out_path, dtype=str)  # dtype=str prevents type-mismatch issues
else:
    existing_df = pd.DataFrame()

new_rows_df = pd.DataFrame()


def build_patient_name(user: dict) -> str:
    full_name = " ".join(
        filter(None, [
            str(user.get("Client First Name", "")).strip(),
            str(user.get("Client Last Name", "")).strip(),
        ])
    ).strip()
    return full_name or "No name found"


def build_fallback_row(user: dict, status: str, entity_names: str = "") -> pd.DataFrame:
    now = datetime.now()
    return pd.DataFrame([{
        "patient_name": build_patient_name(user),
        "run_date": now.strftime("%Y-%m-%d"),
        "run_timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "entity_names": entity_names,
        "status": status,
    }])

def extract_entity_names(benefit_row: dict) -> str:
    if benefit_row.get("name") != "Managed Care Coordinator":
        return ""

    names = []
    for entity in benefit_row.get("benefitsRelatedEntities", []) or []:
        name = entity.get("entityName")
        if name:
            names.append(name)

    entity = benefit_row.get("benefitsRelatedEntity") or {}
    name = entity.get("entityName")
    if name:
        names.append(name)
    unique_names = list(dict.fromkeys(names))
    return "+".join(unique_names)


def extract_managed_care_entity_names(benefits: list[dict]) -> str:
    names = []
    for benefit in benefits:
        entity_names = extract_entity_names(benefit)
        if entity_names:
            names.extend(entity_names.split("+"))

    unique_names = list(dict.fromkeys(names))
    return "+".join(unique_names)

def format_dob(dob_raw: str) -> str:
    dob_raw = str(dob_raw or "").strip()
    if not dob_raw or set(dob_raw) == {"#"}:
        return ""
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            parsed = datetime.strptime(dob_raw, fmt)
            if fmt == "%m/%d/%y" and parsed > datetime.now():
                parsed = parsed.replace(year=parsed.year - 100)
            return parsed.strftime("%Y%m%d")
        except ValueError:
            continue
    return ""


# for user in user_excel_data[50:80]:  # Limit to first 10 users for testing
for user in user_excel_data:
    print("\n\n")
    print("===================================")
    # print(user)
    # print(re.sub(r'[^A-Za-z0-9\- ]', '', str(user.get('user_Medicaid ID')).strip()))
    print("\n")
    url = "https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/eligibility/v3"
    if str(user.get('Client Mass Health Id')).strip() != "nan":
        #TODO need to automate this trading partner service id code input
        body = {
        "provider": {
            "npi": "1245675776",
            "organizationName": "ENTYRE CARE MASSACHUSETTS INC"
        },
        "subscriber": {
            "firstName": str(user.get('Client First Name')),
            "lastName": str(user.get('Client Last Name')),
            #TODO
            "memberId": re.sub(r'[^A-Za-z0-9\- ]', '', str(user.get('Client Mass Health Id')).strip())
        },
      #TODO this if more Medicaid eligibility
      #MA medicaid= KWDBT
      #Ohio medicaid= SMZIL
      #UHC = KMQTZ
      #UHC Medicaid managed care entity= HSVNU
      "tradingPartnerServiceId": "KWDBT"
      # "tradingPartnerServiceId": str(user.get('response_tradingPartnerServiceId'))
    }
    else:
        gender_raw = str(user.get('Client Gender', '')).strip().lower()
        gender_map = {
            "female": "F",
            "male": "M"
        }
        gender = gender_map.get(gender_raw, "")

        # dob_raw = str(user.get("Client Birthdate", "")).strip()
        # dob_formatted = ""
        # if dob_raw:
        #     dob_formatted = datetime.strptime(dob_raw, "%m/%d/%Y").strftime("%Y%m%d")
        dob_raw = str(user.get("Client Birthdate", "")).strip()
        dob_formatted = format_dob(dob_raw)
        
        body = {
        "provider": {
            "npi": "1245675776",
            "organizationName": "ENTYRE CARE MASSACHUSETTS INC"
        },
        "subscriber": {
            "dateOfBirth": dob_formatted,
            "firstName": str(user.get('Client First Name')),
            "lastName": str(user.get('Client Last Name')),
            "gender": gender
        },
      #TODO this if more Medicaid eligibility
      #MA medicaid= KWDBT
      #Ohio medicaid= SMZIL
      #UHC = KMQTZ
      #UHC Medicaid managed care entity= HSVNU
      "tradingPartnerServiceId": "KWDBT"
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

    print(user["Client First Name"], user["Client Last Name"])
    print("❓❓❓gender:", eligibility_data.get("subscriber", {}).get("gender", "No gender found"))
    print("❓❓❓first status: ", eligibility_data.get("planStatus", [{}])[0].get("status", "No status found"))
    print(body)

    df = pd.json_normalize(
        benefits,
        sep=".",
        max_level=None
    )

    # If no benefits returned, or response shape is different, skip safely
    if df.empty:
        print("⚠️ No benefitsInformation rows returned")
        print("⚠️ errors:", eligibility_data.get("errors", []))
        empty_row = build_fallback_row(user, "No benefitsInformation returned")
        df = df.fillna("").astype(str)
        new_rows_df = pd.concat([new_rows_df, empty_row], ignore_index=True)

        continue

    # Keep managed care coordinator names even if that benefit row is later filtered out
    managed_care_entity_names = extract_managed_care_entity_names(benefits)
    df["entity_names"] = managed_care_entity_names

    # Optional: turn list/dict-valued columns into strings for easier CSV/Excel viewing
    complex_cols = [
        c for c in df.columns
        if df[c].apply(lambda x: isinstance(x, (list, dict))).any()
    ]

    for c in complex_cols:
        df[c] = df[c].apply(
            lambda x: "|".join(map(str, x)) if isinstance(x, list)
            else json.dumps(x, ensure_ascii=False) if isinstance(x, dict)
            else x
        )

    # Build full name
    full_name = build_patient_name(user)

    # Current datetime
    now = datetime.now()
    run_date = now.strftime("%Y-%m-%d")
    run_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    df["run_date"] = run_date
    df["run_timestamp"] = run_timestamp

    # Append column and move to front
    df["patient_name"] = full_name
    front = ["patient_name", "run_date", "run_timestamp", "entity_names"]
    df = df[front + [c for c in df.columns if c not in front]]

    # Ensure all data is string type for consistent CSV output
    # df = df.astype(str)
    df = df.fillna("").astype(str)

    # Only filter by code if the column exists
    if "code" in df.columns and "serviceTypeCodes" in df.columns:
        df = df[df["code"].astype(str).isin(["1", "2", "3", "4", "5"])]
        # removes rows where "serviceTypeCodes" contains "88"
        df = df[~df["serviceTypeCodes"].astype(str).str.contains("88", na=False)]
        df = df[~df["serviceTypeCodes"].astype(str).str.contains("54", na=False)]
        if df.empty:
            print("⚠️ All benefit rows were filtered out")
            filtered_row = build_fallback_row(
                user,
                "All benefits filtered out",
                managed_care_entity_names,
            )
            new_rows_df = pd.concat([new_rows_df, filtered_row], ignore_index=True)
            continue
    else:
        print("⚠️ 'code' column missing; available columns:", df.columns.tolist())
        print("⚠️ errors:", eligibility_data.get("errors", []))
        missing_code_row = build_fallback_row(
            user,
            "Missing code/serviceTypeCodes columns",
            managed_care_entity_names,
        )
        new_rows_df = pd.concat([new_rows_df, missing_code_row], ignore_index=True)
        continue

    # Normalize types for consistent concatenation across runs
    df = df.astype(str)

    new_rows_df = pd.concat([new_rows_df, df], ignore_index=True)

    # Preserve column order:
    front = ["patient_name", "run_date", "run_timestamp", "entity_names"]

    remaining_cols = [c for c in new_rows_df.columns if c not in front]
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
