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
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name     TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password      TEXT    NOT NULL,
            created       TEXT    NOT NULL,
            mobile_number TEXT,
            dob           TEXT,
            bank_name     TEXT,
            card_number   TEXT,
            fraud_type    TEXT,
            profile_done  INTEGER DEFAULT 0
        )
    """)

    # Migration: add the extra profile columns if this DB was created
    # before they existed (ALTER TABLE, since CREATE TABLE IF NOT EXISTS
    # won't touch an already-existing table).
    c.execute("PRAGMA table_info(users)")
    existing_cols = {row[1] for row in c.fetchall()}
    profile_cols = {
        "mobile_number": "TEXT",
        "dob":           "TEXT",
        "bank_name":     "TEXT",
        "card_number":   "TEXT",
        "fraud_type":    "TEXT",
        "profile_done":  "INTEGER DEFAULT 0",
    }
    for col, col_type in profile_cols.items():
        if col not in existing_cols:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")

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
    Returns (True, "Success", user_id) or (False, "error message", None).
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
        return True, "Account created successfully!", c.lastrowid
    except sqlite3.IntegrityError:
        return False, "This email is already registered.", None
    finally:
        conn.close()


def email_exists(email: str) -> bool:
    """Check whether an email is already registered."""
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE email=?", (email.strip().lower(),))
    row = c.fetchone()
    conn.close()
    return row is not None


def save_profile_details(user_id: int, mobile_number: str, dob: str,
                          bank_name: str, card_number: str, fraud_type: str):
    """Save the post-signup profile details (card, bank, DOB, mobile, fraud type)."""
    conn = _connect()
    c = conn.cursor()
    c.execute(
        "UPDATE users SET mobile_number=?, dob=?, bank_name=?, card_number=?, "
        "fraud_type=?, profile_done=1 WHERE id=?",
        (mobile_number.strip(), dob, bank_name.strip(), card_number.strip(),
         fraud_type, user_id)
    )
    conn.commit()
    conn.close()


def mark_profile_skipped(user_id: int):
    """Mark the profile step as handled even if the user chose to skip it."""
    conn = _connect()
    c = conn.cursor()
    c.execute("UPDATE users SET profile_done=1 WHERE id=?", (user_id,))
    conn.commit()
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