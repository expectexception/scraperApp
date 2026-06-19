import requests

url = "https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions?cid=06351502-0666-4c6f-9a0b-165c5faeab35&ccId=9200784035909_2&lang=en_CA"
response = requests.get(url)
data = response.json()
print("Total jobs:", len(data.get("jobRequisitions", [])))
if data.get("jobRequisitions"):
    print("Sample job:", data["jobRequisitions"][0].get("requisitionTitle"))
    print("Locations:", data["jobRequisitions"][0].get("requisitionLocations"))
    print("Client info:", data.get("clientName", "Not found"))
