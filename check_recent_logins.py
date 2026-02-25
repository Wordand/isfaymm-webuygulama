from services.db import get_conn
import psycopg2.extras
from datetime import datetime

def check_recent_logins():
    try:
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            # Check for logins today
            c.execute("SELECT * FROM login_logs WHERE login_time >= CURRENT_DATE ORDER BY id DESC")
            rows = c.fetchall()
            if not rows:
                print("No login attempts today.")
            for row in rows:
                print(f"ID: {row['id']}, User: {row['username']}, Success: {row['success']}, Time: {row['login_time']}")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    check_recent_logins()
