import mysql.connector

def run_year_end_reset(admin_user_id, current_year_to_archive):
    try:
        connection = mysql.connector.connect(host="localhost", user="root", password="", database="sunday_savings_db")
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT role FROM users WHERE user_id = %s", (admin_user_id,))
        admin = cursor.fetchone()
        if not admin or admin['role'] != 'super_admin':
            print("\n❌ ACCESS DENIED: Only the Primary Project Leader can reset the year.")
            return
        print(f"\n⚠️ Starting Year-End Process for {current_year_to_archive}...")
        summary_query = """
        SELECT u.full_name, COALESCE(SUM(d.amount), 0) AS final_total
        FROM users u LEFT JOIN deposits d ON u.user_id = d.member_id
        WHERE u.role = 'member' GROUP BY u.user_id
        """
        cursor.execute(summary_query)
        year_totals = cursor.fetchall()
        archive_query = "INSERT INTO year_end_archive (archive_year, member_name, total_amount_saved) VALUES (%s, %s, %s)"
        for row in year_totals:
            if row['final_total'] > 0:
                cursor.execute(archive_query, (current_year_to_archive, row['full_name'], row['final_total']))
        cursor.execute("DELETE FROM deposits")
        connection.commit()
        print("==============================================")
        print(f" 🎉 SUCCESS: Year {current_year_to_archive} is fully archived!")
        print(" -> All active balances have been wiped to 0.00 UGX.")
        print(" -> Historical summaries saved securely for Admin review.")
        print("==============================================")
        cursor.close()
        connection.close()
    except mysql.connector.Error as error:
        print(f"Database Error: {error}")

def view_archived_history():
    try:
        connection = mysql.connector.connect(host="localhost", user="root", password="", database="sunday_savings_db")
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM year_end_archive ORDER BY archive_year DESC, member_name ASC")
        records = cursor.fetchall()
        print("\n==============================================")
        print("       📁 ADMIN HISTORICAL ARCHIVE LOOK-BACK   ")
        print("==============================================")
        if not records:
            print(" No past archived years found.")
        else:
            for r in records:
                print(f" [Year: {r['archive_year']}] | Member: {r['member_name']:<15} | Returned Payout: {r['total_amount_saved']:,.0f} UGX")
        print("==============================================\n")
        cursor.close()
        connection.close()
    except mysql.connector.Error as error:
        print(f"Database Error: {error}")

if __name__ == "__main__":
    run_year_end_reset(admin_user_id=1, current_year_to_archive=2026)
    view_archived_history()
