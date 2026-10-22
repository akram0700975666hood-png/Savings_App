import hashlib
import mysql.connector

# A simple helper function to securely scramble (hash) passwords
def hash_password(password):
    # We turn the text into secure SHA-256 code
    return hashlib.sha256(password.encode()).hexdigest()

try:
    # 1. CONNECT TO THE DATABASE
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="sunday_savings_db"
    )
    cursor = connection.cursor()

    print("Hashing passwords and registering system administrators...")

    # 2. DEFINE THE TWO ADMIN ACCOUNTS
    # You can change 'super_admin_pass' and 'co_admin_pass' to your desired passwords later!
    admin_data = [
        # Full Name, Username, Plain Password, Role, Status
        ("Primary Project Leader", "superadmin", "super_admin_pass", "super_admin", "active"),
        ("Partner Administrator", "coadmin", "co_admin_pass", "admin", "active")
    ]

    # 3. INSERT THEM INTO THE DATABASE ONE BY ONE
    sql_query = """
    INSERT INTO users (full_name, username, password_hash, role, account_status, terms_accepted) 
    VALUES (%s, %s, %s, %s, %s, TRUE)
    """

    for full_name, username, plain_password, role, status in admin_data:
        # We scramble the password before saving it
        secured_password = hash_password(plain_password)
        
        # We execute the command passing the safe data
        cursor.execute(sql_query, (full_name, username, secured_password, role, status))

    # CRITICAL STEP: When inserting or changing data in MySQL, you MUST 'commit'
    # Think of a commit like pressing 'Save' on a document.
    connection.commit()

    print("\n==============================================")
    print(" SUCCESS: Both admin accounts are registered!")
    print("==============================================")

    # Close connections safely
    cursor.close()
    connection.close()

except mysql.connector.Error as error:
    print(f"Database Error: {error}")
