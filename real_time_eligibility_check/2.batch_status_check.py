import requests

''' this is pulled from MA_medicaid_eligibility_results.csv'''
batchid = "019caf7a-dbe7-7d11-9992-98a4d11d5d84"


url = f"https://manager.us.stedi.com/2024-04-01/eligibility-manager/batch/{batchid}"
response = requests.request("GET", url, headers = {
  "Authorization": "RYnvhqL.0X6jgBc6ewt5N7v2ILnQtiGy"
})
print(response.text)