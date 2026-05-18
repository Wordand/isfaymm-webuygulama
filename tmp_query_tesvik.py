import sqlite3

con = sqlite3.connect("instance/database.db")
con.row_factory = sqlite3.Row
cur = con.cursor()

cur.execute("select name from sqlite_master where type='table' and name like 'tesvik%'")
print("tables", [r["name"] for r in cur.fetchall()])

cur.execute("PRAGMA table_info(tesvik_kullanim)")
print("tesvik_kullanim cols", [r[1] for r in cur.fetchall()])

cur.execute("select * from tesvik_kullanim where belge_no=? order by hesap_donemi, donem_turu", ("test-3305",))
rows = cur.fetchall()
print("kullanim count", len(rows))
for r in rows:
    print(dict(r))

