-- Migration: assign all members to OPS team (SQLite version)
-- Up
UPDATE members
SET team_id = (
    SELECT id FROM teams WHERE name = 'OPS' LIMIT 1
)
WHERE EXISTS (SELECT 1 FROM teams WHERE name = 'OPS');

-- Down: no-op (reverting requires knowing previous assignments)
