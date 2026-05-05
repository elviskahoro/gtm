import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path("data/progress.db")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            subject TEXT,
            sender TEXT,
            date TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            screenshot_path TEXT,
            error TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def add_emails(conn: sqlite3.Connection, emails: list[dict[str, Any]]) -> None:
    with conn:
        conn.executemany(
            "INSERT OR IGNORE INTO emails (id, url, status) VALUES (?, ?, 'pending')",
            [(e["id"], e["url"]) for e in emails],
        )


def get_pending_emails(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM emails WHERE status = 'pending' ORDER BY rowid",
    ).fetchall()
    return [dict(r) for r in rows]


def get_error_emails(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM emails WHERE status = 'error' ORDER BY rowid",
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_emails(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM emails ORDER BY rowid").fetchall()
    return [dict(r) for r in rows]


def mark_done(
    conn: sqlite3.Connection,
    email_id: str,
    subject: str,
    sender: str,
    date: str,
    screenshot_path: str,
) -> None:
    with conn:
        conn.execute(
            """UPDATE emails SET status='done', subject=?, sender=?, date=?,
               screenshot_path=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (subject, sender, date, screenshot_path, email_id),
        )


def mark_error(conn: sqlite3.Connection, email_id: str, error: str) -> None:
    with conn:
        conn.execute(
            "UPDATE emails SET status='error', error=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (str(error), email_id),
        )


def get_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT status, COUNT(*) as count FROM emails GROUP BY status",
    ).fetchall()
    return {r["status"]: r["count"] for r in rows}


def get_session(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM sessions WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def set_session(conn: sqlite3.Connection, key: str, value: str) -> None:
    with conn:
        conn.execute(
            """INSERT INTO sessions (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET value=?, updated_at=CURRENT_TIMESTAMP""",
            (key, value, value),
        )
