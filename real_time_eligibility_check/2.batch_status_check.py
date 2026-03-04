import requests

''' this is pulled from MA_medicaid_eligibility_results.csv'''
batchid = "019cb3fe-d505-7a22-a73b-6e791940c03c"


url = f"https://manager.us.stedi.com/2024-04-01/eligibility-manager/batch/{batchid}"
response = requests.request("GET", url, headers = {
  "Authorization": "RYnvhqL.0X6jgBc6ewt5N7v2ILnQtiGy"
})
print(response.text)