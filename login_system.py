import datetime
import hashlib
import mysql.connector

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_user(username, plain_password):
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="sunday_savings_db"
        )
        cursor = connection.cursor(dictionary=True)

        secured_password = hash_password(plain_password)
        query = "SELECT * FROM users WHERE username = %s AND password_hash = %s"
        cursor.execute(query, (username, secured_password))
        user = cursor.fetchone()

        if not user:
            print("\n❌ ERROR: Invalid username or password.")
            return None

        if user['account_status'] == 'pending':
            print("\n🔒 ACCESS DENIED: Your account is pending admin approval.")
            return None
        elif user['account_status'] == 'suspended':
            print("\n❌ ACCESS DENIED: This account has been suspended.")
            return None

        print(f"\n✅ Welcome back, {user['full_name']}! (Role: {user['role'].upper()})")

        if user['role'] == 'member':
            if not user['terms_accepted']:
                print("\n==================================================")
                print("🚨 FIRST TIME LOGIN: MANDATORY SAVINGS AGREEMENT 🚨")
                print("==================================================")
                print(" 1. NO LOANS: We do not give out loans or credit.")
                print(" 2. NO EARLY WITHDRAWALS: Money is strictly locked.")
                print(" 3. DECEMBER PAYOUT: Funds are paid out only in December.")
                print("==================================================")
                
                choice = input("Do you agree to these terms? (Type 'YES' to sign off): ")
                
                if choice.strip().upper() == "YES":
                    right_now = datetime.datetime.now()
                    simulated_ip = "192.168.100.45" 
                    
                    update_query = """
                    UPDATE users 
                    SET terms_accepted = TRUE, terms_accepted_at = %s, ip_address_at_signoff = %s 
                    WHERE user_id = %s
                    """
                    cursor.execute(update_query, (right_now, simulated_ip, user['user_id']))
                    connection.commit()
                    
                    print("\n✍️ Digital signature captured successfully!")
                    print(f"Timestamped on: {right_now}")
                    print("🎉 Dashboard unlocked! You can now view your balances.")
                else:
                    print("\n❌ You must agree to the terms to access your account. Logging out.")
                    return None
            else:
                print("📊 Loading your Sunday Savings Dashboard... Everything is ready!")

        cursor.close()
        connection.close()
        return user

    except mysql.connector.Error as error:
        print(f"Database Error: {error}")
        return None

# --- TESTING RUNS ---
# This guard ensures this block ONLY runs if you right-click and run login_system.py directly.
# When imported into main.py, it remains completely silent!
if __name__ == "__main__":
    print("--- RUNNING SIMULATED LOGIN FOR JOHN DOE ---")
    login_user("johndoe", "welcome123")
