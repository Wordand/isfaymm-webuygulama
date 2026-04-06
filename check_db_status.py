from services.db import get_conn
import json

def check_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check users
            cur.execute("SELECT id, username, role, has_kdv_access FROM users")
            users = cur.fetchall()
            print("Users:")
            for u in users:
                print(u)
            
            # Check if kdv_system_logs exists
            try:
                cur.execute("SELECT COUNT(*) FROM kdv_system_logs")
                count = cur.fetchone()
                print(f"kdv_system_logs count: {count}")
                
                cur.execute("SELECT * FROM kdv_system_logs ORDER BY id DESC LIMIT 5")
                logs = cur.fetchall()
                print("Last 5 Logs:")
                for l in logs:
                    print(l)
            except Exception as e:
                print(f"kdv_system_logs error: {e}")

if __name__ == "__main__":
    check_db()
