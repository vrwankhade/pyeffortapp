-- Migration: Add is_locked column to members (SQLite version)
-- Up
ALTER TABLE members ADD COLUMN is_locked INTEGER DEFAULT 0 NOT NULL;
-- SQLite adds the column with the default; existing rows will have 0.
-- No further modification needed.

-- Down (rollback)
-- SQLite does not support DROP COLUMN directly; you would need to
-- rebuild the table without it if you truly want to remove it.

