import pandas as pd
import json
import requests
from datetime import datetime

'''this file comes from Databricks MA client pull'''

file_path = "real_time_eligibility_check/02March26_MA_clients.csv"
df = pd.read_csv(file_path)

items = []

for _, row in df.iterrows():
    item = {
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
    }
    items.append(item)

'''timestamp creates a unique name for each batch eligibility check'''
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

body = {
    "items": items,
    "name": f"eligibility-batch-{timestamp}"
}

url = "https://manager.us.stedi.com/2024-04-01/eligibility-manager/batch-eligibility"

response = requests.request("POST", url, json = body, headers = {
  "Authorization": "RYnvhqL.0X6jgBc6ewt5N7v2ILnQtiGy",
  "Content-Type": "application/json"
})

print(response.text)

log_df = pd.DataFrame([{
    "batch_id": response.json().get("batchId"),
    "submitted_at": response.json().get("submittedAt")
}])

log_df.to_csv("eligibility_batch_log.csv", mode="a", header=False, index=False)