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

# Search criteria
target_first_name = "MARC"
target_last_name = "BURKE"
target_member_id = "100012856553"

# Search for items where subscriber.firstName == "MARC"
matches = [
    item for item in all_items
    if item.get("subscriber", {}).get("firstName") == target_first_name 
    and item.get("subscriber", {}).get("lastName") == target_last_name 
    and item.get("subscriber", {}).get("memberId") == target_member_id
]

print(f"\n🔎 Found {len(matches)} items")

if matches:
    print(json.dumps(matches[0], indent=2))