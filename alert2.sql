ALTER TABLE deposits ADD UNIQUE KEY unique_member_sunday (member_id, target_sunday_date);
ALTER TABLE deposits AUTO_INCREMENT = 1;
