import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

print(f"DASHBOARD_USERNAME: {os.environ.get('DASHBOARD_USERNAME')}")
print(f"DASHBOARD_PASSWORD: {os.environ.get('DASHBOARD_PASSWORD')}")
print(f"ADMIN_PASSWORD: {os.environ.get('ADMIN_PASSWORD')}")
print(f"AEROOPS_PASSWORD: {os.environ.get('AEROOPS_PASSWORD')}")
