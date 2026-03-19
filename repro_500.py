import requests

BASE_URL = "http://localhost:8008/api/scrapers"
USERNAME = "admin"
PASSWORD = "aeroops2024"

def test_active_500():
    # Login first
    login_url = f"{BASE_URL}/auth/login/"
    response = requests.post(login_url, json={"username": USERNAME, "password": PASSWORD})
    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        return
    
    token = response.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try GET /active/
    print("Testing GET /active/...")
    response = requests.get(f"{BASE_URL}/active/", headers=headers)
    print(f"GET /active/ status: {response.status_code}")
    if response.status_code != 200:
        print(response.text[:500])

    # Try POST /active/ (as seen in logs)
    print("Testing POST /active/...")
    response = requests.post(f"{BASE_URL}/active/", headers=headers)
    print(f"POST /active/ status: {response.status_code}")
    if response.status_code != 200:
        print(response.text[:500])

if __name__ == "__main__":
    test_active_500()
