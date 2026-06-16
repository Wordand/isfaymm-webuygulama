import os
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv

load_dotenv(override=True)
db_url = os.getenv("DATABASE_URL")

print(f"Connecting to: {db_url}")
try:
    conn = psycopg2.connect(db_url, sslmode="require", connect_timeout=5)
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = cur.fetchall()
    print("\n=== Remote PostgreSQL Database Tables ===")
    for t in tables:
        t_name = t['table_name']
        try:
            cur.execute(f'SELECT COUNT(*) FROM "{t_name}"')
            count = cur.fetchone()['count']
            print(f"Table: {t_name:<30} Row count: {count}")
        except Exception as e:
            print(f"Table: {t_name:<30} Error: {e}")
            conn.rollback()
    conn.close()
except Exception as e:
    print(f"Failed to connect to Postgres: {e}")
