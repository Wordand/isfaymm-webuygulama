from werkzeug.security import check_password_hash, generate_password_hash
from services.db import get_conn
import psycopg2.extras
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

def verify_admin_db_password():
    env_pw = os.getenv("ADMIN_PASSWORD")
    print(f"Password in .env: {env_pw}")
    
    try:
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            c.execute("SELECT password FROM users WHERE username = 'admin'")
            row = c.fetchone()
            if row:
                db_hash = row['password']
                match = check_password_hash(db_hash, env_pw)
                print(f"Does DB hash match .env password? {match}")
                
                # Check if generate_password_hash produces a match
                new_hash = generate_password_hash(env_pw)
                match_new = check_password_hash(new_hash, env_pw)
                print(f"Test new hash match: {match_new}")
            else:
                print("Admin user not found.")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    verify_admin_db_password()
