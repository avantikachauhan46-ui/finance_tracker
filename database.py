"""
database.py — SQLite persistence layer for Finance Tracker
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / ".finance_tracker" / "finance.db"


def get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database, creating it if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all required tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS categories (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT    NOT NULL UNIQUE,
                type    TEXT    NOT NULL CHECK(type IN ('income','expense')),
                budget  REAL    DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT    NOT NULL,
                amount      REAL    NOT NULL CHECK(amount > 0),
                type        TEXT    NOT NULL CHECK(type IN ('income','expense')),
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
                description TEXT    DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );
        """)

        # Seed default categories
        defaults = [
            ("Salary",       "income",  0),
            ("Freelance",    "income",  0),
            ("Investment",   "income",  0),
            ("Other Income", "income",  0),
            ("Housing",      "expense", 0),
            ("Food",         "expense", 0),
            ("Transport",    "expense", 0),
            ("Healthcare",   "expense", 0),
            ("Entertainment","expense", 0),
            ("Shopping",     "expense", 0),
            ("Utilities",    "expense", 0),
            ("Education",    "expense", 0),
            ("Other",        "expense", 0),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO categories (name, type, budget) VALUES (?,?,?)",
            defaults
        )
