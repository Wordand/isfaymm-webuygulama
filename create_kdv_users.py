import os
import sys
from werkzeug.security import generate_password_hash

# Uygulama bağlamını yüklemek için ana dizine ekleyelim
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services.db import get_conn
import psycopg2.extras

# Kullanıcı listesini burada ayarlayabilirsiniz.
# role: 'uzman' veya 'yonetici' gibi belirleyebilirsiniz.
USERS_TO_CREATE = [
    {
        "username": "ismetali",
        "password": "ismet34",
        "role": "yonetici",
        "kdv_pin": "1234"
    },
    {
        "username": "talhaoner",
        "password": "11.talha",
        "role": "yonetici",
        "kdv_pin": "1234"
    },
    {
        "username": "serhat",
        "password": "Sifre.9",
        "role": "uzman",
        "kdv_pin": "1234"
    },
    {
        "username": "osman",
        "password": "Sifre.1",
        "role": "uzman",
        "kdv_pin": "1234"
    }
]

def add_users():
    with get_conn() as conn:
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        for user_data in USERS_TO_CREATE:
            username = user_data["username"]
            password = user_data["password"]
            role = user_data["role"]
            pin = user_data["kdv_pin"]
            
            hashed_pw = generate_password_hash(password)

            # Kullanıcı daha önce eklenmiş mi kontrol et
            c.execute("SELECT id FROM users WHERE username = %s", (username,))
            existing_user = c.fetchone()

            if existing_user:
                # Kullanıcı varsa, yetkilerini ve şifresini güncelle
                user_id = existing_user["id"]
                c.execute("""
                    UPDATE users 
                    SET password = %s, is_approved = 1, role = %s, has_kdv_access = 1, kdv_pin = %s
                    WHERE id = %s
                """, (hashed_pw, role, pin, user_id))
                print(f"[GÜNCELLENDİ] {username} kullanıcısı güncellendi ve KDV yetkisi verildi.")
            else:
                # Kullanıcı yoksa yeni ekle
                c.execute("""
                    INSERT INTO users (username, password, is_approved, role, has_kdv_access, kdv_pin)
                    VALUES (%s, %s, 1, %s, 1, %s)
                """, (username, hashed_pw, role, pin))
                print(f"[EKLENDİ] {username} kullanıcısı KDV yetkisiyle eklendi.")

        conn.commit()
    print("\nTüm işlemler tamamlandı.")

if __name__ == "__main__":
    add_users()
