import hashlib
import mysql.connector

# Our standard password security function
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_new_user(full_name, username, plain_password, is_self_registered=False):
    try:
        # 1. CONNECT TO DATABASE
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="sunday_savings_db"
        )
        cursor = connection.cursor()

        # 2. DETERMINE STATUS AND AGREEMENT RULES
        # If they sign up themselves: status is pending, terms are not accepted (False)
        # If admin creates it: status is active, but they still must sign terms on first login (False)
        if is_self_registered:
            status = "pending"
        else:
            status = "active"

        secured_password = hash_password(plain_password)

        # 3. INSERT COMMAND
        sql_query = """
        INSERT INTO users (full_name, username, password_hash, role, account_status, terms_accepted) 
        VALUES (%s, %s, %s, 'member', %s, FALSE)
        """
        
        cursor.execute(sql_query, (full_name, username, secured_password, status))
        connection.commit()

        print("==============================================")
        print(f" SUCCESS: Account created for {full_name}!")
        print(f" Username: {username}")
        print(f" Account Status: {status.upper()}")
        print("==============================================")

        cursor.close()
        connection.close()

    except mysql.connector.Error as error:
        print(f"Error: Could not register user. {error}")

# --- TESTING AREA ---
# Let's test by manually adding our very first group member!
# Arguments: Full Name, Username, Temporary Password, IsSelfRegistered (False means Admin created)
register_new_user("John Doe", "johndoe", "welcome123", is_self_registered=False)


# --- TESTING AREA ---
if __name__ == "__main__":
    # Arguments: Full Name, Username, Temporary Password, IsSelfRegistered (False means Admin created)
    register_new_user("John Doe", "johndoe", "welcome123", is_self_registered=False)
