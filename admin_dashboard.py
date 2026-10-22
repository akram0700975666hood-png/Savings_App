import mysql.connector

def view_admin_dashboard():
    try:
        connection = mysql.connector.connect(host="localhost", user="root", password="", database="sunday_savings_db")
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT SUM(amount) AS grand_total FROM deposits")
        grand_result = cursor.fetchone()
        grand_total = grand_result['grand_total'] if grand_result['grand_total'] else 0
        member_summary_query = """
        SELECT u.user_id, u.full_name, u.username, u.account_status, COALESCE(SUM(d.amount), 0) AS individual_total
        FROM users u LEFT JOIN deposits d ON u.user_id = d.member_id
        WHERE u.role = 'member' GROUP BY u.user_id ORDER BY u.full_name ASC
        """
        cursor.execute(member_summary_query)
        members_list = cursor.fetchall()
        print("\n==================================================")
        print("         👑 ADMINISTRATOR MASTER REPORT            ")
        print("==================================================")
        print(f" 🏦 GRAND TOTAL GROUP CASH LOGGED: {grand_total:,.2f} UGX")
        print("==================================================")
        print("               MEMBER BALANCE OVERVIEW             ")
        print("--------------------------------------------------")
        print(f"{'NAME':<18} | {'USERNAME':<10} | {'STATUS':<8} | {'TOTAL BAL':<12}")
        print("--------------------------------------------------")
        if not members_list:
            print(" No members registered in the system yet.")
        else:
            for member in members_list:
                print(f"{member['full_name']:<18} | {member['username']:<10} | {member['account_status'].upper():<8} | {member['individual_total']:,.0f} UGX")
        print("==================================================\n")
        cursor.close()
        connection.close()
    except mysql.connector.Error as error:
        print(f"Database Error: {error}")

if __name__ == "__main__":
    view_admin_dashboard()
