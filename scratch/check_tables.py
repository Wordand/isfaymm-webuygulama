import sqlite3
import os

dbs = ['instance/local_fast.db', 'instance/database.db']
for db in dbs:
    if os.path.exists(db):
        print(f"\n=== Database: {db} ===")
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cur.fetchall()
        for t in tables:
            t_name = t[0]
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t_name}")
                count = cur.fetchone()[0]
                print(f"Table: {t_name:<30} Row count: {count}")
            except Exception as e:
                print(f"Table: {t_name:<30} Error: {e}")
        conn.close()
    else:
        print(f"\n=== Database {db} NOT found ===")
