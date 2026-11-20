"""
db.py – SQLite helpers: connection factory and schema initialisation.
All dates are stored as ISO-8601 strings (YYYY-MM-DD).
"""
import sqlite3
from config import DB_PATH


def get_conn(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Return a connection with Row factory so columns are accessible by name."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Create all tables if they don't exist."""
    conn = get_conn(db_path)
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS books (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        title           TEXT NOT NULL,
        author          TEXT NOT NULL,
        subject         TEXT NOT NULL,
        isbn            TEXT,
        description     TEXT,
        published_year  INTEGER,
        language        TEXT DEFAULT 'English',
        total_copies    INTEGER DEFAULT 1,
        available_copies INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS members (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        email       TEXT UNIQUE NOT NULL,
        department  TEXT NOT NULL,
        year        INTEGER,
        joined_on   TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS loans (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id       INTEGER NOT NULL REFERENCES members(id),
        book_id         INTEGER NOT NULL REFERENCES books(id),
        issued_on       TEXT NOT NULL,
        due_on          TEXT NOT NULL,
        returned_on     TEXT,
        renewed_count   INTEGER DEFAULT 0,
        fine_amount     REAL DEFAULT 0,
        fine_paid       INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS reservations (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id   INTEGER NOT NULL REFERENCES members(id),
        book_id     INTEGER NOT NULL REFERENCES books(id),
        reserved_on TEXT NOT NULL,
        status      TEXT DEFAULT 'active'   -- active / fulfilled / cancelled
    );

    CREATE TABLE IF NOT EXISTS chat_logs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id   INTEGER REFERENCES members(id),
        role        TEXT NOT NULL,
        content     TEXT NOT NULL,
        created_at  TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()
