/* 1. Create a temporary staging table with unique rows collapsed down */
CREATE TABLE temp_deposits AS 
SELECT MAX(deposit_id) as keep_id, member_id, target_sunday_date, MAX(amount) as final_amount
FROM deposits
GROUP BY member_id, target_sunday_date;

/* 2. Clear out the old duplicated table rows balance records */
DELETE FROM deposits 
WHERE deposit_id NOT IN (SELECT keep_id FROM temp_deposits);

/* 3. Drop the temporary cleanup staging table structure */
DROP TABLE temp_deposits;
