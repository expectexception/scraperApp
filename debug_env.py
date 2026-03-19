import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

print(f"DEBUG: {os.environ.get('DEBUG')}")
print(f"MONGODB_URI: {os.environ.get('MONGODB_URI')}")
print(f"MONGO_URI: {os.environ.get('MONGO_URI')}")
print(f"DB_HOST: {os.environ.get('DB_HOST')}")
print(f"MONGODB_NAME: {os.environ.get('MONGODB_NAME')}")
print(f"DB_NAME: {os.environ.get('DB_NAME')}")
