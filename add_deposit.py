import mysql.connector

def add_sunday_savings(member_username, amount, deposit_date_string, admin_user_id):
    try:
        connection = mysql.connector.connect(host="localhost", user="root", password="", database="sunday_savings_db")
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT user_id, full_name FROM users WHERE username = %s AND role = 'member'", (member_username,))
        member = cursor.fetchone()
        if not member:
            print(f"\n❌ ERROR: Member username '{member_username}' not found.")
            return
        insert_query = "INSERT INTO deposits (member_id, amount, deposit_date, recorded_by) VALUES (%s, %s, %s, %s)"
        cursor.execute(insert_query, (member['user_id'], amount, deposit_date_string, admin_user_id))
        connection.commit()
        print("==============================================")
        print(" SUCCESS: Deposit recorded automatically!")
        print(f" Member: {member['full_name']}")
        print(f" Amount: {amount:,} UGX")
        print(f" Sunday Date: {deposit_date_string}")
        print("==============================================")
        cursor.close()
        connection.close()
    except mysql.connector.Error as error:
        print(f"Database Error: {error}")

if __name__ == "__main__":
    print("--- RUNNING ADMIN DEPOSIT ENTRIES ---")
    add_sunday_savings("johndoe", 50000, "2026-10-11", 1)
    add_sunday_savings("johndoe", 35000, "2026-10-18", 1)
