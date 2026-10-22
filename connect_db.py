import mysql.connector

# 1. SETTING UP THE CONNECTION DETAILS
# We tell Python where our Laragon database is located and how to log into it.
try:
    db_connection = mysql.connector.connect(
        host="localhost",        # Laragon runs locally on your PC
        user="root",             # Laragon's default username
        password="",             # Laragon's default password is blank (empty quotes)
        database="sunday_savings_db" # The database we just created together
    )

    # 2. TESTING THE CONNECTION
    # If the login details match, this code runs and tells us it worked.
    if db_connection.is_connected():
        print("==============================================")
        # We print a simple human-level success message
        print(" SUCCESS: Python connected to sunday_savings_db!")
        print("==============================================")
        
        # We close the connection safely when done testing
        db_connection.close()

# 3. CATCHING AN ERROR
# If something goes wrong (like a typo in the database name), Python will catch it here.
except mysql.connector.Error as error:
    print("==============================================")
    print(" ERROR: Could not connect to the database.")
    print(f" Reason: {error}")
    print("==============================================")
