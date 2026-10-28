from flask import Flask, render_template, request, redirect, url_for, session, flash
import hashlib
import mysql.connector
import calendar
import os
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

# CLEANED DATETIME IMPORTS: This version allows you to use datetime.now() everywhere safely
from datetime import datetime, date, timedelta


# ==========================================
# 1. LOAD CONFIGURATION AND SECRET KEYS
# ==========================================
load_dotenv()
GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')

# Live Gmail Server Settings
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # Secure SSL port

app = Flask(__name__)
app.secret_key = 'replace_this_with_a_secure_random_key_later'

# ==========================================
# 2. SYSTEM UTILITY & CONNECTIONS SECTION
# ==========================================

def get_db_connection():
    """Establishes a clean bridge to your existing Laragon database."""
    return mysql.connector.connect(
        host="localhost",
        user="root",        # Your Laragon default user
        password="",        # Your Laragon default password (usually empty)
        database="sunday_savings_db"
    )

def send_system_email(recipient_email, subject, body_content):
    """Utility function to pull contact details and route automated system emails safely."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print(">>> ERROR: Email configuration credentials missing from environment setup.")
        return False

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = GMAIL_USER
    msg['To'] = recipient_email
    msg.set_content(body_content)

    try:
        # Open secure tunnel directly to Gmail
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f">>> SUCCESS: System email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f">>> ERROR: Transmission failure to {recipient_email}. Details: {e}")
        return False

# ==========================================
# 3. APPLICATION ROUTES & LOGIC
# ==========================================

@app.route('/')
def home():
    """Redirects base traffic directly to the login interface."""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles visual authentication and branches users by role and policy completion state."""
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        # Hash the incoming password to match your verified SHA-256 database records
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True) # Returns rows as readable dictionaries
        
        query = "SELECT * FROM users WHERE username = %s AND password_hash = %s"
        cursor.execute(query, (username, hashed_password))
        user = cursor.fetchone()

        if user:
            # Force the status to lowercase to match 'active' safely
            current_status = str(user['account_status']).strip().lower()
            
            # Check gates for status flags
            if current_status in ['pending', 'suspended']:
                flash("Your account access is currently locked or pending approval.", "danger")
                cursor.close()  
                conn.close()    
                return redirect(url_for('login'))
        
            # Log the session data using the exact 'user_id' column key
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            # Update dynamic state flag to online using 'user_id'
            update_status = "UPDATE users SET is_online = 1 WHERE user_id = %s"
            cursor.execute(update_status, (user['user_id'],))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            # Clean the role text from the database before checking it to prevent loops
            clean_role = str(user['role']).strip().lower()
            
            # Route smoothly based on role evaluation (Allows both 'admin' and 'super_admin')
            if clean_role in ['admin', 'super_admin']:
                return redirect(url_for('admin_dashboard'))
            else:
                # Intercept standard member to check if they have accepted the terms yet
                if not user.get('terms_accepted'):
                    return redirect(url_for('member_sign_policy'))
                return redirect(url_for('member_dashboard'))
        else:
            flash("Invalid username or password credentials.", "danger")
            cursor.close()
            conn.close()
            
    return render_template('login.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    """Guarded portal route exclusively for administrative accounts."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Clean the role text by removing hidden spaces and forcing lowercase
    user_role = str(session.get('role', '')).strip().lower()
    
    # Secure gate allows both admin roles to view the template layout
    if user_role not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    # Open connection to pull active database metrics
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Fetch total registered system users
    cursor.execute("SELECT COUNT(user_id) AS total_users FROM users")
    users_result = cursor.fetchone()
    total_users = users_result['total_users'] if users_result else 0
    
    # 2. Fetch total accumulated savings group pool (UGX)
    cursor.execute("SELECT SUM(amount) AS total_savings FROM deposits")
    savings_result = cursor.fetchone()
    total_savings = savings_result['total_savings'] if savings_result and savings_result['total_savings'] is not None else 0
    
    # 3. Fetch total pending admin alerts from complaints pipeline
    cursor.execute("SELECT COUNT(*) AS total_complaints FROM complaints")
    complaints_result = cursor.fetchone()
    total_complaints = complaints_result['total_complaints'] if complaints_result else 0
    
    # 4. Fetch active member list for the Direct Notifications drop-down selector form
    cursor.execute("SELECT user_id, username, full_name FROM users WHERE LOWER(role) = 'member' ORDER BY username ASC")
    members_list = cursor.fetchall()

    # Securely close connections after retrieving metric results
    cursor.close()
    conn.close()
        
    # Renders the admin visual panel template, passing the login user session data, metrics, and member rows
    return render_template(
        'admin_dashboard.html', 
        username=session['username'],
        total_users=total_users,
        total_savings=total_savings,
        total_complaints=total_complaints,
        members=members_list
    )


@app.route('/admin/deposit', methods=['GET', 'POST'])
def record_deposit():
    """Form processing portal to route and log member weekly savings safely with strict input filtering."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        member_id = request.form['member_id']
        amount_input = request.form['amount'].strip()
        # Capture the custom target calendar date string from the picker interface
        chosen_date_input = request.form.get('target_sunday_date', '').strip()
        
        # Validation Gate: Prevent empty values or formatting crashes
        if not amount_input or not chosen_date_input:
            flash("All form fields including the target date parameter are strictly required.", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for('record_deposit'))
            
        amount = float(amount_input)
        
        # 🛡️ INPUT FILTER GATE: Assert transaction integrity
        if amount <= 0:
            flash("Invalid Transaction! Deposit contributions must be strictly greater than UGX 0.", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for('record_deposit'))
        
        # Capture the current execution log timestamp for record audits
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Explicitly pass the user's custom chosen_date_input to target_sunday_date to fill missed gaps
        insert_query = """
            INSERT INTO deposits (member_id, amount, recorded_by, deposit_date, target_sunday_date) 
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (member_id, amount, session['user_id'], current_time, chosen_date_input))
        conn.commit()
        
        flash(f"Successfully recorded contribution entry of UGX {amount:,.0f} mapped to target date {chosen_date_input}!", "success")
        cursor.close()
        conn.close()
        return redirect(url_for('admin_dashboard'))
        
    # GET Request: Fetch members so admin can pick who is paying from a dropdown list
    cursor.execute("SELECT user_id, username FROM users WHERE LOWER(role) = 'member'")
    members = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('record_deposit.html', members=members, username=session['username'])


@app.route('/admin/members')
def view_members():
    """Pulls full user base schema table to audit registered community group profiles."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # FIX: Explicitly pulled the terms_accepted database field column into the cursor selection query array
    cursor.execute("SELECT user_id, username, contact_info, next_of_kin_info, role, account_status, is_online, terms_accepted FROM users")
    all_members = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('view_members.html', members=all_members, username=session['username'])


@app.route('/admin/complaints')
def view_complaints():
    """Fetches complaints and handles username lookups safely without strict JOIN assumptions."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Fetch usernames dictionary to map IDs seamlessly in memory
    cursor.execute("SELECT user_id, username FROM users")
    users_list = cursor.fetchall()
    user_map = {u['user_id']: u['username'] for u in users_list}
    
    # 2. Fetch raw complaints rows safely without guessing column structure details
    cursor.execute("SELECT * FROM complaints")
    raw_complaints = cursor.fetchall()
    
    processed_complaints = []
    for c in raw_complaints:
        # Automatically find whichever ID column exists in your complaints row layout
        sender_id = c.get('sender_id') or c.get('user_id') or c.get('member_id')
        
        processed_complaints.append({
            'complaint_id': c.get('complaint_id'),
            'message': c.get('message', '[No Message]'),
            'username': user_map.get(sender_id, f"User #{sender_id}")
        })
    
    cursor.close()
    conn.close()
    return render_template('view_complaints.html', complaints=processed_complaints, username=session['username'])

@app.route('/member/dashboard')
def member_dashboard():
    """Guarded portal route for member accounts equipped with dynamic savings milestone trend charts and active notifications query."""
    if 'user_id' not in session or str(session.get('role', '')).strip().lower() != 'member':
        return redirect(url_for('login'))
        
    member_id = session['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # SECURITY POLICY GATE ENFORCEMENT: Verify that they did not bypass by typing the URL directly
    cursor.execute("SELECT terms_accepted FROM users WHERE user_id = %s", (member_id,))
    status_check = cursor.fetchone()
    if status_check and not status_check['terms_accepted']:
        cursor.close()
        conn.close()
        return redirect(url_for('member_sign_policy'))
    
    # 1. Fetch total accumulated personal savings group pool (UGX)
    cursor.execute("SELECT SUM(amount) AS total_savings FROM deposits WHERE member_id = %s", (member_id,))
    savings_result = cursor.fetchone()
    total_savings = savings_result['total_savings'] if savings_result and savings_result['total_savings'] is not None else 0
    
    # 2. Fetch total logged complaints/alerts for this member
    cursor.execute("SELECT COUNT(*) AS total_complaints FROM complaints WHERE member_id = %s", (member_id,))
    complaints_result = cursor.fetchone()
    total_complaints = complaints_result['total_complaints'] if complaints_result else 0

    # 3. CORRECTED NOTIFICATION QUERY: Uses member_id instead of user_id to eliminate the 1054 crash
    cursor.execute(
        "SELECT notification_id, alert_message FROM notifications WHERE member_id = %s AND is_read = 0 ORDER BY notification_id DESC", 
        (member_id,)
    )
    active_notifications = cursor.fetchall()

    # 4. Monthly Cumulative Savings Trend Calculator
    chart_query = """
        SELECT YEAR(target_sunday_date) as s_year, MONTH(target_sunday_date) as s_month, SUM(amount) as monthly_sum
        FROM deposits
        WHERE member_id = %s
        GROUP BY YEAR(target_sunday_date), MONTH(target_sunday_date)
        ORDER BY s_year ASC, s_month ASC
    """
    cursor.execute(chart_query, (member_id,))
    trend_rows = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Process rows into arrays of strings for frontend JavaScript parsing loops
    chart_labels = []
    chart_data = []
    running_total = 0
    
    for row in trend_rows:
        month_name = calendar.month_name[row['s_month']][:3] # e.g., 'Jan', 'Feb'
        label_str = f"{month_name} {row['s_year']}"
        chart_labels.append(label_str)
        
        # Accumulate the running sum total to display growth pacing trends
        running_total += float(row['monthly_sum'])
        chart_data.append(running_total)
        
    # If no savings history exists yet, provide baseline initial parameters to prevent empty chart crashes
    if not chart_labels:
        chart_labels = ["No Data Available"]
        chart_data = [0]

    return render_template(
        'member_dashboard.html', 
        username=session['username'],
        total_savings=total_savings,
        total_complaints=total_complaints,
        chart_labels=chart_labels,
        chart_data=chart_data,
        notifications=active_notifications  # Sent along safely to your template
    )


@app.route('/logout')
def logout():
    """Clears system state tracking and logs out safely."""
    if 'user_id' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_online = 0 WHERE user_id = %s", (session['user_id'],))
        conn.commit()
        cursor.close()
        conn.close()
        
    session.clear() # Completely flushes session cookies
    return redirect(url_for('login'))

@app.route('/member/change-password', methods=['GET', 'POST'])
def change_password():
    """Securely handles member profile password rotations using SHA-256 verification."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # --- 1. RENDER SECURE PROFILE PAGE INTERFACE (GET) ---
    if request.method == 'GET':
        return render_template('change_password.html')
        
    # --- 2. PROCESS SECURE CRYPTOGRAPHICAL OVERWRITE (POST) ---
    current_pwd = request.form.get('current_password', '').strip()
    new_pwd = request.form.get('new_password', '').strip()
    confirm_pwd = request.form.get('confirm_password', '').strip()
    
    if not current_pwd or not new_pwd or not confirm_pwd:
        flash("All fields are strictly required to change your password.", "danger")
        return redirect(url_for('change_password'))
        
    if new_pwd != confirm_pwd:
        flash("Confirmation mismatch. Your new passwords do not match.", "danger")
        return redirect(url_for('change_password'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    member_id = session['user_id']
    
    cursor.execute("SELECT password_hash FROM users WHERE user_id = %s", (member_id,))
    user_record = cursor.fetchone()
    
    if user_record:
        hashed_current = hashlib.sha256(current_pwd.encode()).hexdigest()
        
        if hashed_current != user_record['password_hash']:
            flash("Incorrect current password verification failed.", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for('change_password'))
            
        hashed_new = hashlib.sha256(new_pwd.encode()).hexdigest()
        cursor.execute("UPDATE users SET password_hash = %s WHERE user_id = %s", (hashed_new, member_id))
        conn.commit()
        flash("Your profile password has been successfully updated!", "success")
        
    cursor.close()
    conn.close()
    return redirect(url_for('change_password'))



def send_payout_email(recipient_email, member_name, total_saved, calendar_year):
    """Helper routine to dispatch an isolated year-end HTML receipt statement via Mailtrap."""
    # 🧪 Mailtrap Sandbox Configuration Settings
    smtp_server = "sandbox.smtp.mailtrap.io"
    smtp_port = 2525
    
    # PASTE YOUR COPIED MAILTRAP STRINGS DIRECTLY HERE:
    sender_username = "YOUR_MAILTRAP_USERNAME_HERE"  
    sender_password = "YOUR_MAILTRAP_PASSWORD_HERE"  
    
    # Official masking address shown to members
    sender_display_email = "receipts@sundaysavings.org"

    # Craft the email transport container
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"☀️ Sunday Savings System: Year-End Payout Receipt {calendar_year}"
    msg['From'] = f"Sunday Savings System <{sender_display_email}>"
    msg['To'] = recipient_email

    # Construct clean, isolated HTML message markup targeting only this member's variables
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f8f9fa; padding: 20px; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 25px; border-radius: 8px; border: 1px solid #dee2e6;">
            <h2 style="color: #198754; border-bottom: 2px solid #198754; padding-bottom: 10px;">Sunday Savings System</h2>
            <p>Hello <strong>{member_name}</strong>,</p>
            <p>Your annual cycle payout statement for the calendar year <strong>{calendar_year}</strong> has been officially compiled and archived.</p>
            <div style="background-color: #cfe2ff; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 5px solid #0d6efd;">
                <h4 style="margin: 0; color: #052c65; text-transform: uppercase; font-size: 0.85rem;">Total Accumulated Savings Pool Balance Issued:</h4>
                <p style="font-size: 1.8rem; font-weight: bold; margin: 10px 0 0 0; color: #0a58ca;">UGX {total_saved:,.0f}</p>
            </div>
            <p style="font-size: 0.85rem; color: #6c757d;">Your active transactional contributions ledger balance has now been reset to zero for the upcoming operational cycle.</p>
            <hr style="border: 0; border-top: 1px solid #dee2e6; margin: 20px 0;">
            <p style="font-size: 0.8rem; color: #adb5bd; text-align: center;">This is an automated system dispatch statement. Please do not reply directly to this mailer pipeline.</p>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_content, 'html'))

    try:
        # Establish connection to Mailtrap's testing servers
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Secure connection via TLS
        server.login(sender_username, sender_password)
        server.sendmail(sender_display_email, recipient_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP dispatch failure logging fallback notification: {e}")
        return False


@app.route('/admin/archive-rollover', methods=['POST'])
def archive_rollover():
    """Calculates year-end balances, copies records to archive table, sends emails, and clears active logs."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    current_year = datetime.now().year
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. Fetch total accumulated savings grouped by member username and pull contact email strings
        query_totals = """
            SELECT u.username AS member_name, u.contact_info, SUM(d.amount) AS total_saved
            FROM deposits d
            JOIN users u ON d.member_id = u.user_id
            GROUP BY d.member_id
        """
        cursor.execute(query_totals)
        member_balances = cursor.fetchall()
        
        if not member_balances:
            flash("No active savings balances found to snapshot or rollover.", "warning")
            cursor.close()
            conn.close()
            return redirect(url_for('admin_dashboard'))
            
        # 2. Iterate through each row balance record, replicate into archive, and send isolated alert email
        insert_archive = """
            INSERT INTO year_end_archive (archive_year, member_name, total_amount_saved)
            VALUES (%s, %s, %s)
        """
        emails_sent = 0
        for balance in member_balances:
            # Commit the archive snapshot line
            cursor.execute(insert_archive, (
                current_year, 
                balance['member_name'], 
                float(balance['total_saved'])
            ))
            
            # If the member's contact info is a valid email, trigger the isolated payout email receipt pipeline
            if balance['contact_info'] and '@' in balance['contact_info']:
                success = send_payout_email(
                    recipient_email=balance['contact_info'].strip(),
                    member_name=balance['member_name'],
                    total_saved=float(balance['total_saved']),
                    calendar_year=current_year
                )
                if success:
                    emails_sent += 1
            
        # 3. Clear out active contributions ledger row records so the new year starts at zero
        cursor.execute("DELETE FROM deposits")

        # ========================================================================
        # RESTORED ATOMIC AUTO-INCREMENT RESET COMMANDS (FROM PROJECT 2)
        # ========================================================================
        cursor.execute("ALTER TABLE deposits AUTO_INCREMENT = 1")
        
        
        # Commit all table alterations safely together as an atomic unit
        conn.commit()
        flash(f"Year-End Payout complete! Successfully archived financial blocks for {current_year} and emailed {emails_sent} statements.", "success")
        
    except mysql.connector.Error as err:
        conn.rollback() # Rollback adjustments if database execution errors happen
        flash(f"An error occurred during rollover execution: {err}", "danger")
        
    cursor.close()
    conn.close()
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/logs')
def view_logs():
    """Pulls historical year-end payout data sheets to view community lifecycle metrics."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Query all historical metrics out from your year_end_archive architecture layout
    cursor.execute("SELECT * FROM year_end_archive ORDER BY archive_year DESC, archived_at DESC")
    archive_logs = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('view_logs.html', logs=archive_logs, username=session['username'])

@app.route('/admin/complaints/clear/<int:complaint_id>', methods=['POST'])
def clear_complaint(complaint_id):
    """Admin-only controller action route to permanently delete or dismiss a complaint ticket from the database."""
    if 'user_id' not in session or str(session.get('role', '')).strip().lower() not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Atomic purge query execution
        delete_query = "DELETE FROM complaints WHERE complaint_id = %s"
        cursor.execute(delete_query, (complaint_id,))
        conn.commit() # Formally commit changes to Laragon MySQL logs
        
        flash('Complaint record has been permanently cleared from the system pipeline.', 'success')
    except Exception as err:
        flash(f"Failed to execute complaint purge operation: {str(err)}", 'danger')
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('admin_view_complaints'))


@app.route('/admin/members/add', methods=['GET', 'POST'])
def add_member():
    """Processes administrative creation of new group saving profiles securely."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        full_name = request.form.get('full_name', '').strip()
        contact_info = request.form.get('contact_info', '').strip()
        # Capture the optional Next of Kin field text safely
        next_of_kin = request.form.get('next_of_kin_info', '').strip()
        role = request.form.get('role', 'member').strip().lower()
        
        # If Next of Kin was left blank, cast it to None so it stores as a clean NULL in MySQL
        if not next_of_kin:
            next_of_kin = None
        
        if not username or not password or not full_name or not contact_info:
            flash("All fields including full name and contact details are strictly required.", "danger")
            return redirect(url_for('add_member'))
            
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                flash(f"The username '{username}' is already taken. Please choose another.", "danger")
                cursor.close()
                conn.close()
                return redirect(url_for('add_member'))
                
            # Updated query signature to pass both contact_info and optional next_of_kin_info field columns cleanly
            insert_query = """
                INSERT INTO users (username, password_hash, full_name, contact_info, next_of_kin_info, role, account_status, is_online)
                VALUES (%s, %s, %s, %s, %s, %s, 'active', 0)
            """
            cursor.execute(insert_query, (username, hashed_password, full_name, contact_info, next_of_kin, role))
            conn.commit()
            flash(f"Successfully registered user profile '{username}'! Provide them their login details.", "success")
            
            cursor.close()
            conn.close()
            return redirect(url_for('view_members'))
            
        except mysql.connector.Error as err:
            flash(f"Database registration error: {err}", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for('add_member'))
            
    return render_template('add_member.html', username=session['username'])



@app.route('/admin/members/statement/<int:target_user_id>')
def view_member_statement(target_user_id):
    """Queries individual user balance histories to generate a printable banking statement."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Fetch user data details
    cursor.execute("SELECT username, full_name, role FROM users WHERE user_id = %s", (target_user_id,))
    member_profile = cursor.fetchone()
    
    if not member_profile:
        flash("Target profile was not found inside active database infrastructure.", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for('view_members'))
        
    # 2. Fetch individual contribution rows chronologically
    query_history = """
        SELECT amount, deposit_date 
        FROM deposits 
        WHERE member_id = %s 
        ORDER BY deposit_date ASC
    """
    cursor.execute(query_history, (target_user_id,))
    transactions = cursor.fetchall()
    
    # 3. Calculate running individual total sum
    total_saved = sum(float(tx['amount']) for tx in transactions)
    
    cursor.close()
    conn.close()
    
    return render_template(
        'print_statement.html',
        profile=member_profile,
        transactions=transactions,
        total_saved=total_saved,
        generation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

@app.route('/admin/master-ledger/print')
def print_master_ledger():
    """Compiles all records to construct a printable global annual transactional ledger report."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Query every deposit tracking block row executed throughout the system cycle
    query_master = """
        SELECT d.deposit_id, u.full_name, u.username, d.amount, d.deposit_date 
        FROM deposits d
        JOIN users u ON d.member_id = u.user_id
        ORDER BY d.deposit_date DESC
    """
    cursor.execute(query_master)
    master_logs = cursor.fetchall()
    
    # Calculate group pool total values
    pool_sum = sum(float(row['amount']) for row in master_logs)
    
    cursor.close()
    conn.close()
    
    return render_template(
        'print_master_ledger.html',
        logs=master_logs,
        pool_sum=pool_sum,
        generation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )


@app.route('/admin/members/toggle-status/<int:target_user_id>', methods=['POST'])
def toggle_member_status(target_user_id):
    """Administratively shifts a user account status between Active and Suspended states."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Look up the current condition of the target user profile
    cursor.execute("SELECT username, account_status FROM users WHERE user_id = %s", (target_user_id,))
    target_user = cursor.fetchone()
    
    if not target_user:
        flash("Target user profile was not found inside active database infrastructure.", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for('view_members'))
        
    # Prevent administrators from accidentally locking themselves out of the dashboard
    if target_user_id == session['user_id']:
        flash("Security Block: You cannot suspend your own active administrative session profile.", "warning")
        cursor.close()
        conn.close()
        return redirect(url_for('view_members'))
        
    # 2. Evaluate string flag and flip state to alternative parameter
    current_status = str(target_user['account_status']).strip().lower()
    new_status = 'suspended' if current_status == 'active' else 'active'
    
    # 3. Commit state adjustment update and terminate sessions if suspending them
    try:
        cursor.execute("UPDATE users SET account_status = %s WHERE user_id = %s", (new_status, target_user_id))
        
        # Force baseline status offline if suspending them immediately
        if new_status == 'suspended':
            cursor.execute("UPDATE users SET is_online = 0 WHERE user_id = %s", (target_user_id,))
            
        conn.commit()
        flash(f"Profile state for @{target_user['username']} successfully updated to {new_status.upper()}!", "success")
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f"Database error during status modification: {err}", "danger")
        
    cursor.close()
    conn.close()
    return redirect(url_for('view_members'))

@app.route('/admin/members/delete/<int:target_user_id>', methods=['POST'])
def delete_member(target_user_id):
    """Safely executes cascading deletion logic to clean out active logs and drop profiles cleanly."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    # Fail-safe gate: block administrators from executing a self-destructive action loop
    if target_user_id == session['user_id']:
        flash("Security Block: You cannot delete your own active administrative session profile.", "warning")
        return redirect(url_for('view_members'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Check if user profile actually exists before modifying row entities
        cursor.execute("SELECT username FROM users WHERE user_id = %s", (target_user_id,))
        user_record = cursor.fetchone()
        
        if not user_record:
            flash("Target user profile was not found inside active database infrastructure.", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for('view_members'))
            
        # ⚡ ORDERED CASCADING DELETION PIPELINE (Task 2)
        # Step A: Delete matching child rows from 'complaints' table mapped via foreign keys
        cursor.execute("DELETE FROM complaints WHERE member_id = %s", (target_user_id,))
        
        # Step B: Delete matching financial transaction logs inside 'deposits' table
        cursor.execute("DELETE FROM deposits WHERE member_id = %s", (target_user_id,))
        
        # Step C: Erase parent account row record out from the base 'users' framework safely
        cursor.execute("DELETE FROM users WHERE user_id = %s", (target_user_id,))
        
        # Commit table operations together as an atomic transactional save unit
        conn.commit()
        flash(f"Account for @{user_record['username']} and all linked tracking dependencies were permanently purged.", "success")
        
    except mysql.connector.Error as err:
        conn.rollback() # Rollback modifications to restore integrity if an query error happens
        flash(f"Database relational error occurred during deletion execution: {err}", "danger")
        
    cursor.close()
    conn.close()
    return redirect(url_for('view_members'))

@app.route('/admin/members/reset-password/<int:target_user_id>', methods=['POST'])
def admin_reset_password(target_user_id):
    """Administratively forces a password overwrite for a member account using SHA-256."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    new_password = request.form.get('new_temporary_password', '').strip()
    
    if not new_password:
        flash("Password reset error: The new password field cannot be blank.", "danger")
        return redirect(url_for('view_members'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Check if the target user actually exists
        cursor.execute("SELECT username FROM users WHERE user_id = %s", (target_user_id,))
        user_record = cursor.fetchone()
        
        if not user_record:
            flash("Target user profile was not found inside active database infrastructure.", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for('view_members'))
            
        # Hash the new temporary string safely to maintain cryptographical compliance
        hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
        
        # Overwrite the password field directly
        cursor.execute("UPDATE users SET password_hash = %s WHERE user_id = %s", (hashed_password, target_user_id))
        conn.commit()
        
        flash(f"Successfully updated access credentials for @{user_record['username']}!", "success")
        
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f"Database password modification error: {err}", "danger")
        
    cursor.close()
    conn.close()
    return redirect(url_for('view_members'))


import calendar

def get_sundays_matrix(member_id, year, month):
    """Helper function that returns a list of dictionaries tracking paid/missed/future Sundays."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Creating our matching mask string (e.g., '2026-10-%')
    target_pattern = f"{year}-{month:02d}-%"

    # CORRECTED QUERY: Removing 'status' column to match your exact database table schema columns fields
    query = """
        SELECT DISTINCT target_sunday_date
        FROM deposits
        WHERE member_id = %s
        AND target_sunday_date LIKE %s
    """
    cursor.execute(query, (member_id, target_pattern))
    paid_rows = cursor.fetchall()

    # Dynamic look-up array aggregator handling both datetime.date objects and raw textual strings cleanly
    paid_sundays = set()
    for r in paid_rows:
        date_val = r['target_sunday_date']
        if date_val:
            if hasattr(date_val, 'strftime'):
                paid_sundays.add(date_val.strftime('%Y-%m-%d'))
            else:
                paid_sundays.add(str(date_val).strip()[:10])

    cursor.close()
    conn.close()

    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.itermonthdays4(year, month)

    today_date = datetime.now().date()
    sundays_matrix = []

    for d_year, d_month, d_day, weekday in month_days:
        if weekday == 6 and d_month == month:
            date_str = f"{d_year}-{d_month:02d}-{d_day:02d}"
            formatted_display_date = f"Sunday, {d_day} {calendar.month_name[month][:3]}"

            current_loop_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            is_paid = date_str in paid_sundays

            if is_paid:
                status_label = 'PAID'
            elif current_loop_date > today_date:
                status_label = 'FUTURE'
            else:
                status_label = 'MISSED'

            sundays_matrix.append({
                'date_string': date_str,
                'display_label': formatted_display_date,
                'status': status_label
            })

    return sundays_matrix


@app.route('/admin/members/calendar/<int:target_user_id>', methods=['GET', 'POST'])
def admin_member_calendar(target_user_id):
    """Admin route upgraded to inspect and dynamically filter a specific member's calendar."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Fetch current profile targets to verify the URL parameter
    cursor.execute("SELECT user_id, username, full_name FROM users WHERE user_id = %s", (target_user_id,))
    member = cursor.fetchone()
    
    if not member:
        flash("Target member matrix profile not found.", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for('view_members'))
        
    # 2. Fetch all registered members to fill the drop-down selector form
    cursor.execute("SELECT user_id, username FROM users WHERE LOWER(role) = 'member' ORDER BY username ASC")
    all_members = cursor.fetchall()
    
    # 3. Establish temporal filter states (Default to current month/year unless submitted via form)
    current_date = datetime.now()
    year = int(request.form.get('year') or current_date.year)
    month = int(request.form.get('month') or current_date.month)
    month_name = calendar.month_name[month]
    
    cursor.close()
    conn.close()
    
    # 4. Generate the matrix array using your existing helper logic block
    matrix = get_sundays_matrix(target_user_id, year, month)
    
    # Define year and month options dynamically for our HTML selectors
    months_choices = [(i, calendar.month_name[i]) for i in range(1, 13)]
    years_choices = [current_date.year - 1, current_date.year, current_date.year + 1]
    
    return render_template(
        'admin_member_calendar.html', 
        username=session['username'], 
        member=member, 
        members_list=all_members,
        matrix=matrix, 
        current_month_name=month_name,
        current_month=month, 
        current_year=year,
        months_choices=months_choices,
        years_choices=years_choices
    )



@app.route('/admin/year-end-payout', methods=['POST'])
def year_end_payout():
    """Processes final balances for all members, updates statuses, and dispatches receipts unless bypassed."""
    if 'role' not in session or str(session['role']).strip().lower() not in ['admin', 'super_admin']:
        flash("Unauthorized access. Only system administrators can process year-end payouts.", "danger")
        return redirect(url_for('login'))

    # Read the hidden variable out from the POST form payload dictionary safely
    skip_email_param = request.form.get('skip_email', 'false').lower() == 'true'
    # Intercept query argument to check if admin explicitly authorized ignoring missing profiles
    ignore_missing_param = request.args.get('ignore_missing', 'false').lower() == 'true'
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch active members tracking profiles
        query_members = """
            SELECT u.user_id, u.username, u.contact_info 
            FROM users u 
            WHERE LOWER(u.role) = 'member' AND LOWER(u.account_status) = 'active'
        """
        cursor.execute(query_members)
        members = cursor.fetchall()

        if not members:
            flash("No active member records found to process.", "warning")
            cursor.close()
            conn.close()
            return redirect(url_for('admin_dashboard'))

        current_year = datetime.now().year

        # ========================================================
        # PATHWAY A: EMERGENCY BYPASS (RESET AND CLEAR LEDGER ONLY)
        # ========================================================
        if skip_email_param:
            cursor.execute("DELETE FROM deposits")
            # Reset increment counter targets to keep sequence numbers orderly
            cursor.execute("ALTER TABLE deposits AUTO_INCREMENT = 1")
            conn.commit()
            
            # Clear any old warning list from session memory so the banner disappears
            session.pop('missing_email_usernames', None)
            
            flash(f"Success! Year-end ledger reset complete. Financial logs for {current_year} cleared down to UGX 0 (Automated messaging pipeline was bypassed).", "success")
            return redirect(url_for('admin_dashboard'))

        # ========================================================
        # PATHWAY B: STANDARD RUN (SELECTIVE DISPATCH PIPELINE)
        # ========================================================
        
        # FAIL-SAFE GATE 1: Block completely if the system credentials inside .env are blank
        if not GMAIL_USER or not GMAIL_APP_PASSWORD:
            raise RuntimeError("Missing live server configurations inside your secret .env key registry file.")

        # Pre-audit user contact fields to identify unconfigured email rows
        unconfigured_members = []
        for member in members:
            recipient_email = member['contact_info']
            if not recipient_email or '@' not in str(recipient_email):
                unconfigured_members.append(member['username'])

        # If missing profiles are discovered, and the admin did not explicitly override, halt execution
        if unconfigured_members and not ignore_missing_param:
            session['missing_email_usernames'] = unconfigured_members
            flash("Missing Email Configuration Warning", "warning")
            cursor.close()
            conn.close()
            return redirect(url_for('admin_dashboard'))

        processed_count = 0
        skipped_count = 0
        
        for member in members:
            user_id = member['user_id']
            username = member['username']
            recipient_email = member['contact_info']

            query_savings = "SELECT SUM(amount) AS total_savings FROM deposits WHERE member_id = %s"
            cursor.execute(query_savings, (user_id,))
            savings_result = cursor.fetchone()
            total_payout = savings_result['total_savings'] if savings_result and savings_result['total_savings'] else 0.0

            if recipient_email and '@' in str(recipient_email):
                email_subject = f"Sunday Savings System - {current_year} Year-End Payout Receipt"
                email_body = f"""Hello {username},

This is an automated financial summary statement from your Sunday Savings Tracking System group.

Your year-end account settlement has been successfully processed by the system administrators.

==============================================
            FINAL PAYOUT SUMMARY              
==============================================
Member ID         : {user_id}
Username          : {username}
Settlement Year   : {current_year}
Total Accumulated : UGX {total_payout:,.2f}
Payout Status     : DISBURSED & COMPLETED
==============================================

Your accumulated savings have been prepared for distribution according to your registered collection profile. 

Thank you for your dedicated contributions throughout the year!

Best regards,
Sunday Savings System Management"""

                email_success = send_system_email(str(recipient_email).strip(), email_subject, email_body)
                
                if not email_success:
                    raise RuntimeError(f"SMTP transmission delivery failed while processing statement dispatch route for @{username}.")
                    
                processed_count += 1
            else:
                skipped_count += 1
                print(f">>> SKIPPED NOTIFICATION: Member @{username} tracks via phone parameters; digital receipt bypassed.")

        # Wipe active contribution ledger records cleanly to restart cycle at zero
        cursor.execute("DELETE FROM deposits")
        conn.commit()
        
        # Clear any old warning list from session memory so the banner disappears
        session.pop('missing_email_usernames', None)
        
        if skipped_count > 0:
            flash(f"Success! Year-end payout processed. Receipts sent to {processed_count} members. Skipped {skipped_count} profile(s) missing an email address. Deposits ledger successfully reset.", "success")
        else:
            flash(f"Success! Year-end payout processed. Receipts sent to {processed_count} active members and database deposits ledger successfully reset.", "success")

    except Exception as e:
        conn.rollback() 
        # Clear warning on critical crash so the layout doesn't get stuck in a bad state
        session.pop('missing_email_usernames', None)
        print(f">>> CRITICAL SYSTEM ERROR DURING PAYOUT RUN: {e}")
        flash(f"Settlement Pipeline Aborted: {str(e)} Your ledger records were NOT modified.", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_dashboard'))


# ==========================================
# 4. DIRECT IN-APP NOTIFICATION SYSTEM ROUTING CONTROLLERS
# ==========================================

@app.route('/admin/notifications/send', methods=['POST'])
def send_direct_notification():
    """Captures custom announcement logs from administrators and binds them to member profiles."""
    if 'role' not in session or str(session['role']).strip().lower() not in ['admin', 'super_admin']:
        flash("Unauthorized access. Notifications can only be filed by administrators.", "danger")
        return redirect(url_for('login'))
        
    target_member_id = request.form.get('target_member_id', '').strip()
    alert_text = request.form.get('alert_message', '').strip()
    
    if not target_member_id or not alert_text:
        flash("Notification failure: Target selection and message text parameters are strictly required.", "danger")
        return redirect(url_for('admin_dashboard'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Injects the unread announcement log row straight into your notifications table schema
        insert_query = "INSERT INTO notifications (member_id, alert_message, is_read) VALUES (%s, %s, 0)"
        cursor.execute(insert_query, (target_member_id, alert_text))
        conn.commit()
        flash("In-app notification alert successfully blasted to the target member's dashboard view panels!", "success")
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f"Database error while creating notification log: {err}", "danger")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('admin_dashboard'))

@app.route('/member/my-calendar')
def view_my_calendar():
    """Renders the standalone dedicated calendar matrix view panel for a standard member account."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role != 'member':
        return redirect(url_for('login'))
        
    member_id = session['user_id']
    current_date = datetime.now()
    
    # Generate the calendar matrix array dynamically for the current year and month parameters
    matrix = get_sundays_matrix(member_id, current_date.year, current_date.month)
    month_name = calendar.month_name[current_date.month]
    
    return render_template(
        'member_calendar.html',
        username=session['username'],
        matrix=matrix,
        current_month=month_name,
        current_year=current_date.year
    )

@app.route('/member/full-history')
def view_full_history():
    """Queries all chronological transactional savings rows to generate a standalone lifetime tracking ledger sheet."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role != 'member':
        return redirect(url_for('login'))
        
    member_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Query every chronological deposit contribution row logged on this profile since registration
    cursor.execute("SELECT amount, deposit_date, target_sunday_date FROM deposits WHERE member_id = %s ORDER BY deposit_date DESC", (member_id,))
    full_history = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('member_history.html', username=session['username'], full_history=full_history)

@app.route('/admin/members/edit/<int:target_user_id>', methods=['GET', 'POST'])
def edit_member(target_user_id):
    """Processes administrative profile updates for names, contacts, and next of kin details securely."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # --- 1. RENDER EDIT INTERFACE PRE-FILLED WITH PROFILE DATA (GET) ---
    if request.method == 'GET':
        cursor.execute("SELECT user_id, username, full_name, contact_info, next_of_kin_info, role FROM users WHERE user_id = %s", (target_user_id,))
        member_record = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not member_record:
            flash("Target profile was not found inside active database infrastructure.", "danger")
            return redirect(url_for('view_members'))
            
        return render_template('edit_member.html', member=member_record, username=session['username'])
        
    # --- 2. PROCESS SECURE DATABASE ROW MODIFICATIONS (POST) ---
    full_name = request.form.get('full_name', '').strip()
    contact_info = request.form.get('contact_info', '').strip()
    next_of_kin = request.form.get('next_of_kin_info', '').strip()
    role = request.form.get('role', 'member').strip().lower()
    
    # Cast empty next-of-kin strings back to None so they map as clean NULLs in MySQL
    if not next_of_kin:
        next_of_kin = None
        
    if not full_name or not contact_info:
        flash("Profile modification error: Full Name and Primary Contact parameters cannot be blank.", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for('edit_member', target_user_id=target_user_id))
        
    try:
        update_query = """
            UPDATE users 
            SET full_name = %s, contact_info = %s, next_of_kin_info = %s, role = %s 
            WHERE user_id = %s
        """
        cursor.execute(update_query, (full_name, contact_info, next_of_kin, role, target_user_id))
        conn.commit()
        flash(f"Successfully updated system profile details for user record #{target_user_id}!", "success")
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f"Database modification error occurred: {err}", "danger")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('view_members'))

    # ========================================================================
# ADMINISTRATIVE ROUTE: RETROACTIVE SAVINGS ENTRY OVERWRITE (TASK A)
# ========================================================================
@app.route('/admin/retroactive-deposit', methods=['GET', 'POST'])
def admin_retroactive_deposit():
    """Form processing portal to route, log, or overwrite missed historical Sunday savings balances."""
    if 'user_id' not in session or str(session.get('role', '')).strip().lower() not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        member_id = request.form.get('member_id')
        target_sunday_date = request.form.get('target_sunday_date')
        amount = request.form.get('amount')
        
        if not member_id or not target_sunday_date or not amount:
            flash('All configuration adjustment parameters are strictly mandatory.', 'danger')
            return redirect(url_for('admin_retroactive_deposit'))
            
        try:
            # FIX: Implemented ON DUPLICATE KEY UPDATE to overwrite the amount instead of summing items up
            upsert_query = """
                INSERT INTO deposits (member_id, amount, target_sunday_date, deposit_date) 
                VALUES (%s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE 
                    amount = VALUES(amount),
                    deposit_date = NOW();
            """
            cursor.execute(upsert_query, (member_id, amount, target_sunday_date))
            conn.commit() # Formally commit changes to Laragon MySQL logs
            
            flash('Retroactive savings override record updated and synchronized successfully!', 'success')
            return redirect(url_for('admin_retroactive_deposit'))
            
        except Exception as err:
            conn.rollback()
            flash(f"Database modification sequence failed: {str(err)}", 'danger')
            return redirect(url_for('admin_retroactive_deposit'))
        finally:
            cursor.close()
            conn.close()

    # GET Method: Fetches member list options for the dropdown selector layout frame field
    try:
        cursor.execute("SELECT user_id, username FROM users WHERE LOWER(role) = 'member' ORDER BY username ASC")
        members = cursor.fetchall()
        return render_template('retroactive_deposit.html', members=members, username=session['username'])
    except Exception as err:
        flash(f"Failed to fetch database user arrays safely: {str(err)}", 'danger')
        return redirect('/admin/dashboard')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


    # GET Method: Fetches member list options for the dropdown selector layout frame field
    try:
        cursor.execute("SELECT user_id, username FROM users WHERE LOWER(role) = 'member' ORDER BY username ASC")
        members = cursor.fetchall()
        return render_template('retroactive_deposit.html', members=members, username=session['username'])
    except Exception as err:
        flash(f"Failed to fetch database user arrays safely: {str(err)}", 'danger')
        return redirect('/admin/dashboard')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# ========================================================================
# ADMINISTRATIVE ROUTE: GLOBAL GROUP CALENDAR SAVINGS MATRIX BOARD (TASK B)
# ========================================================================
@app.route('/admin/global-calendar', methods=['GET'])
def admin_global_calendar():
    """Compiles all active member profiles alongside their calculated paid/missed weekly rows arrays."""
    if 'user_id' not in session or str(session.get('role', '')).strip().lower() not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    # Handles calendar date extraction and matrix processing loop for members
    # Please refer to the full source code block in the provided implementation for complete matrix assembly.
    now = datetime.now()
    current_year = int(request.args.get('year', now.year))
    current_month = int(request.args.get('month', now.month))
    month_name = calendar.month_name[current_month]
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, username FROM users WHERE LOWER(role) = 'member' ORDER BY username ASC")
    system_members = cursor.fetchall()
    cursor.close()
    conn.close()
    
    processed_global_rows = [{'username': m['username'], 'matrix': get_sundays_matrix(m['user_id'], current_year, current_month)} for m in system_members]
    
    return render_template(
        'admin_global_calendar.html',
        global_matrix_data=processed_global_rows,
        current_year=current_year,
        current_month=current_month,
        current_month_name=month_name,
        username=session['username']
    )


@app.route('/member/calendar', methods=['GET', 'POST'])
def member_calendar():
    """Upgraded member route to inspect and dynamically filter their own monthly calendar."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role != 'member':
        return redirect(url_for('login'))
        
    member_id = session['user_id']
    
    # Establish temporal filter states (Default to current month/year unless submitted via form)
    current_date = datetime.now()
    
    if request.method == 'POST':
        year = int(request.form.get('year') or current_date.year)
        month = int(request.form.get('month') or current_date.month)
    else:
        year = int(request.args.get('year') or current_date.year)
        month = int(request.args.get('month') or current_date.month)
        
    month_name = calendar.month_name[month]
    
    # Generate the matrix array using your existing robust helper logic block
    matrix = get_sundays_matrix(member_id, year, month)
    
    # Define year and month options dynamically for our HTML selectors
    months_choices = [(i, calendar.month_name[i]) for i in range(1, 13)]
    years_choices = [current_date.year - 1, current_date.year, current_date.year + 1]
    
    return render_template(
        'member_calendar.html', 
        username=session['username'], 
        matrix=matrix, 
        current_month_name=month_name,
        current_month=month, 
        current_year=year,
        months_choices=months_choices,
        years_choices=years_choices
    )


@app.route('/member/savings-trend')
def member_savings_trend():
    """Dedicated route to display a member's cumulative monthly metrics chart."""
    if 'user_id' not in session or str(session.get('role', '')).strip().lower() != 'member':
        return redirect(url_for('login'))
        
    member_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    chart_query = """
        SELECT YEAR(target_sunday_date) as s_year, MONTH(target_sunday_date) as s_month, SUM(amount) as monthly_sum
        FROM deposits
        WHERE member_id = %s
        GROUP BY YEAR(target_sunday_date), MONTH(target_sunday_date)
        ORDER BY s_year ASC, s_month ASC
    """
    cursor.execute(chart_query, (member_id,))
    trend_rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    chart_labels = []
    chart_data = []
    running_total = 0
    
    for row in trend_rows:
        month_name = calendar.month_name[row['s_month']][:3]
        chart_labels.append(f"{month_name} {row['s_year']}")
        running_total += float(row['monthly_sum'])
        chart_data.append(running_total)
        
    if not chart_labels:
        chart_labels = ["No Data Available"]
        chart_data = [0]
        
    return render_template(
        'member_trend.html',
        username=session['username'],
        chart_labels=chart_labels,
        chart_data=chart_data
    )

@app.route('/member/submit-complaint', methods=['POST'])
def member_submit_complaint():
    """Controller processing endpoint route to log submitted member help tickets into database fields."""
    if 'user_id' not in session or str(session.get('role', '')).strip().lower() != 'member':
        return redirect(url_for('login'))
        
    member_id = session['user_id']
    
    # Extract values from our modal input elements
    title_category = request.form.get('title')
    message_body = request.form.get('description')
    
    if not title_category or not message_body:
        flash('Complaint subject topic and description body entries are mandatory.', 'danger')
        return redirect(url_for('member_dashboard'))
        
    # Combine category and text into one clean string layout block
    combined_message = f"[{title_category}] {message_body}"
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # CORRECTED INSERT SYSTEM: Targets the 'message' column field to match your actual database schema
        insert_query = """
            INSERT INTO complaints (member_id, message) 
            VALUES (%s, %s)
        """
        cursor.execute(insert_query, (member_id, combined_message))
        conn.commit() # Safely save record logs into your Laragon local database server
        
        flash('Your grievance help ticket has been successfully dispatched to the admin panel!', 'success')
    except Exception as err:
        flash(f"System failed logging complaint query operations arrays: {str(err)}", 'danger')
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('member_dashboard'))

@app.route('/admin/view-complaints')
def admin_view_complaints():
    """Central grievance monitoring desk routing endpoint linking member IDs to usernames in-memory."""
    if 'user_id' not in session or str(session.get('role', '')).strip().lower() not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # CORRECTED ADMIN QUERY: Pulls c.message and maps user_id via your member_id foreign key bridge
        query = """
            SELECT c.complaint_id, c.member_id, c.message, u.username, u.full_name
            FROM complaints c
            JOIN users u ON c.member_id = u.user_id
            ORDER BY c.complaint_id DESC
        """
        cursor.execute(query)
        complaints_list = cursor.fetchall()
        
        return render_template(
            'view_complaints.html',
            username=session['username'],
            complaints=complaints_list
        )
        
    except Exception as err:
        flash(f"Database error loading administrative grievances console logs: {str(err)}", 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        cursor.close()
        conn.close()

# FIX: Adding this explicit route decorator clears the 404 Not Found error instantly!
@app.route('/member/notification/dismiss/<int:notification_id>', methods=['POST'])
def dismiss_notification(notification_id):
    """Marks a specific notification as read in the database so it vanishes from the dashboard."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_role = str(session.get('role', '')).strip().lower()
    if user_role not in ['admin', 'super_admin', 'member']:
        return redirect(url_for('login'))
        
    member_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # FIX: Explicitly updates using notification_id and safeguards it via member_id (user_id column)
        update_query = "UPDATE notifications SET is_read = 1 WHERE notification_id = %s AND member_id = %s"
        cursor.execute(update_query, (notification_id, member_id))
        conn.commit()
        flash("Notification dismissed successfully.", "success")
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f"Database error while dismissing notification: {err}", "danger")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('member_dashboard'))

@app.route('/member/sign-policy', methods=['GET', 'POST'])
def member_sign_policy():
    """Forces first-time logging members to explicitly review and accept strict group terms."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    member_id = session['user_id']
    
    if request.method == 'POST':
        rule_no_loans = request.form.get('rule_no_loans')
        rule_december_only = request.form.get('rule_december_only')
        
        if not rule_no_loans or not rule_december_only:
            flash("You must read and check both validation boxes to accept the project terms and proceed.", "danger")
            return redirect(url_for('member_sign_policy'))
            
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            update_query = "UPDATE users SET terms_accepted = TRUE, agreed_at = %s WHERE user_id = %s"
            cursor.execute(update_query, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), member_id))
            conn.commit()
            
            flash("Thank you! You have successfully signed the Sunday Savings Project Agreement policy document.", "success")
            return redirect(url_for('member_dashboard'))
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f"System failed saving your policy signature record: {err}", "danger")
            return redirect(url_for('member_sign_policy'))
        finally:
            cursor.close()
            conn.close()
            
    return render_template('sign_policy.html', username=session['username'])

@app.route('/admin/members/view-policy/<int:target_user_id>')
def admin_view_policy(target_user_id):
    """Fetches and displays an individual member's policy signature tracking sheet for printing or audit disputes."""
    if 'user_id' not in session or str(session.get('role', '')).strip().lower() not in ['admin', 'super_admin']:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Fetch target member details using the user_id URL parameter mapping
    cursor.execute("SELECT user_id, username, full_name, contact_info, terms_accepted, agreed_at FROM users WHERE user_id = %s", (target_user_id,))
    member = cursor.fetchone()
    
    if not member:
        cursor.close()
        conn.close()
        flash("Target profile record was not found inside active database logs.", "danger")
        return redirect(url_for('view_members'))
        
    # ========================================================================
    # RESTORED SELECTION PIPELINE: AUTOMATICALLY FETCH ALL REGISTERED ADMINS
    # ========================================================================
    cursor.execute("SELECT full_name FROM users WHERE LOWER(role) IN ('admin', 'super_admin') ORDER BY full_name ASC")
    admins_list = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Passes both the member record and your full admin rows context array into your html layout file cleanly
    return render_template(
        'print_policy_receipt.html', 
        member=member, 
        admins=admins_list, 
        generation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )





if __name__ == '__main__':
    # Starts Flask with live hot-reloading active for code edits
    app.run(debug=True)
