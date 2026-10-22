import mysql.connector
import hashlib

# Connect to your Laragon database
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="sunday_savings_db"
)
cursor = conn.cursor()

# 1. Create a clean SHA-256 hash for the password 'member123'
new_password = "member123"
hashed_password = hashlib.sha256(new_password.encode()).hexdigest()

# 2. Update the password_hash column for johndoe
query = "UPDATE users SET password_hash = %s WHERE username = %s"
cursor.execute(query, (hashed_password, "johndoe"))
conn.commit()

print("\n==================================================")
print("            MEMBER PASSWORD RESET                 ")
print("==================================================")
print(f"Successfully updated 'johndoe' password to: {new_password}")
print(f"Hashed Record: {hashed_password}")
print("==================================================\n")

cursor.close()
conn.close()