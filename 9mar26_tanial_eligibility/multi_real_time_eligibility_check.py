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
# user_excel_data = pd.read_csv('/Users/Andy.Chen/Billing_Automation/9mar26_tanial_eligibility/MA Lost in App with Most Recent Appointment.csv').to_dict(orient='records')
# user_excel_data = pd.read_csv('/Users/Andy.Chen/Billing_Automation/9mar26_tanial_eligibility/24march26_MA_leads.csv').to_dict(orient='records')
user_excel_data = pd.read_csv('/Users/Andy.Chen/Billing_Automation/9mar26_tanial_eligibility/26march26_MA_leads_NO_DEMO.csv').to_dict(orient='records')

#POC with Ohio UHC people
# out_path = "benefitsInformation_flat.csv"

out_path = "/Users/Andy.Chen/Billing_Automation/9mar26_tanial_eligibility/test.csv"

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


def extract_client_identity(user: dict) -> dict:
    return {
        "client_public_id": str(user.get("Client Public Id", "") or "").strip(),
        "client_mass_health_id": str(user.get("Client Mass Health Id", "") or "").strip(),
        "client_birthdate": str(user.get("Client Birthdate", "") or "").strip(),
        "most_recent_appointment_scheduled_date_time": str(
            user.get("Most Recent Appointment Scheduled Date Time", "") or ""
        ).strip(),
    }


def build_fallback_row(
    user: dict,
    status: str,
    entity_names: str = "",
    lookup_gender: str = "",
) -> pd.DataFrame:
    now = datetime.now()
    identity = extract_client_identity(user)
    return pd.DataFrame([{
        "patient_name": build_patient_name(user),
        "client_public_id": identity["client_public_id"],
        "client_mass_health_id": identity["client_mass_health_id"],
        "client_birthdate": identity["client_birthdate"],
        "most_recent_appointment_scheduled_date_time": identity[
            "most_recent_appointment_scheduled_date_time"
        ],
        "run_date": now.strftime("%Y-%m-%d"),
        "run_timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "entity_names": entity_names,
        "lookup_gender": lookup_gender,
        "status": status,
    }])


def extract_plan_status(eligibility_data: dict) -> str:
    plan_status = eligibility_data.get("planStatus", [])
    if isinstance(plan_status, list) and plan_status:
        return str(plan_status[0].get("status", "") or "")
    return ""


def errors_to_string(eligibility_data: dict) -> str:
    errors = eligibility_data.get("errors", [])
    if not errors:
        return ""
    if isinstance(errors, (list, dict)):
        return json.dumps(errors, ensure_ascii=False)
    return str(errors)


def build_fallback_metadata(
    eligibility_data: dict,
    lookup_method: str,
    status_code: str,
    status_message: str,
    status_detail: str,
) -> dict:
    plan_status = extract_plan_status(eligibility_data)
    return {
        "status_code": status_code,
        "status_message": status_message,
        "status_detail": status_detail,
        "lookup_method": lookup_method,
        "plan_status": plan_status,
        "api_errors": errors_to_string(eligibility_data),
    }


def build_fallback_row_with_metadata(
    user: dict,
    status: str,
    metadata: dict,
    entity_names: str = "",
    lookup_gender: str = "",
) -> pd.DataFrame:
    fallback_row = build_fallback_row(user, status, entity_names, lookup_gender)
    for key, value in metadata.items():
        fallback_row[key] = str(value or "")
    return fallback_row

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
    print("\n")

    url = "https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/eligibility/v3"
    mass_health_id_raw = str(user.get("Client Mass Health Id", "")).strip()
    mass_health_member_id = re.sub(r"[^A-Za-z0-9\- ]", "", mass_health_id_raw)
    has_mass_health_id = bool(mass_health_member_id) and mass_health_member_id.lower() != "nan"

    attempts = []
    if has_mass_health_id:
        attempts.append({
            "lookup_method": "member_id",
            "lookup_gender": "",
            "dob_formatted": "",
            "body": {
                "provider": {
                    "npi": "1245675776",
                    "organizationName": "ENTYRE CARE MASSACHUSETTS INC"
                },
                "subscriber": {
                    "memberId": mass_health_member_id
                },
                "tradingPartnerServiceId": "KWDBT"
            }
        })
    else:
        gender_raw = str(user.get("Client Gender", "") or "").strip().lower()
        gender_map = {
            "female": "F",
            "male": "M",
            "f": "F",
            "m": "M",
        }
        normalized_gender = gender_map.get(gender_raw, "")
        gender_is_empty = not gender_raw or gender_raw == "nan"
        gender_candidates = ["F", "M"] if gender_is_empty else [normalized_gender]

        dob_raw = str(user.get("Client Birthdate", "")).strip()
        dob_formatted = format_dob(dob_raw)

        for gender in gender_candidates:
            attempts.append({
                "lookup_method": "demographics",
                "lookup_gender": gender,
                "dob_formatted": dob_formatted,
                "body": {
                    "provider": {
                        "npi": "1245675776",
                        "organizationName": "ENTYRE CARE MASSACHUSETTS INC"
                    },
                    "subscriber": {
                        "dateOfBirth": dob_formatted,
                        "firstName": str(user.get("Client First Name")),
                        "lastName": str(user.get("Client Last Name")),
                        "gender": gender,
                    },
                    "tradingPartnerServiceId": "KWDBT"
                }
            })

    for attempt in attempts:
        lookup_method = attempt["lookup_method"]
        lookup_gender = attempt["lookup_gender"]
        dob_formatted = attempt["dob_formatted"]
        body = attempt["body"]

        response = requests.request("POST", url, json=body, headers={
            "Authorization": "RYnvhqL.0X6jgBc6ewt5N7v2ILnQtiGy",
            "Content-Type": "application/json"
        })
        eligibility_data = response.json()
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
            has_errors = bool(eligibility_data.get("errors", []))
            status_code = "NO_BENEFITS_AND_API_ERRORS" if has_errors else "NO_BENEFITS_NO_ERRORS"
            status_message = (
                "No benefitsInformation returned; API reported errors"
                if has_errors
                else "No benefitsInformation returned; API returned no errors"
            )
            if lookup_method == "member_id":
                lookup_detail = f"member_id={mass_health_member_id or 'missing'}"
            else:
                lookup_detail = (
                    "first_name={first_name},last_name={last_name},dob={dob},gender={gender}".format(
                        first_name=str(user.get("Client First Name", "") or "").strip() or "missing",
                        last_name=str(user.get("Client Last Name", "") or "").strip() or "missing",
                        dob=dob_formatted or "missing",
                        gender=lookup_gender or "missing",
                    )
                )
            status_detail = (
                f"{lookup_detail}; plan_status={extract_plan_status(eligibility_data) or 'missing'}; "
                f"error_count={len(eligibility_data.get('errors', []) or [])}"
            )
            metadata = build_fallback_metadata(
                eligibility_data=eligibility_data,
                lookup_method=lookup_method,
                status_code=status_code,
                status_message=status_message,
                status_detail=status_detail,
            )
            empty_row = build_fallback_row_with_metadata(
                user,
                status_message,
                metadata,
                lookup_gender=lookup_gender,
            )
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

        full_name = build_patient_name(user)
        client_identity = extract_client_identity(user)

        now = datetime.now()
        run_date = now.strftime("%Y-%m-%d")
        run_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

        df["run_date"] = run_date
        df["run_timestamp"] = run_timestamp
        df["patient_name"] = full_name
        df["client_public_id"] = client_identity["client_public_id"]
        df["client_mass_health_id"] = client_identity["client_mass_health_id"]
        df["client_birthdate"] = client_identity["client_birthdate"]
        df["most_recent_appointment_scheduled_date_time"] = client_identity[
            "most_recent_appointment_scheduled_date_time"
        ]
        df["lookup_gender"] = lookup_gender

        front = [
            "patient_name",
            "client_public_id",
            "client_mass_health_id",
            "client_birthdate",
            "most_recent_appointment_scheduled_date_time",
            "run_date",
            "run_timestamp",
            "entity_names",
            "lookup_gender",
        ]
        df = df[front + [c for c in df.columns if c not in front]]

        df = df.fillna("").astype(str)

        # Only filter by code if the column exists
        if "code" in df.columns and "serviceTypeCodes" in df.columns:
            before_filter_count = len(df)
            df = df[df["code"].astype(str).isin(["1", "2", "3", "4", "5"])]
            df = df[~df["serviceTypeCodes"].astype(str).str.contains("88", na=False)]
            df = df[~df["serviceTypeCodes"].astype(str).str.contains("54", na=False)]
            if df.empty:
                print("⚠️ All benefit rows were filtered out")
                status_message = "All benefits filtered out by service code rules"
                status_detail = (
                    f"before_filter_rows={before_filter_count}; rules=code in [1-5],"
                    "exclude serviceTypeCodes containing 88 or 54"
                )
                metadata = build_fallback_metadata(
                    eligibility_data=eligibility_data,
                    lookup_method=lookup_method,
                    status_code="ALL_BENEFITS_FILTERED_OUT",
                    status_message=status_message,
                    status_detail=status_detail,
                )
                filtered_row = build_fallback_row_with_metadata(
                    user,
                    status_message,
                    metadata,
                    managed_care_entity_names,
                    lookup_gender,
                )
                new_rows_df = pd.concat([new_rows_df, filtered_row], ignore_index=True)
                continue
        else:
            print("⚠️ 'code' column missing; available columns:", df.columns.tolist())
            print("⚠️ errors:", eligibility_data.get("errors", []))
            missing_columns = [c for c in ["code", "serviceTypeCodes"] if c not in df.columns]
            status_message = "Missing expected benefits columns"
            status_detail = (
                f"missing_columns={','.join(missing_columns) or 'none'}; "
                f"available_columns={','.join(df.columns.tolist())}"
            )
            metadata = build_fallback_metadata(
                eligibility_data=eligibility_data,
                lookup_method=lookup_method,
                status_code="MISSING_EXPECTED_COLUMNS",
                status_message=status_message,
                status_detail=status_detail,
            )
            missing_code_row = build_fallback_row_with_metadata(
                user,
                status_message,
                metadata,
                managed_care_entity_names,
                lookup_gender,
            )
            new_rows_df = pd.concat([new_rows_df, missing_code_row], ignore_index=True)
            continue

        # Keep one row per attempt: first row after filters
        df = df.head(1).astype(str)
        new_rows_df = pd.concat([new_rows_df, df], ignore_index=True)

    # Preserve column order:
    front = [
        "patient_name",
        "client_public_id",
        "client_mass_health_id",
        "client_birthdate",
        "most_recent_appointment_scheduled_date_time",
        "run_date",
        "run_timestamp",
        "entity_names",
        "lookup_gender",
    ]

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
