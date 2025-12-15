-- Migration: assign all members to OPS team
-- Up
MERGE INTO members m
USING (SELECT id FROM teams WHERE name = 'OPS') t
ON (1=1)
WHEN MATCHED THEN
  UPDATE SET m.team_id = t.id
WHERE t.id IS NOT NULL;

-- Down: no-op (reverting requires knowing previous assignments)
