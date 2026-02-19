-- Migration: ensure standard teams exist (OPS, DevOPS, Infra) for SQLite
-- Up
INSERT OR IGNORE INTO teams(name) VALUES ('OPS');
INSERT OR IGNORE INTO teams(name) VALUES ('DevOPS');
INSERT OR IGNORE INTO teams(name) VALUES ('Infra');

-- Down: not implemented (removing teams might be destructive)
