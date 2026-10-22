import mysql.connector

def view_member_dashboard(member_username):
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="sunday_savings_db"
        )
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT user_id, full_name FROM users WHERE username = %s AND role = 'member'", (member_username,))
        member = cursor.fetchone()
        if not member:
            print(f"❌ Error: Username '{member_username}' not found.")
            return
        balance_query = "SELECT SUM(amount) AS total_balance FROM deposits WHERE member_id = %s"
        cursor.execute(balance_query, (member['user_id'],))
        balance_result = cursor.fetchone()
        current_balance = balance_result['total_balance'] if balance_result['total_balance'] else 0
        history_query = "SELECT deposit_date, amount FROM deposits WHERE member_id = %s ORDER BY deposit_date ASC"
        cursor.execute(history_query, (member['user_id'],))
        deposit_history = cursor.fetchall()
        print("\n==================================================")
        print("       👤 MEMBER SAVINGS PROGRESS DASHBOARD       ")
        print("==================================================")
        print(f" Member Name:    {member['full_name']}")
        print(f" Account Status: ACTIVE")
        print(f"--------------------------------------------------")
        print(f" 💰 TOTAL RUNNING BALANCE: {current_balance:,.2f} UGX")
        print("==================================================")
        print("       📅 CHRONOLOGICAL DEPOSIT HISTORY LIST       ")
        print("--------------------------------------------------")
        if not deposit_history:
            print(" No deposits recorded yet.")
        else:
            for count, row in enumerate(deposit_history, 1):
                print(f"  {count}. Sunday [{row['deposit_date']}] -> Saved: {row['amount']:,} UGX")
        print("==================================================\n")
        cursor.close()
        connection.close()
    except mysql.connector.Error as error:
        print(f"Database Error: {error}")

if __name__ == "__main__":
    view_member_dashboard("johndoe")
