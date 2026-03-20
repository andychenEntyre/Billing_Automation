import requests
import csv

# # Path to the CSV file
# csv_path = "/Users/Andy.Chen/Billing_Automation/9mar26_missing_feb_eligibility_check/Feb_eligibility_batch_log.csv"

# ''' Read the last row's first column from csv_path '''
batchid = '019cd8e9-a45a-7140-9555-7523246ed592'
# with open(csv_path, newline='') as csvfile:
#     reader = csv.reader(csvfile)
#     rows = list(reader)
#     batchid = rows[-1][0]  # last row, first column

print(batchid)

url = f"https://manager.us.stedi.com/2024-04-01/eligibility-manager/batch/{batchid}"
response = requests.request("GET", url, headers = {
  "Authorization": "RYnvhqL.0X6jgBc6ewt5N7v2ILnQtiGy"
})
print(response.text)