"""
SQLite persistence — signal history + outcome tracking (WAL mode for
safe concurrent access on Railway volumes).
"""
import sqlite3
import os
from datetime import datetime, timezone
import config


def get_connection():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry REAL NOT NULL,
            stop_loss REAL NOT NULL,
            tp1 REAL, tp2 REAL, tp3 REAL,
            leverage INTEGER,
            confidence INTEGER,
            session TEXT,
            reasons TEXT,
            outcome TEXT DEFAULT 'open'
        )
    """)
    conn.commit()
    conn.close()


def save_signal(signal) -> int:
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO signals
        (created_at, direction, entry, stop_loss, tp1, tp2, tp3, leverage, confidence, session, reasons)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        signal.direction, signal.entry, signal.stop_loss,
        signal.take_profits[0], signal.take_profits[1], signal.take_profits[2],
        signal.leverage, signal.confidence, signal.session,
        "; ".join(signal.reasons),
    ))
    conn.commit()
    signal_id = cur.lastrowid
    conn.close()
    return signal_id


def last_signal_time():
    conn = get_connection()
    row = conn.execute("SELECT created_at FROM signals ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return row["created_at"] if row else None


def signals_today_count() -> int:
    conn = get_connection()
    today = datetime.now(timezone.utc).date().isoformat()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM signals WHERE created_at LIKE ?", (f"{today}%",)
    ).fetchone()
    conn.close()
    return row["c"]


def update_outcome(signal_id: int, outcome: str):
    conn = get_connection()
    conn.execute("UPDATE signals SET outcome = ? WHERE id = ?", (outcome, signal_id))
    conn.commit()
    conn.close()


def get_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) c FROM signals").fetchone()["c"]
    wins = conn.execute("SELECT COUNT(*) c FROM signals WHERE outcome = 'win'").fetchone()["c"]
    losses = conn.execute("SELECT COUNT(*) c FROM signals WHERE outcome = 'loss'").fetchone()["c"]
    open_ = conn.execute("SELECT COUNT(*) c FROM signals WHERE outcome = 'open'").fetchone()["c"]
    conn.close()
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    return {
        "total": total, "wins": wins, "losses": losses,
        "open": open_, "win_rate": round(win_rate, 1),
    }
