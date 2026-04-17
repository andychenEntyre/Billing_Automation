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
from nanoid import generate

# manually set year and month here
YEAR = '2026'
MONTH = '03'

PCN_LENGTH = 17
PCN_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

state = dict
insurance = dict

USAGE_INDICATOR = "T"

#MA medicaid = "KWDBT"
#OH medicaid = "SMZIL"
MEDICAID_BY_STATE = "SMZIL"
#MA - S5140
#OH - S5136
procedure_code = "S5136"
#MA - Z741
#OH - R6889
diagnosis_code = "R6889"

# user_excel_data = pd.read_csv('MA_Molina/molina_feb_12.csv').to_dict(orient='records')
# user_excel_data = pd.read_csv('/Users/Andy.Chen/Billing_Automation/MA_Molina/11March26_feb_billing.csv').to_dict(orient='records')
# user_excel_data = pd.read_csv('/Users/Andy.Chen/Billing_Automation/Ohio_UnitedHealth/20march26_molinaOH.csv').to_dict(orient='records')
# user_excel_data = pd.read_csv('/Users/Andy.Chen/Billing_Automation/MA_Molina/March26_Molina_Stedi.csv').to_dict(orient='records')
# user_excel_data = pd.read_csv('/Users/Andy.Chen/Billing_Automation/mycare_march_flowsheets/March_MyCare_billing.csv',
#                               encoding='cp1252').to_dict(orient='records')
user_excel_data = pd.read_csv('/Users/Andy.Chen/Billing_Automation/Ohio_flowsheets/17april_mycare_missing_medicaid_billing.csv').to_dict(orient='records')

if not user_excel_data:
    raise ValueError("Input file has no rows.")

required_columns = ["Medicaid ID", "Billable"]
available_columns = list(user_excel_data[0].keys())
missing_columns = [col for col in required_columns if col not in available_columns]
if missing_columns:
    print(f"❌❌❌ ERROR: Missing required columns: {missing_columns}")
    print(f"Available columns in CSV: {available_columns}")
    raise ValueError(f"Required column '{missing_columns[0]}' not found in CSV. Please check column names.")

parsed_responses = []
used_patient_control_numbers = set()


def new_patient_control_number(existing):
    while True:
        pcn = generate(PCN_ALPHABET, PCN_LENGTH)
        if pcn not in existing:
            existing.add(pcn)
            return pcn
        
def get_payer_info(plan_name):
    plan_name = str(plan_name).strip().lower()

    if plan_name == 'anthem':
        return "Anthem Blue Cross Blue Shield MyCare Ohio", "RVDFM"
    elif plan_name == 'caresource':
        return "Next Generation MyCare Ohio - CareSource", "XENXY"
    elif plan_name == 'molina':
        return "Next Generation MyCare Ohio - Molina", "DAQUG"
    #TODO waiting for Aetna and United stedi enrollment
    return None, None

for user in user_excel_data:
    client_name = user.get("Name") or user.get("Deal Name") or user.get("user_Name") or "Unknown user"
    medicaid_insurance_plan = user.get("Medicaid Insurance Plan-")
    billable_amount = user.get("Billable")
    audit_base = {
      "medicaid_insurance_plan": medicaid_insurance_plan,
      "billable_amount": billable_amount,
      "user": {
        "Name": client_name,
        "Medicaid ID": user.get("Medicaid ID"),
        "public_id": user.get("public_id", "missing")
      }
    }
    payerName, STEDI_PAYER_ID = get_payer_info(user.get('Medicaid Insurance Plan-'))

    if not payerName or not STEDI_PAYER_ID:
      print(f"❌ Unknown payer for user {user.get('Name')}: {user.get('Medicaid Insurance Plan-')}")
      parsed_responses.append({
        **audit_base,
        "outcome": "skipped",
        "stage": "payer",
        "reason": f"Unknown payer: {user.get('Medicaid Insurance Plan-')}",
        "status_code": "skipped",
        "patient_control_number": None,
        "errors": [{
          "code": "UNKNOWN_PAYER",
          "message": f"Unknown payer: {user.get('Medicaid Insurance Plan-')}"
        }],
        "response": None
      })
      continue

    medicaid_id = re.sub(r'[^A-Za-z0-9\- ]', '', str(user.get('Medicaid ID', '')).strip())
    print(user)
    print(medicaid_id)
    print("\n")
    
    url = "https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/eligibility/v3"
    body = {
      "provider": {
        "npi": "1245675776",
        "organizationName": "ENTYRE CARE MASSACHUSETTS INC"
      },
      "subscriber": {
        #TODO need to add memberID to csv file before running this.
        "memberId": medicaid_id
      },
      #TODO this if more Medicaid eligibility
      "tradingPartnerServiceId": MEDICAID_BY_STATE
    }
    response = requests.request("POST", url, json = body, headers = {
      "Authorization": "RYnvhqL.0X6jgBc6ewt5N7v2ILnQtiGy",
      "Content-Type": "application/json"
    })
    eligibility_data = response.json()
    # print(json.dumps(eligibility_data, indent=2))
    print("❓❓❓gender:", eligibility_data.get("subscriber", {}).get("gender", "No gender found"))
    '''check to find patients eligibility status''' 
    print("❓❓❓first status: ", eligibility_data.get("planStatus", [{}])[0].get("status", "No status found"))
    if eligibility_data.get("planStatus", [{}])[0].get("status", "No status found") != "Inactive":
        print("✅ Success Medicaid eligibility found")

        # build serviceLines from D1..D31 for this user
        service_line_items = []
        for n in range(1, 32):
            col = f"D{n}"
            raw = user.get(col)
            if raw is None or pd.isna(raw):
                continue

            raw_str = str(raw).strip().lower()
            if raw_str in {"full day", "full"}:
                qty = 1.0
            elif raw_str in {"half day", "half"}:
                qty = 0.5
            else:
                try:
                    qty = float(raw)
                except (TypeError, ValueError):
                    continue

            try:
                qty = float(qty)
            except (TypeError, ValueError):
                continue
            if qty <= 0:
                print(col, "No matching charge amount for quantity:")
                continue
            #TODO make more robust
            if qty == 1:
                # charge_amount = str(user["Rate"]).replace('$', '').strip()
                charge_amount = "102.68"
                # print(col, charge_amount)
            elif qty == 0.5:
                charge_amount = "51.34"
                # print(col, charge_amount)
            else:
                continue

            modifier = user.get("Modifier")
            procedure_modifier = []
            if modifier is not None and not pd.isna(modifier):
                modifier = str(modifier).strip()
                if modifier:
                  procedure_modifier = [m.strip() for m in modifier.split(":") if m.strip()]

            service_line_items.append({
                "professionalService": {
                    "compositeDiagnosisCodePointers": {"diagnosisCodePointers": ["1"]},
                    "lineItemChargeAmount": charge_amount,
                    "measurementUnit": "UN",
                    "procedureCode": procedure_code,
                    "procedureIdentifier": "HC",
                    "procedureModifiers": procedure_modifier,
                    "serviceUnitCount": "1"
                },
                # "providerControlNumber": "1", #if empty string, stedi auto-generates one
                "renderingProvider": None,
                "serviceDate": f"{YEAR}{int(MONTH):02d}{n:02d}"
            })

        if not service_line_items:
            print("❌❌❌", user.get("Name", "Unknown user"), "has no billable service lines; skipping claim submission")
            parsed_responses.append({
                **audit_base,
                "outcome": "skipped",
                "stage": "service_lines",
                "reason": "No billable D1-D31 values",
                "status_code": "skipped",
                "patient_control_number": None,
                "errors": [{
                    "code": "NO_SERVICE_LINES",
                    "message": "No positive D1-D31 values were found for this claim."
                }],
                "response": {
                    "claimInformation": {
                        "serviceLines": []
                    }
                }
            })
            continue

        # print("✅ Service line items built:", service_line_items)
        patient_control_number = new_patient_control_number(used_patient_control_numbers)

        pulled = {
          "billing": {
            "address": {
              "address1": "218 Shove St",
              "address2": None,
              "city": "Fall River",
              "postalCode": "027242068",
              "state": "MA"
            },
            "contactInformation": {
              "name": "ENTYRE CARE MASSACHUSETTS INC",
              "phoneNumber": "6147218413" 
            },
            "employerId": "462744465",
            "npi": "1245675776",
            "organizationName": "ENTYRE CARE MASSACHUSETTS INC",
            "providerType": "BillingProvider",
            "taxonomyCode": None
          },
          "claimInformation": {
            "claimSupplementalInformation": {
              # "claimControlNumber": str(user['supplement_control_number']),
              "priorAuthorizationNumber": str(user['Prior Auth #'])
              if str(user.get('Prior Auth #', '')).strip().lower() != "unknown"
              else None
            },
            "benefitsAssignmentCertificationIndicator": "Y",
            "claimChargeAmount": str(user['Billable']).replace('$', '').replace(',', '').strip(),  #needs to be the total Billable amout from excel
            "claimFilingCode": "MC",
            "claimFrequencyCode": "1",
            "healthCareCodeInformation": [
              {
                "diagnosisCode": diagnosis_code,
                "diagnosisTypeCode": "ABK"
              }
            ],
            "patientControlNumber": patient_control_number,
            "placeOfServiceCode": "12",
            "planParticipationCode": "A",
            "releaseInformationCode": "Y",
            "serviceFacilityLocation": None,
            "serviceLines": service_line_items,
            "signatureIndicator": "Y"
          },
          "receiver": {
            "organizationName": payerName
          },
          "submitter": {
            "contactInformation": {
              "name": "ENTYRE CARE MASSACHUSETTS INC",
              "phoneNumber": "6147218413" 
            },
            "organizationName": "ENTYRE CARE MASSACHUSETTS INC",
            "submitterIdentification": "1245675776"
          },
          "subscriber": {
            "address": {
              "address1": eligibility_data.get("subscriber", {}).get("address", {}).get("address1", ""),
              "city": eligibility_data.get("subscriber", {}).get("address", {}).get("city", ""),
              "postalCode": eligibility_data.get("subscriber", {}).get("address", {}).get("postalCode", ""),
              "state": eligibility_data.get("subscriber", {}).get("address", {}).get("state", "")
            },
            "dateOfBirth": eligibility_data.get("subscriber", {}).get("dateOfBirth", ""),
            "firstName": eligibility_data.get("subscriber", {}).get("firstName", ""),
            "gender": eligibility_data.get("subscriber", {}).get("gender", ""),
            "groupNumber": None,
            "lastName": eligibility_data.get("subscriber", {}).get("lastName", ""),
            "memberId": eligibility_data.get("subscriber", {}).get("memberId", ""),
            "paymentResponsibilityLevelCode": "P",
            #TODO check if subscriberGroupName is correct
            "subscriberGroupName": payerName,
          },
          #TODO check if tradingPartnerName and tradingPartnerServiceId are correct
          "tradingPartnerName": payerName,
          "tradingPartnerServiceId": STEDI_PAYER_ID,
          "usageIndicator": USAGE_INDICATOR
        }
        url = "https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/professionalclaims/v3/submission"
        body = pulled
        response = requests.request(
          "POST",
          url,
          json=body,
          headers={
            "Authorization": "RYnvhqL.0X6jgBc6ewt5N7v2ILnQtiGy",
            "Content-Type": "application/json"
          }
        )
        # print(response.text)
        try:
            parsed = response.json()
            errors = parsed.get("errors", [])
            status_value = str(parsed.get("status", "")).strip()
            is_success = status_value.lower() == "success"
            print("🌀🌀🌀", user["user_Name"], "SUBMISSION STATUS")
            # print("Response Errors:", errors)
            if not is_success:
              print(json.dumps(parsed, indent=2))
            parsed_responses.append({
                **audit_base,
                "outcome": "success" if is_success else "failed",
                "stage": "submission",
                "reason": "Claim submitted" if is_success else "Medicaid returned non-success status",
                "patient_control_number": patient_control_number,
                "status_code": status_value,
                "errors": parsed.get("errors"),
                "response": parsed
            })
        except ValueError:
            print("❌❌❌ Failed to parse JSON response")
            parsed_responses.append({
                **audit_base,
                "outcome": "failed",
                "stage": "parse",
                "reason": "Failed to parse JSON response",
                "patient_control_number": patient_control_number,
                "status_code": str(response.status_code),
                "errors": [{
                    "code": "RESPONSE_PARSE_ERROR",
                    "message": "Failed to parse JSON response"
                }],
                "response": response.text
            })
    else:
        print("❌❌❌", user["Name"], "Medicaid eligibility not found")
        parsed_responses.append({
            **audit_base,
            "outcome": "failed",
            "stage": "eligibility",
            "reason": "Medicaid eligibility not found (Inactive)",
            "status_code": "ineligible",
            "patient_control_number": None,
            "errors": [{
                "code": "ELIGIBILITY_INACTIVE",
                "message": "Eligibility status was Inactive"
            }],
            "response": eligibility_data
        })


flat_df = pd.json_normalize(data=parsed_responses,
                            sep='_')

# More readable timestamp
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
mode_prefix = "TEST" if str(USAGE_INDICATOR).strip().upper() == "T" else "PROD"
filename = f"{mode_prefix}_stedi_parsed_responses_{timestamp}.csv"
flat_df['date_time'] = timestamp
# flat_df['medicaid_state'] = 
# flat_df['Medicaid_ID'] = re.sub(r'[^A-Za-z0-9\- ]', '', str(user.get('Medicaid ID')).strip())

output_dir = "submission_log"
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, filename)
flat_df.to_csv(output_path, index=False)
print(f"✅✅✅ Parsed responses saved to {output_path}")
