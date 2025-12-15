-- Migration: ensure standard teams exist (OPS, DevOPS, Infra)
-- Up
MERGE INTO teams t
USING (
  SELECT 'OPS' as name FROM dual
  UNION ALL SELECT 'DevOPS' FROM dual
  UNION ALL SELECT 'Infra' FROM dual
) s
ON (t.name = s.name)
WHEN NOT MATCHED THEN
  INSERT (name) VALUES (s.name);

-- Down: not implemented (removing teams might be destructive)
