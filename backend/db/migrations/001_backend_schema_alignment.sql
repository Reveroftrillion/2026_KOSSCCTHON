-- MySQL: original schema.sql -> aligned schema. Inspect SHOW COLUMNS first.
-- Run only the ADD COLUMN statements for columns that do not already exist.
-- DDL may auto-commit; back up the database before applying.
ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NULL;
ALTER TABLE users ADD COLUMN bio TEXT;
ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE trips ADD COLUMN description TEXT;

-- Accounts without an existing password must reset it. This marker is NOT a hash
-- and cannot be used as a shared password. Do not overwrite existing hashes.
UPDATE users SET password_hash = '!reset-required' WHERE password_hash IS NULL;
ALTER TABLE users MODIFY COLUMN password_hash VARCHAR(255) NOT NULL;

-- ONLY if trips has user_id and DOES NOT have owner_user_id (MySQL 8+):
-- ALTER TABLE trips RENAME COLUMN user_id TO owner_user_id;
-- Never rename trip_members.user_id. If both owner columns exist, reconcile
-- their data and foreign keys manually before removing either column.
