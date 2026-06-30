"""
database.py
Handles all SQLite database operations:
  - User registration & login
  - Transaction history logging
"""

import struct
import sqlite3
import hashlib
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "fraudguard.db")


def _connect():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    """Create tables if they do not exist."""
    conn = _connect()
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT    NOT NULL,
            email     TEXT    UNIQUE NOT NULL,
            password  TEXT    NOT NULL,
            created   TEXT    NOT NULL
        )
    """)

    # Transaction history table
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            amount      REAL    NOT NULL,
            result      TEXT    NOT NULL,
            confidence  REAL    NOT NULL,
            checked_at  TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(full_name: str, email: str, password: str):
    """
    Returns (True, "Success") or (False, "error message").
    """
    conn = _connect()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users (full_name, email, password, created) VALUES (?,?,?,?)",
            (full_name.strip(), email.strip().lower(), _hash(password),
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "This email is already registered."
    finally:
        conn.close()


def login_user(email: str, password: str):
    """
    Returns user dict on success, None on failure.
    """
    conn = _connect()
    c = conn.cursor()
    c.execute(
        "SELECT id, full_name, email FROM users WHERE email=? AND password=?",
        (email.strip().lower(), _hash(password))
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "full_name": row[1], "email": row[2]}
    return None


def log_transaction(user_id: int, amount: float, result: str, confidence: float):
    """Save a fraud-check result to history."""
    conn = _connect()
    c = conn.cursor()
    c.execute(
        "INSERT INTO transactions (user_id, amount, result, confidence, checked_at) VALUES (?,?,?,?,?)",
        (user_id, amount, result, confidence,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def get_user_transactions(user_id: int, limit: int = 10):
    """Return latest transactions for a user."""
    conn = _connect()
    c = conn.cursor()
    c.execute(
        "SELECT amount, result, confidence, checked_at FROM transactions "
        "WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )
    rows = c.fetchall()
    conn.close()
    return [
        {"amount": r[0], "result": r[1], "confidence": struct.unpack("f", r[2])[0] if isinstance(r[2], bytes) else float(r[2] or 0), "checked_at": r[3]}
        for r in rows
    ]


def get_user_stats(user_id: int):
    """Return total, fraud count, legit count for a user."""
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM transactions WHERE user_id=?", (user_id,))
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM transactions WHERE user_id=? AND result='FRAUD'", (user_id,))
    fraud = c.fetchone()[0]
    conn.close()
    return {"total": total, "fraud": fraud, "legit": total - fraud}