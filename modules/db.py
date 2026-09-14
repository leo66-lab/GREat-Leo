from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import BACKUP_DIR, DATA_DIR, DB_PATH, EXPORT_DIR


SCHEMA_VERSION = 6


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL COLLATE NOCASE UNIQUE,
    lemma TEXT,
    pronunciation TEXT,
    general_notes TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS word_senses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_id INTEGER NOT NULL,
    sense_label TEXT,
    part_of_speech TEXT NOT NULL DEFAULT 'Pending',
    core_meaning_cn TEXT NOT NULL DEFAULT 'Pending',
    core_meaning_en TEXT NOT NULL DEFAULT 'Pending',
    usage_notes TEXT NOT NULL DEFAULT '',
    nuance TEXT NOT NULL DEFAULT '',
    common_collocations TEXT NOT NULL DEFAULT '',
    usage_register TEXT NOT NULL DEFAULT '',
    word_root TEXT NOT NULL DEFAULT '',
    root_key TEXT NOT NULL DEFAULT '',
    synonym_key TEXT NOT NULL DEFAULT '',
    example_sentence TEXT NOT NULL DEFAULT '',
    antonyms TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    familiarity INTEGER NOT NULL DEFAULT 0 CHECK (familiarity BETWEEN 0 AND 4),
    wrong_count INTEGER NOT NULL DEFAULT 0,
    review_status TEXT NOT NULL DEFAULT 'learning',
    next_review_date TEXT NOT NULL DEFAULT (DATE('now')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS semantic_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER,
    level INTEGER NOT NULL CHECK (level IN (1, 2)),
    name_cn TEXT NOT NULL,
    name_en TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES semantic_categories(id) ON DELETE CASCADE,
    UNIQUE(parent_id, level, name_cn, name_en)
);

CREATE TABLE IF NOT EXISTS synonym_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_name_cn TEXT NOT NULL,
    group_name_en TEXT NOT NULL DEFAULT '',
    level1_id INTEGER,
    level2_id INTEGER,
    group_definition TEXT NOT NULL DEFAULT '',
    semantic_axis TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    axis_enabled INTEGER NOT NULL DEFAULT 0 CHECK (axis_enabled IN (0, 1)),
    axis_name TEXT NOT NULL DEFAULT '',
    low_label TEXT NOT NULL DEFAULT '',
    high_label TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (level1_id) REFERENCES semantic_categories(id) ON DELETE SET NULL,
    FOREIGN KEY (level2_id) REFERENCES semantic_categories(id) ON DELETE SET NULL,
    UNIQUE(group_name_cn, group_name_en, level1_id, level2_id)
);

CREATE TABLE IF NOT EXISTS synonym_memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sense_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    typicality TEXT NOT NULL DEFAULT '',
    strength_level TEXT NOT NULL DEFAULT '',
    axis_position INTEGER,
    display_order INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sense_id) REFERENCES word_senses(id) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES synonym_groups(id) ON DELETE CASCADE,
    UNIQUE(sense_id, group_id)
);

CREATE TABLE IF NOT EXISTS gre_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_type TEXT NOT NULL DEFAULT 'Other',
    source TEXT NOT NULL DEFAULT '',
    question_text TEXT NOT NULL,
    correct_answer TEXT NOT NULL DEFAULT '',
    explanation TEXT NOT NULL DEFAULT '',
    logic_structure TEXT NOT NULL DEFAULT '',
    date_added TEXT NOT NULL DEFAULT (DATE('now')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS question_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    option_text TEXT NOT NULL,
    is_correct INTEGER NOT NULL DEFAULT 0 CHECK (is_correct IN (0, 1)),
    explanation TEXT NOT NULL DEFAULT '',
    relation_note TEXT NOT NULL DEFAULT '',
    linked_sense_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES gre_questions(id) ON DELETE CASCADE,
    FOREIGN KEY (linked_sense_id) REFERENCES word_senses(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS word_question_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sense_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT '',
    context_sentence TEXT NOT NULL DEFAULT '',
    personal_note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sense_id) REFERENCES word_senses(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES gre_questions(id) ON DELETE CASCADE,
    UNIQUE(sense_id, question_id, role, context_sentence)
);

CREATE TABLE IF NOT EXISTS review_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sense_id INTEGER NOT NULL,
    reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    mode TEXT NOT NULL,
    rating TEXT NOT NULL,
    familiarity_before INTEGER NOT NULL,
    familiarity_after INTEGER NOT NULL,
    next_review_before TEXT NOT NULL DEFAULT '',
    next_review_after TEXT NOT NULL DEFAULT '',
    wrong_delta INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (sense_id) REFERENCES word_senses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS review_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT '',
    total_days INTEGER NOT NULL,
    seed INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS review_plan_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL,
    day_number INTEGER NOT NULL,
    sense_id INTEGER NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES review_plans(id) ON DELETE CASCADE,
    FOREIGN KEY (sense_id) REFERENCES word_senses(id) ON DELETE CASCADE,
    UNIQUE(plan_id, sense_id)
);

CREATE TABLE IF NOT EXISTS import_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    rows_seen INTEGER NOT NULL DEFAULT 0,
    rows_created INTEGER NOT NULL DEFAULT 0,
    rows_skipped INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_word_senses_word_id ON word_senses(word_id);
CREATE INDEX IF NOT EXISTS idx_word_senses_review ON word_senses(next_review_date, review_status);
CREATE INDEX IF NOT EXISTS idx_words_word_nocase ON words(word COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_word_senses_synonym_key ON word_senses(synonym_key);
CREATE INDEX IF NOT EXISTS idx_word_senses_root_key ON word_senses(root_key);
CREATE INDEX IF NOT EXISTS idx_word_senses_word_root ON word_senses(word_root);
CREATE INDEX IF NOT EXISTS idx_word_senses_meaning_cn ON word_senses(core_meaning_cn);
CREATE INDEX IF NOT EXISTS idx_word_senses_created_at ON word_senses(created_at);
CREATE INDEX IF NOT EXISTS idx_review_plans_status ON review_plans(status, id);
CREATE INDEX IF NOT EXISTS idx_review_plan_items_plan_day ON review_plan_items(plan_id, day_number, display_order);
CREATE INDEX IF NOT EXISTS idx_review_plan_items_sense ON review_plan_items(sense_id);
CREATE INDEX IF NOT EXISTS idx_semantic_categories_parent ON semantic_categories(parent_id, level);
CREATE INDEX IF NOT EXISTS idx_synonym_groups_categories ON synonym_groups(level1_id, level2_id);
CREATE INDEX IF NOT EXISTS idx_synonym_memberships_sense ON synonym_memberships(sense_id);
CREATE INDEX IF NOT EXISTS idx_synonym_memberships_group ON synonym_memberships(group_id, display_order);
CREATE INDEX IF NOT EXISTS idx_word_question_sense ON word_question_relations(sense_id);
CREATE INDEX IF NOT EXISTS idx_word_question_question ON word_question_relations(question_id);
CREATE INDEX IF NOT EXISTS idx_review_history_sense ON review_history(sense_id, reviewed_at);

CREATE TRIGGER IF NOT EXISTS trg_words_updated
AFTER UPDATE ON words
BEGIN
    UPDATE words SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_word_senses_updated
AFTER UPDATE ON word_senses
BEGIN
    UPDATE word_senses SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_semantic_categories_updated
AFTER UPDATE ON semantic_categories
BEGIN
    UPDATE semantic_categories SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_synonym_groups_updated
AFTER UPDATE ON synonym_groups
BEGIN
    UPDATE synonym_groups SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_synonym_memberships_updated
AFTER UPDATE ON synonym_memberships
BEGIN
    UPDATE synonym_memberships SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_gre_questions_updated
AFTER UPDATE ON gre_questions
BEGIN
    UPDATE gre_questions SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_question_options_updated
AFTER UPDATE ON question_options
BEGIN
    UPDATE question_options SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_word_question_relations_updated
AFTER UPDATE ON word_question_relations
BEGIN
    UPDATE word_question_relations SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
"""


def ensure_directories() -> None:
    for path in (DATA_DIR, EXPORT_DIR, BACKUP_DIR):
        path.mkdir(parents=True, exist_ok=True)


def get_connection(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def initialize_database(db_path: Path | str = DB_PATH) -> None:
    ensure_directories()
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(word_senses)").fetchall()}
        if "word_root" not in columns:
            conn.execute("ALTER TABLE word_senses ADD COLUMN word_root TEXT NOT NULL DEFAULT ''")
        if "root_key" not in columns:
            conn.execute("ALTER TABLE word_senses ADD COLUMN root_key TEXT NOT NULL DEFAULT ''")
        if "synonym_key" not in columns:
            conn.execute("ALTER TABLE word_senses ADD COLUMN synonym_key TEXT NOT NULL DEFAULT ''")
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)",
            (SCHEMA_VERSION,),
        )
        conn.commit()


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}
