import sqlite3
import os
from datetime import date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cat_tracker.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS weeks (
    week_num INTEGER PRIMARY KEY,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_num INTEGER NOT NULL,
    section TEXT NOT NULL CHECK(section IN ('QA','DILR','VARC')),
    topic_name TEXT NOT NULL,
    target_count INTEGER NOT NULL,
    unit TEXT NOT NULL CHECK(unit IN ('q','set','psg')),
    syllabus_topic_id INTEGER,
    FOREIGN KEY(week_num) REFERENCES weeks(week_num)
);

CREATE TABLE IF NOT EXISTS syllabus_master (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section TEXT NOT NULL CHECK(section IN ('QA','DILR','VARC')),
    topic_name TEXT NOT NULL,
    historical_weight INTEGER NOT NULL DEFAULT 0,
    volatile_flag INTEGER NOT NULL DEFAULT 0,
    total_done INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS daily_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    topic_id INTEGER,
    count_done INTEGER,
    unit TEXT,
    notes TEXT,
    plan_topic_id INTEGER,
    FOREIGN KEY(topic_id) REFERENCES syllabus_master(id),
    FOREIGN KEY(plan_topic_id) REFERENCES plan_topics(id)
);

CREATE TABLE IF NOT EXISTS mocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    series_name TEXT,
    overall_score REAL NOT NULL,
    overall_percentile REAL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS mock_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mock_id INTEGER NOT NULL,
    section TEXT NOT NULL CHECK(section IN ('QA','DILR','VARC')),
    attempts INTEGER,
    correct INTEGER,
    wrong INTEGER,
    score REAL,
    percentile REAL,
    time_taken_min REAL,
    FOREIGN KEY(mock_id) REFERENCES mocks(id)
);

CREATE TABLE IF NOT EXISTS error_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    topic_id INTEGER,
    mock_id_nullable INTEGER,
    section TEXT CHECK(section IN ('QA','DILR','VARC')),
    reason_tag TEXT CHECK(reason_tag IN ('silly error','concept gap','misread','time pressure','guessed wrong')),
    notes TEXT,
    FOREIGN KEY(topic_id) REFERENCES syllabus_master(id),
    FOREIGN KEY(mock_id_nullable) REFERENCES mocks(id)
);

CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    theme TEXT NOT NULL DEFAULT 'graphite',
    persona_frequency TEXT NOT NULL DEFAULT 'once_per_day',
    schedule_adherence_mode TEXT NOT NULL DEFAULT 'flexible',
    last_persona_shown_date TEXT,
    exam_date TEXT NOT NULL DEFAULT '2026-11-29'
);

CREATE TABLE IF NOT EXISTS streak_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    current_streak INTEGER NOT NULL DEFAULT 0,
    last_log_date TEXT
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    _ensure_schedule_link_column(conn)
    conn.commit()

    # Seed new databases, or replace only the schedule when its source data changes.
    already_seeded = conn.execute("SELECT COUNT(*) c FROM weeks").fetchone()["c"] > 0
    if not already_seeded:
        _seed(conn)
    elif not _schedule_matches(conn):
        _replace_schedule(conn)

    if conn.execute("SELECT COUNT(*) c FROM settings").fetchone()["c"] == 0:
        conn.execute("INSERT INTO settings (id) VALUES (1)")
    if conn.execute("SELECT COUNT(*) c FROM streak_state").fetchone()["c"] == 0:
        conn.execute("INSERT INTO streak_state (id, current_streak, last_log_date) VALUES (1, 0, NULL)")
    conn.commit()
    conn.close()


def _schedule_matches(conn):
    import seed_data as sd

    weeks = [tuple(row) for row in conn.execute(
        "SELECT week_num, start_date, end_date FROM weeks ORDER BY week_num"
    ).fetchall()]
    topics = [tuple(row) for row in conn.execute(
        "SELECT week_num, section, topic_name, target_count, unit FROM plan_topics ORDER BY week_num, id"
    ).fetchall()]
    return weeks == sd.WEEKS and topics == sd.PLAN_TOPICS


def _replace_schedule(conn):
    import seed_data as sd

    # Preserve practice history while clearing links to obsolete plan rows.
    conn.execute("UPDATE daily_logs SET plan_topic_id = NULL")
    conn.execute("DELETE FROM plan_topics")
    conn.execute("DELETE FROM weeks")
    conn.executemany(
        "INSERT INTO weeks (week_num, start_date, end_date) VALUES (?, ?, ?)",
        sd.WEEKS,
    )
    conn.executemany(
        "INSERT INTO plan_topics (week_num, section, topic_name, target_count, unit) VALUES (?, ?, ?, ?, ?)",
        sd.PLAN_TOPICS,
    )
    _link_plan_topics(conn)
    conn.commit()


def _seed(conn):
    import seed_data as sd

    conn.executemany(
        "INSERT INTO weeks (week_num, start_date, end_date) VALUES (?, ?, ?)",
        sd.WEEKS,
    )
    conn.executemany(
        "INSERT INTO plan_topics (week_num, section, topic_name, target_count, unit) VALUES (?, ?, ?, ?, ?)",
        sd.PLAN_TOPICS,
    )
    conn.executemany(
        "INSERT INTO syllabus_master (section, topic_name, historical_weight, volatile_flag) VALUES (?, ?, ?, ?)",
        [(s, t, w, 1 if v else 0) for (s, t, w, v) in sd.SYLLABUS_MASTER],
    )
    _link_plan_topics(conn)
    conn.commit()


def _ensure_schedule_link_column(conn):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(plan_topics)").fetchall()}
    if "syllabus_topic_id" not in columns:
        conn.execute("ALTER TABLE plan_topics ADD COLUMN syllabus_topic_id INTEGER")
        _link_plan_topics(conn)


def _link_plan_topics(conn):
    aliases = {
        "Percentages": "Percentage",
        "Mixtures & Alligations": "Mixture & Alligation",
        "Ratio, Proportion & Variation": "Arithmetics (Ratio & Proportion)",
        "Progressions": "Progressions & Series",
        "Interest": "Simple Interest, Compound Interest",
        "Linear & Quadratic Equations": "Equations & Polynomials",
        "Logarithms": "Logarithms & Exponents",
        "Functions": "Functions & Graphs",
        "Permutations & Combinations": "Permutation, Combination & Probability",
        "Pipes, Trains & Boats": "Pipes & Cisterns / Clocks",
        "Clocks": "Pipes & Cisterns / Clocks",
        "Seating Arrangements": "Sitting / Standing Arrangement",
        "Bar Graphs": "Line & Bar Charts",
        "Column Graphs": "Line & Bar Charts",
        "Line Charts": "Line & Bar Charts",
        "Tables": "Data Tabulation",
    }
    topics = conn.execute("SELECT id, section, topic_name FROM plan_topics").fetchall()
    for topic in topics:
        syllabus_name = aliases.get(topic["topic_name"], topic["topic_name"])
        match = conn.execute(
            "SELECT id FROM syllabus_master WHERE section=? AND topic_name=?",
            (topic["section"], syllabus_name),
        ).fetchone()
        conn.execute(
            "UPDATE plan_topics SET syllabus_topic_id=? WHERE id=?",
            (match["id"] if match else None, topic["id"]),
        )
