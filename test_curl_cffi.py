from curl_cffi import requests

url = "https://hub-vistaglobal.icims.com/jobs/search?ss=1&searchCategory=109470&searchCategory=17882&searchCategory=17912&searchCategory=17886&searchCategory=8748&searchCategory=17898&searchCategory=54473&searchCategory=57874&mobile=false&width=1296&height=500&bga=true&needsRedirect=false&jan1offset=330&jun1offset=330"

print("Fetching with curl_cffi...")
try:
    resp = requests.get(url, impersonate="chrome110", timeout=20)
    print("Status:", resp.status_code)
    print("Body length:", len(resp.text))
    print("Snippet:")
    print(resp.text[:1000])
except Exception as e:
    print("Error:", e)
