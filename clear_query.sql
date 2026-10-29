/* Permanently delete only the older test run rows from 11:42:06 AM */
DELETE FROM year_end_archive WHERE archived_at = '2026-10-29 11:42:06';
