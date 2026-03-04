import pandas as pd
import json
import re
import requests

df = pd.read_csv("/Users/Andy.Chen/Billing_Automation/ERA_check/04March2026_stedi.csv")

list_transactionIds = []
for i, row in df.iterrows():
    s = row["data"]

    if pd.isna(s):
        continue

    # If the CSV stored it with surrounding quotes, trim whitespace
    s = str(s).strip()

    # Normalize python-ish tokens to JSON-ish
    s = re.sub(r"\bNone\b", "null", s)
    s = re.sub(r"\bTrue\b", "true", s)
    s = re.sub(r"\bFalse\b", "false", s)
    s = re.sub(r"\bNaN\b|\bnan\b", "null", s)

    # Convert single quotes to double quotes (works if there are no embedded apostrophes in values)
    s = s.replace("'", '"')

    try:
        data = json.loads(s)
        transactionId = data["event"]["detail"]["transactionId"]
        list_transactionIds.append(transactionId)
        print(transactionId)
    except Exception as e:
        print(f"Row {i} failed parse: {e}")
        # print(s)  # uncomment to inspect

print("✅", len(list_transactionIds))

for transactionId in list_transactionIds:
    url = f"https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/reports/v2/{transactionId}/835"
    response = requests.request("GET", url, headers = {
    "Authorization": "RYnvhqL.0X6jgBc6ewt5N7v2ILnQtiGy"
    })
    data = json.loads(response.text)

    results = []
    print("🔴starting transactionId:", transactionId)
    for transaction in data["transactions"]:
        for detail in transaction["detailInfo"]:
            for payment in detail["paymentInfo"]:
                results.append({
                    "firstName": payment["patientName"]["firstName"],
                    "lastName": payment["patientName"]["lastName"],
                    "totalClaimChargeAmount": payment["claimPaymentInfo"]["totalClaimChargeAmount"],
                    "claimPaymentAmount": payment["claimPaymentInfo"]["claimPaymentAmount"],
                    "claimStatementPeriodStart": payment["claimStatementPeriodStart"],
                    "claimStatementPeriodEnd": payment["claimStatementPeriodEnd"]
                })

    for result in results:
        print(result)
    print("✅ Finished transactionId:", transactionId, "\n")