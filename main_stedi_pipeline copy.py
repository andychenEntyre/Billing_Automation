import json
import re
import warnings
warnings.filterwarnings(
    "ignore",
    message="urllib3 v2 only supports OpenSSL",
)

import requests
import pandas as pd
import datetime

# manually set year and month here
YEAR = '2026'
MONTH = '01'

user_excel_data = pd.read_csv('Jan_stedi_billing_PT2.csv').to_dict(orient='records')
parsed_responses = []

for user in user_excel_data:
    print(user)
    print(str(user.get('Medicaid ID'))) #TODO need to add memberID to csv file before running this.
    print(re.sub(r'[^A-Za-z0-9\- ]', '', str(user.get('Medicaid ID')).strip()))
    print("\n")
    url = "https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/eligibility/v3"
    body = {
      "provider": {
        "npi": "1245675776",
        "organizationName": "ENTYRE CARE MASSACHUSETTS INC"
      },
      "subscriber": {
        "memberId": re.sub(r'[^A-Za-z0-9\- ]', '', str(user.get('Medicaid ID')).strip()) #TODO need to add memberID to csv file before running this.
      },
      #TODO check if tradingPartnerServiceId is correct
      "tradingPartnerServiceId": "SMZIL"
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
            try:
                qty = float(raw)
            except (TypeError, ValueError):
                continue
            if qty <= 0:
                print(col, "No matching charge amount for quantity:")
                continue

            if qty == 1:
                charge_amount = "102.68"
                # print(col, charge_amount)
            elif qty == 0.5:
                charge_amount = "51.34"
                # print(col, charge_amount)
            else:
                None   
            service_line_items.append({
                "professionalService": {
                    "compositeDiagnosisCodePointers": {"diagnosisCodePointers": ["1"]},
                    "lineItemChargeAmount": charge_amount,
                    "measurementUnit": "UN",
                    "procedureCode": "S5136",
                    "procedureIdentifier": "HC",
                    "procedureModifiers": [],
                    "serviceUnitCount": "1"
                },
                # "providerControlNumber": "1", #if empty string, stedi auto-generates one
                "renderingProvider": None,
                "serviceDate": f"{YEAR}{int(MONTH):02d}{n:02d}"
            })
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
            "benefitsAssignmentCertificationIndicator": "Y",
            "claimChargeAmount": user['Billed'].replace('$', '').replace(',', '').strip(),  #needs to be the total Billable amout from excel
            "claimFilingCode": "MC",
            "claimFrequencyCode": "1",
            "healthCareCodeInformation": [
              {
                "diagnosisCode": "R6889",
                "diagnosisTypeCode": "ABK"
              }
            ],
            "patientControlNumber": str(user.get('Hubspot ID', 'missing')), #todo hubspot RecordID
            "placeOfServiceCode": "12",
            "planParticipationCode": "A",
            "releaseInformationCode": "Y",
            "serviceFacilityLocation": None,
            #TODO Feb4th make sure "service_line_items" is populated and formated correctly from excel
            "serviceLines": service_line_items,
            "signatureIndicator": "Y"
          },
          "receiver": {
            "organizationName": "UnitedHealthcare"
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
            "subscriberGroupName": "UnitedHealthcare"
          },
          "tradingPartnerName": "UnitedHealthcare",
          "tradingPartnerServiceId": "87726",
          "usageIndicator": "P"
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
            print("✅✅✅", user["Name"], "SUBMISSION STATUS")
            # print("Response Errors:", errors)
            print(json.dumps(parsed, indent=2))
            parsed_responses.append({
                "user": {"Name": user.get("Name"), 
                "Medicaid ID": user.get("Medicaid ID")},
                "status_code": parsed.get("status"),
                "errors": parsed.get("errors"),
                "response": parsed
            })
        except ValueError:
            print("❌❌❌ Failed to parse JSON response")
    else:
        print("❌❌❌", user["Name"], "Medicaid eligibility not found")


flat_df = pd.json_normalize(data=parsed_responses,
                            sep='_')
flat_df.to_csv('stedi_jan_parsed_responses_full.csv', index=False)
