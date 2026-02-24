from services.db import get_conn
import psycopg2.extras

def test():
    try:
        with get_conn() as conn:
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            c.execute("SELECT * FROM mukellef LIMIT 1")
            row = c.fetchone()
            if row:
                print("Mukellef Columns found:", row.keys())
            else:
                print("Table 'mukellef' is empty.")
    except Exception as e:
        print("Error checking 'mukellef' table:", e)

if __name__ == "__main__":
    test()
