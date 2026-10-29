/* 1. Create a temporary staging table with unique rows collapsed down to unified sums */
CREATE TABLE temp_compressed_archive AS 
SELECT MIN(archive_id) as keep_id, archive_year, member_name, SUM(total_amount_saved) as final_amount
FROM year_end_archive
GROUP BY member_name, archive_year;

/* 2. Clear out the old duplicated table rows records */
DELETE FROM year_end_archive;

/* 3. Re-insert the perfectly calculated math records back into the main log layout */
INSERT INTO year_end_archive (archive_id, archive_year, member_name, total_amount_saved)
SELECT keep_id, archive_year, member_name, final_amount FROM temp_compressed_archive;

/* 4. Drop the temporary cleanup staging table structure */
DROP TABLE temp_compressed_archive;
