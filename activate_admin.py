import mysql.connector
import hashlib

# Connect to Laragon MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="sunday_savings_db"
)
cursor = conn.cursor(dictionary=True)

# 1. Force the status update again to be absolutely sure
cursor.execute("UPDATE users SET account_status = 'Active' WHERE username = 'superadmin'")
conn.commit()

# 2. Pull the actual database record for superadmin to see what is inside
cursor.execute("SELECT user_id, username, role, account_status, password_hash FROM users WHERE username = 'superadmin'")
user_record = cursor.fetchone()

print("==================================================")
print("          DATABASE DIAGNOSTIC REPORT              ")
print("==================================================")

if user_record:
    print(f"User Found: {user_record['username']}")
    print(f"Database Role: '{user_record['role']}'")
    print(f"Database Status: '{user_record['account_status']}'")
    print(f"Database Hash: {user_record['password_hash']}")
    
    # 3. Calculate what 'super_admin_pass' should look like when hashed
    expected_hash = hashlib.sha256("super_admin_pass".encode()).hexdigest()
    print(f"Expected Hash: {expected_hash}")
    
    if user_record['password_hash'] == expected_hash:
        print(">>> MATCH CHECK: Password hash matches perfectly!")
    else:
        print(">>> MATCH CHECK: ERROR! The password in your database does not match 'super_admin_pass'.")
else:
    print("ERROR: No user with the username 'superadmin' exists in your database table!")

print("==================================================")

cursor.close()
conn.close()
