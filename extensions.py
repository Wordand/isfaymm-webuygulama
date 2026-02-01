from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from cryptography.fernet import Fernet
import config
import os

# Limiter'ı app context'ten bağımsız başlat
limiter = Limiter(key_func=get_remote_address)

# Fernet key setup
fernet = None
try:
    key = config.FERNET_KEY
    if not key:
        key = os.getenv("FERNET_KEY")
    
    if key:
        fernet = Fernet(key.encode())
    else:
        print("Warning: FERNET_KEY not found in config or env.")
except Exception as e:
    print(f"Error initializing Fernet: {e}")
