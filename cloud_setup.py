import mysql.connector

def initialize_cloud_tables():
    """Connects to the Aiven instance and builds the exact schema matching your local system backup."""
    try:
        print("--- CONNECTING TO AIVEN MYSQL CLOUD SERVER ---")
        # Hooking directly onto your live connection information parameters
        conn = mysql.connector.connect(
            host="mysql-2e810251-akram0700975666hood-8344.d.aivencloud.com",
            port=10794,
            user="avnadmin",
            password="AVNS_ILLb5-a6gzwHhGIOU0w", # <-- Paste your revealed dashboard password string here
            database="defaultdb"
        )
        cursor = conn.cursor()
        print(" Connected successfully! Initializing production table builds...")

        # 1. Build users profile base directory table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS `users` (
          `user_id` int NOT NULL AUTO_INCREMENT,
          `full_name` varchar(100) NOT NULL,
          `username` varchar(50) NOT NULL,
          `password_hash` varchar(255) NOT NULL,
          `role` enum('super_admin','admin','member') NOT NULL,
          `account_status` enum('pending','active','suspended') DEFAULT 'pending',
          `terms_accepted` tinyint(1) DEFAULT '0',
          `terms_accepted_at` datetime DEFAULT NULL,
          `ip_address_at_signoff` varchar(45) DEFAULT NULL,
          `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
          `is_online` tinyint(1) DEFAULT '0',
          `contact_info` varchar(100) DEFAULT 'No Contact',
          `next_of_kin_info` varchar(150) DEFAULT NULL,
          `agreed_at` datetime DEFAULT NULL,
          PRIMARY KEY (`user_id`),
          UNIQUE KEY `username` (`username`),
          KEY `user_id` (`user_id`),
          KEY `user_id_2` (`user_id`),
          KEY `user_id_3` (`user_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 2. Build savings deposits tracking ledger rows table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS `deposits` (
          `deposit_id` int NOT NULL AUTO_INCREMENT,
          `member_id` int DEFAULT NULL,
          `amount` decimal(10,2) NOT NULL,
          `deposit_date` datetime NOT NULL,
          `recorded_by` int DEFAULT NULL,
          `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
          `target_sunday_date` date DEFAULT NULL,
          PRIMARY KEY (`deposit_id`),
          UNIQUE KEY `unique_member_sunday` (`member_id`,`target_sunday_date`),
          KEY `recorded_by` (`recorded_by`),
          CONSTRAINT `deposits_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `users` (`user_id`),
          CONSTRAINT `deposits_ibfk_2` FOREIGN KEY (`recorded_by`) REFERENCES `users` (`user_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 3. Build text complaints portal index table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS `complaints` (
          `complaint_id` int NOT NULL AUTO_INCREMENT,
          `member_id` int DEFAULT NULL,
          `message` text NOT NULL,
          `is_resolved` tinyint(1) DEFAULT '0',
          `submitted_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (`complaint_id`),
          KEY `member_id` (`member_id`),
          CONSTRAINT `complaints_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `users` (`user_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 4. Build in-app direct notification dashboard table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS `notifications` (
          `notification_id` int NOT NULL AUTO_INCREMENT,
          `member_id` int NOT NULL,
          `alert_message` varchar(500) NOT NULL,
          `is_read` tinyint(1) DEFAULT '0',
          `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (`notification_id`),
          KEY `member_id` (`member_id`),
          CONSTRAINT `notifications_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 5. Build compressed year-end annual logs history table sheets
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS `year_end_archive` (
          `archive_id` int NOT NULL AUTO_INCREMENT,
          `archive_year` int NOT NULL,
          `member_name` varchar(100) NOT NULL,
          `total_amount_saved` decimal(10,2) NOT NULL,
          `archived_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (`archive_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # 6. Seed administrative profiles cleanly into production (Preserving your exact backup password hashes)
        print(" Seeding active administrator credential rows...")
        
        # Insert administrative profile for AKRAM HOOD
        cursor.execute("SELECT * FROM users WHERE username = 'akram'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO users (user_id, full_name, username, password_hash, role, account_status, contact_info) 
                VALUES (1, 'AKRAM HOOD', 'akram', '73a2af8864fc500fa49048bf3003776c19938f360e56bd03663866fb3087884a', 'admin', 'active', 'No Contact')
            """)

        # Insert administrative profile for KATO
        cursor.execute("SELECT * FROM users WHERE username = 'kato'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO users (user_id, full_name, username, password_hash, role, account_status, contact_info) 
                VALUES (17, 'KATO', 'kato', 'd17f25ecfbcc7857f7bebea469308be0b2580943e96d13a3ad98a13675c4bfc2', 'admin', 'active', '0980')
            """)

        conn.commit()
        print("==================================================")
        print(" 🎉 SUCCESS: Cloud Database Infrastructure Complete!")
        print(" Your Aiven MySQL tables precisely match your local setup.")
        print("==================================================")

    except Exception as e:
        print(f"❌ Structural setup failed: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    initialize_cloud_tables()
