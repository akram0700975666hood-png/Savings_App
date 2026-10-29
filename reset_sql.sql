/* 1. Clear out all tracking logs,help tickets, and historical blocks entirely */
TRUNCATE TABLE deposits;
TRUNCATE TABLE complaints;
TRUNCATE TABLE notifications;
TRUNCATE TABLE year_end_archive;

/* 2. Safely clear all test member profiles from the system base framework */
DELETE FROM users WHERE LOWER(role) = 'member';

/* 3. Force remaining active administrator sessions back offline to a fresh standby state */
UPDATE users SET is_online = 0, terms_accepted = 0, agreed_at = NULL;

/* 4. Reset auto-increment sequence counters to keep future production sequence logs orderly */
ALTER TABLE users AUTO_INCREMENT = 1;
