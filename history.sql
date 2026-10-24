/* 2026-10-19 15:19:46 [56 ms] */ 
CREATE DATABASE sunday_savings_db
    DEFAULT CHARACTER SET = 'utf8mb4';
/* 2026-10-19 15:21:11 [79 ms] */ 
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('super_admin', 'admin', 'member') NOT NULL,
    account_status ENUM('pending', 'active', 'suspended') DEFAULT 'pending',
    terms_accepted BOOLEAN DEFAULT FALSE,
    terms_accepted_at DATETIME DEFAULT NULL,
    ip_address_at_signoff VARCHAR(45) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
/* 2026-10-19 20:06:59 [221 ms] */ 
ALTER TABLE users ADD COLUMN is_online BOOLEAN DEFAULT FALSE;
/* 2026-10-19 22:29:11 [17 ms] */ 
SELECT username, is_online, account_status FROM users WHERE username = 'superadmin' LIMIT 100;
/* 2026-10-19 22:33:38 [5 ms] */ 
SELECT username, is_online FROM users WHERE username = 'superadmin' LIMIT 100;
/* 2026-10-19 22:36:19 [27 ms] */ 
DESCRIBE deposits;
/* 2026-10-19 22:39:50 [29 ms] */ 
SELECT * FROM deposits WHERE member_id = 2 ORDER BY deposit_date DESC LIMIT 1;
/* 2026-10-20 15:42:23 [18 ms] */ 
USE sunday_savings_db;
/* 2026-10-20 15:42:23 [37 ms] */ 
DESCRIBE complaints;
/* 2026-10-21 10:29:55 [29 ms] */ 
USE sunday_savings_db;
/* 2026-10-21 10:29:55 [59 ms] */ 
DESCRIBE year_end_archive;
/* 2026-10-21 13:48:16 [16 ms] */ 
SELECT user_id, username, role FROM users LIMIT 100;
/* 2026-10-21 13:50:58 [9 ms] */ 
SELECT * FROM users WHERE user_id = 5 LIMIT 100;
/* 2026-10-21 13:50:58 [8 ms] */ 
SELECT * FROM deposits WHERE member_id = 5 LIMIT 100;
/* 2026-10-21 13:50:58 [4 ms] */ 
SELECT * FROM complaints WHERE member_id = 5 LIMIT 100;
/* 2026-10-21 13:51:05 [5 ms] */ 
SELECT user_id, username, role FROM users LIMIT 100;
/* 2026-10-21 13:51:10 [5 ms] */ 
SELECT * FROM users WHERE user_id = 5 LIMIT 100;
/* 2026-10-21 13:51:14 [4 ms] */ 
SELECT * FROM deposits WHERE member_id = 5 LIMIT 100;
/* 2026-10-21 13:51:14 [2 ms] */ 
SELECT * FROM complaints WHERE member_id = 5 LIMIT 100;
/* 2026-10-21 14:13:26 [213 ms] */ 
ALTER TABLE users ADD COLUMN contact_info VARCHAR(100) DEFAULT 'No Contact';
/* 2026-10-21 14:32:58 [148 ms] */ 
ALTER TABLE users ADD COLUMN next_of_kin_info VARCHAR(150) DEFAULT NULL;
/* 2026-10-21 14:32:58 [41 ms] */ 
ALTER TABLE deposits ADD COLUMN target_sunday_date DATE DEFAULT NULL;
/* 2026-10-21 17:38:16 [14 ms] */ 
USE sunday_savings_db;
/* 2026-10-21 17:38:16 [10 ms] */ 
DESCRIBE year_end_archive;
/* 2026-10-21 17:38:16 [4 ms] */ 
DESCRIBE users;
/* 2026-10-21 18:37:38 [121 ms] */ 
CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    alert_message VARCHAR(500) NOT NULL,
    is_read TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES users(user_id) ON DELETE CASCADE
);
/* 2026-10-22 14:22:05 [41 ms] */ 
SELECT * FROM deposits WHERE member_id = 10 LIMIT 100;
/* 2026-10-22 18:03:15 [61 ms] */ 
SELECT user_id, username, role, account_status FROM users LIMIT 100;
