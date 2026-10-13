PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- User and persona settings: persona_name, user_name,
-- camera_monitoring, mic_monitoring, proactive_enabled
CREATE TABLE IF NOT EXISTS settings (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Structured knowledge graph as entity-relation triples
CREATE TABLE IF NOT EXISTS facts (
  id         INTEGER PRIMARY KEY,
  subject    TEXT NOT NULL,
  relation   TEXT NOT NULL,
  object     TEXT NOT NULL,
  source     TEXT NOT NULL DEFAULT 'user_stated',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (subject, relation, object)
);

-- Recurring routines (days stored as JSON, e.g. ["Mon","Wed"])
CREATE TABLE IF NOT EXISTS routines (
  id         INTEGER PRIMARY KEY,
  activity   TEXT NOT NULL,
  start_time TEXT,
  end_time   TEXT,
  days       TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS reminders (
  id         INTEGER PRIMARY KEY,
  text       TEXT NOT NULL,
  due_at     TEXT NOT NULL,              -- ISO 8601, UTC
  urgency    TEXT NOT NULL DEFAULT 'normal',
  status     TEXT NOT NULL DEFAULT 'pending'
             CHECK (status IN ('pending','fired','done','cancelled')),
  created_by TEXT NOT NULL DEFAULT 'user',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders (status, due_at);

-- Conversation history. Interrupted replies keep the cut-off point.
CREATE TABLE IF NOT EXISTS messages (
  id                 INTEGER PRIMARY KEY,
  session_id         TEXT NOT NULL,
  role               TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
  content            TEXT NOT NULL,
  modality           TEXT NOT NULL DEFAULT 'text' CHECK (modality IN ('voice','text')),
  interrupted        INTEGER NOT NULL DEFAULT 0,
  interrupted_at_char INTEGER,
  created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages (session_id, id);

-- Derived scores only. No images, no audio.
CREATE TABLE IF NOT EXISTS affect_log (
  id         INTEGER PRIMARY KEY,
  ts         TEXT NOT NULL,
  sadness    REAL, anxiety REAL, valence REAL,
  s_distress REAL,
  source     TEXT NOT NULL DEFAULT 'edge'
);
CREATE INDEX IF NOT EXISTS idx_affect_ts ON affect_log (ts);