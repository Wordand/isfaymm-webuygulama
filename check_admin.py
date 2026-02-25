from services.db import get_conn
import psycopg2.extras

def check_admin_user():
    try:
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            c.execute("SELECT * FROM users WHERE username = 'admin'")
            row = c.fetchone()
            if row:
                print(row)
            else:
                print("Admin user not found.")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    check_admin_user()
