import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
print(f"Connecting to: {url[:20]}...")

try:
    conn = psycopg2.connect(url, sslmode="require", connect_timeout=5)
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
