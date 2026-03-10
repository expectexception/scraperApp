import requests
res = requests.get("https://jobs.elal.com/", timeout=10)
print(res.status_code)
