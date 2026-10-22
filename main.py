import sys
import mysql.connector
from login_system import login_user, hash_password
from add_deposit import add_sunday_savings
from member_dashboard import view_member_dashboard
from admin_dashboard import view_admin_dashboard
from complaints_system import submit_member_complaint, view_admin_complaints_panel
from year_end_reset import run_year_end_reset, view_archived_history

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="sunday_savings_db"
    )

def authenticate_session():
    print("\n==============================================")
    print("   ☀️ SUNDAY SAVINGS TRACKING SYSTEM LOGIN   ")
    print("==============================================")
    username = input("Enter Username: ").strip()
    password = input("Enter Password: ").strip()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        secured_pass = hash_password(password)
        query = "SELECT * FROM users WHERE username = %s AND password_hash = %s"
        cursor.execute(query, (username, secured_pass))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        return user
    except mysql.connector.Error as err:
        print(f"Connection Error: {err}")
        return None

def run_member_menu(user):
    while True:
        print(f"\n--- MEMBER MENU (Logged in: {user['full_name']}) ---")
        print("1. View My Savings Dashboard & Deposit History")
        print("2. Submit a Private Complaint/Message to Admins")
        print("3. Log Out")
        print("---------------------------------------------")
        choice = input("Select an option (1-3): ").strip()
        
        if choice == '1':
            view_member_dashboard(user['username'])
        elif choice == '2':
            msg = input("\nEnter your complaint or question: ")
            submit_member_complaint(user['username'], msg)
        elif choice == '3':
            print("Logging out safely...")
            break
        else:
            print("❌ Invalid selection. Please enter 1, 2, or 3.")

def run_admin_menu(user):
    while True:
        print(f"\n--- ADMIN DASHBOARD CONTROL (Logged in: {user['full_name']}) ---")
        print("1. Record a New Sunday Deposit")
        print("2. View Group Cash Grand Total & Member Balances")
        print("3. View Incoming Member Complaints Panel")
        
        if user['role'] == 'super_admin':
            print("4. [SUPER ADMIN ONLY] Run Year-End Archive & Payout Reset")
            print("5. [SUPER ADMIN ONLY] View Historical Archive Look-Back")
            print("6. Log Out")
        else:
            print("4. Log Out")
            
        print("---------------------------------------------")
        choice = input("Select an option: ").strip()
        
        if choice == '1':
            m_user = input("Enter member username: ").strip()
            amt = float(input("Enter deposit amount (UGX): "))
            dep_date = input("Enter Sunday date (YYYY-MM-DD): ").strip()
            add_sunday_savings(m_user, amt, dep_date, user['user_id'])
        elif choice == '2':
            view_admin_dashboard()
        elif choice == '3':
            view_admin_complaints_panel()
        elif choice == '4' and user['role'] == 'super_admin':
            year = int(input("Enter the year to archive (e.g. 2026): "))
            run_year_end_reset(user['user_id'], year)
        elif choice == '5' and user['role'] == 'super_admin':
            view_archived_history()
        elif (choice == '6' and user['role'] == 'super_admin') or (choice == '4' and user['role'] == 'admin'):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_online = FALSE WHERE user_id = %s", (user['user_id'],))
            conn.commit()
            cursor.close()
            conn.close()
            print("Administrative session closed safely. Logging out...")
            break
        else:
            print("❌ Invalid selection. Please try again.")

def main():
    while True:
        user = authenticate_session()
        
        if not user:
            print("❌ Login failed. Incorrect username or password.")
            continue
            
        if user['account_status'] == 'pending':
            print("\n🔒 ACCESS DENIED: Your account is pending admin approval.")
            continue
        elif user['account_status'] == 'suspended':
            print("\n❌ ACCESS DENIED: Account suspended.")
            continue
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_online = TRUE WHERE user_id = %s", (user['user_id'],))
        conn.commit()
        
        if user['role'] in ('super_admin', 'admin'):
            cursor.execute("SELECT full_name FROM users WHERE role IN ('super_admin', 'admin') AND is_online = TRUE AND user_id != %s", (user['user_id'],))
            other = cursor.fetchone()
            if other:
                print(f"\n🔔 NOTIFICATION: Co-Admin [{other[0]}] is currently working online inside this session!")
                
        cursor.close()
        conn.close()

        if user['role'] in ('super_admin', 'admin'):
            run_admin_menu(user)
        elif user['role'] == 'member':
            run_member_menu(user)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSystem shut down manually via terminal command. Goodbye!")
        sys.exit(0)
