from services.db import get_conn
import psycopg2.extras

def check_logins():
    try:
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            c.execute("SELECT * FROM login_logs ORDER BY id DESC LIMIT 20")
            rows = c.fetchall()
            if rows:
                print("Columns:", rows[0].keys())
            for row in rows:
                print(row)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    check_logins()
