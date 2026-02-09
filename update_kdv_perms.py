
from app import get_conn

def update_permissions():
    try:
        # Use the context manager properly for the connection
        # get_conn() returns a context manager that yields the connection
        conn_ctx = get_conn()
        with conn_ctx as conn:
            cur = conn.cursor()
            
            # Reset all to 0 first
            print("Resetting all users to has_kdv_access = 0...")
            cur.execute("UPDATE users SET has_kdv_access = 0")
            
            # Set specific users to 1
            target_users = ('Serhattk0', 'Talhaoner', 'ismetali', 'admin')
            print(f"Granting access to: {target_users}")
            
            # Using tuple for IN clause
            cur.execute("""
                UPDATE users 
                SET has_kdv_access = 1 
                WHERE username IN %s
            """, (target_users,))
            
            conn.commit()
            print("Permissions updated successfully.")

    except Exception as e:
        print(f"Error updating permissions: {e}")

if __name__ == "__main__":
    update_permissions()
