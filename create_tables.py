import mysql.connector

try:
    # 1. CONNECT TO LARAGON
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="sunday_savings_db"
    )
    
    # A cursor is like a digital hand that passes our SQL commands to MySQL
    cursor = connection.cursor()

    print("Creating your remaining system tables...")

    # 2. CREATE THE DEPOSITS TABLE
    # This keeps track of Sunday savings, the amount, and which admin entered it.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deposits (
        deposit_id INT AUTO_INCREMENT PRIMARY KEY,
        member_id INT,
        amount DECIMAL(10, 2) NOT NULL,
        deposit_date DATE NOT NULL,
        recorded_by INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (member_id) REFERENCES users(user_id),
        FOREIGN KEY (recorded_by) REFERENCES users(user_id)
    );
    """)
    print(" -> Deposits table created successfully!")

    # 3. CREATE THE COMPLAINTS TABLE
    # This holds the private, one-way messages from members to admins.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        complaint_id INT AUTO_INCREMENT PRIMARY KEY,
        member_id INT,
        message TEXT NOT NULL,
        is_resolved BOOLEAN DEFAULT FALSE,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (member_id) REFERENCES users(user_id)
    );
    """)
    print(" -> Complaints table created successfully!")

    # 4. CREATE THE YEAR END ARCHIVE TABLE
    # This stores old records safely before active balances reset to zero.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS year_end_archive (
        archive_id INT AUTO_INCREMENT PRIMARY KEY,
        archive_year INT NOT NULL,
        member_name VARCHAR(100) NOT NULL,
        total_amount_saved DECIMAL(10, 2) NOT NULL,
        archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    print(" -> Year-End Archive table created successfully!")

    # Clean up and close everything safely
    cursor.close()
    connection.close()
    print("\n==============================================")
    print(" SUCCESS: All remaining tables are ready!")
    print("==============================================")

except mysql.connector.Error as error:
    print(f"Something went wrong: {error}")
