import mysql.connector

def submit_member_complaint(member_username, text_message):
    try:
        connection = mysql.connector.connect(host="localhost", user="root", password="", database="sunday_savings_db")
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT user_id FROM users WHERE username = %s AND role = 'member'", (member_username,))
        member = cursor.fetchone()
        if not member:
            return
        insert_query = "INSERT INTO complaints (member_id, message) VALUES (%s, %s)"
        cursor.execute(insert_query, (member['user_id'], text_message))
        connection.commit()
        print(f"✉️ Message sent successfully to Admins from '{member_username}'!")
        cursor.close()
        connection.close()
    except mysql.connector.Error as error:
        print(f"Database Error: {error}")

def view_admin_complaints_panel():
    try:
        connection = mysql.connector.connect(host="localhost", user="root", password="", database="sunday_savings_db")
        cursor = connection.cursor(dictionary=True)
        query = """
        SELECT c.complaint_id, u.full_name, c.message, c.submitted_at 
        FROM complaints c JOIN users u ON c.member_id = u.user_id
        WHERE c.is_resolved = FALSE ORDER BY c.submitted_at ASC
        """
        cursor.execute(query)
        complaints_list = cursor.fetchall()
        print("\n==================================================")
        print("       📩 ADMIN INCOMING COMPLAINTS PANEL         ")
        print("==================================================")
        if not complaints_list:
            print(" No unread or pending complaints from members.")
        else:
            for c in complaints_list:
                print(f" From:    {c['full_name']}")
                print(f" Time:    {c['submitted_at']}")
                print(f" Message: {c['message']}")
                print("--------------------------------------------------")
        print("==================================================\n")
        cursor.close()
        connection.close()
    except mysql.connector.Error as error:
        print(f"Database Error: {error}")

if __name__ == "__main__":
    print("--- MEMBER SIDE ---")
    submit_member_complaint("johndoe", "Hello admins, my deposit for Sunday 18th Oct was 45,000 UGX not 35,000 UGX. Please review.")
    print("\n--- ADMIN SIDE ---")
    view_admin_complaints_panel()
