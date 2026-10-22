import hashlib
import mysql.connector

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def admin_login(username, plain_password):
    try:
        # 1. CONNECT TO DATABASE
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="sunday_savings_db"
        )
        cursor = connection.cursor(dictionary=True)

        # 2. VERIFY CREDENTIALS & ROLE
        secured_password = hash_password(plain_password)
        query = "SELECT * FROM users WHERE username = %s AND password_hash = %s AND role IN ('super_admin', 'admin')"
        cursor.execute(query, (username, secured_password))
        admin = cursor.fetchone()

        if not admin:
            print("\n❌ ACCESS DENIED: Invalid Admin Credentials.")
            return

        # 3. SET THIS ADMIN AS ONLINE IN THE DATABASE
        cursor.execute("UPDATE users SET is_online = TRUE WHERE user_id = %s", (admin['user_id'],))
        connection.commit()
        
        print("\n==================================================")
        print(f"🔒 SECURITY CHECK PASSED: Welcome Admin [{admin['full_name']}]")
        print("==================================================")

        # 4. REAL-TIME NOTIFIER SIMULATION
        # Look up if the OTHER administrator is already active online right now
        cursor.execute("SELECT full_name FROM users WHERE role IN ('super_admin', 'admin') AND is_online = TRUE AND user_id != %s", (admin['user_id'],))
        other_admin = cursor.fetchone()

        if other_admin:
            print(f"🔔 REAL-TIME NOTIFICATION: Co-Admin [{other_admin['full_name']}] is currently LOGGED IN.")
            print("💬 LIVE SYNC ACTIVE: You can now communicate and coordinate entries safely!")
        else:
            print("👤 You are currently the only administrator active online.")
        print("==================================================\n")

        cursor.close()
        connection.close()

    except mysql.connector.Error as error:
        print(f"Database Error: {error}")

# --- SIMULATING THE SCENARIO ---
# Let's pretend your partner logs in first, and then YOU log in right after them.
print("--- SCENARIO: CO-ADMIN LOGS IN FIRST ---")
admin_login("coadmin", "co_admin_pass")

print("--- SCENARIO: YOU LOG IN WHILE THEY ARE ONLINE ---")
admin_login("superadmin", "super_admin_pass")


# --- SIMULATING THE SCENARIO ---
if __name__ == "__main__":
    print("--- SCENARIO: CO-ADMIN LOGS IN FIRST ---")
    admin_login("coadmin", "co_admin_pass")

    print("--- SCENARIO: YOU LOG IN WHILE THEY ARE ONLINE ---")
    admin_login("superadmin", "super_admin_pass")
