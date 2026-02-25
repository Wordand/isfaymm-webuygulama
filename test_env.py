import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

print("ADMIN_USERNAME:", os.getenv("ADMIN_USERNAME"))
print("ADMIN_PASSWORD:", os.getenv("ADMIN_PASSWORD"))
