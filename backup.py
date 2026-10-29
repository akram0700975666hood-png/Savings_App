import os
import subprocess
from datetime import datetime

def run_database_backup():
    """Generates a secure timestamped snapshot backup of the sunday_savings_db framework."""
    # Define paths based on your exact Laragon local server architecture
    mysqldump_path = r"C:\laragon\bin\mysql\mysql-8.4.3-winx64\bin\mysqldump.exe"
    db_name = "sunday_savings_db"
    db_user = "root"
    
    # Generate an explicit timestamped filename parameter
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_filename = f"backup_{db_name}_{timestamp}.sql"
    
    # Construct the structural execution arguments block safely
    dump_command = [
        mysqldump_path,
        f"-u{db_user}",
        db_name
    ]
    
    try:
        print(f"--- STARTING DATABASE SNAPSHOT PIPELINE FOR {db_name.upper()} ---")
        with open(backup_filename, "w", encoding="utf-8") as output_file:
            subprocess.run(dump_command, stdout=output_file, check=True)
        print("==================================================")
        print(" SUCCESS: Database backup compiled safely!")
        print(f" Saved File: {backup_filename}")
        print("==================================================")
    except subprocess.CalledProcessError as err:
        print("==================================================")
        print(" ERROR: Extraction sequence aborted.")
        print(f" Reason: {err}")
        print("==================================================")
    except FileNotFoundError:
        print("❌ ERROR: Command failed. Please double-check your path folder directory.")

if __name__ == "__main__":
    run_database_backup()
