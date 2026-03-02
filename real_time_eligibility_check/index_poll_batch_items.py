import requests
import json

''' this is pulled from MA_medicaid_eligibility_results.csv'''
batchid = "019caf7a-dbe7-7d11-9992-98a4d11d5d84"
url = f"https://manager.us.stedi.com/2024-04-01/eligibility-manager/polling/batch-eligibility?batchId={batchid}"

response = requests.request("GET", url, headers = {
  "Authorization": "RYnvhqL.0X6jgBc6ewt5N7v2ILnQtiGy"
})

# Convert response to dictionary
response_data = response.json()

items = response_data.get("items", [])

if items:
    first_item = items[9]
    print("✅", len(items), "items returned.")
    print(json.dumps(first_item, indent=2))
else:
    print("No items returned.")