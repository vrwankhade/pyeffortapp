-- Migration: Add is_locked column to members
-- Up
ALTER TABLE members ADD (is_locked NUMBER(1) DEFAULT 0);
UPDATE members SET is_locked = 0 WHERE is_locked IS NULL;
ALTER TABLE members MODIFY (is_locked DEFAULT 0 NOT NULL);

-- Down (rollback)
-- Note: dropping a column will remove data; use with caution
-- ALTER TABLE members DROP COLUMN is_locked;
