import sqlite3
from datetime import datetime
from config import settings


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS car_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_message_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                received_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS estimates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                car_request_id INTEGER NOT NULL REFERENCES car_requests(id),
                status TEXT NOT NULL,
                low_price REAL,
                high_price REAL,
                currency TEXT,
                reasoning TEXT NOT NULL,
                raw_response TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS negotiations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                estimate_id INTEGER NOT NULL REFERENCES estimates(id),
                opening_message TEXT NOT NULL,
                posted_at TEXT NOT NULL
            );
        """)


def save_car_request(
    telegram_message_id: int,
    chat_id: int,
    user_id: int,
    description: str,
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO car_requests (telegram_message_id, chat_id, user_id, description, received_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (telegram_message_id, chat_id, user_id, description, datetime.utcnow().isoformat()),
        )
        return cursor.lastrowid


def save_estimate(
    car_request_id: int,
    status: str,
    low_price: float | None,
    high_price: float | None,
    currency: str | None,
    reasoning: str,
    raw_response: str,
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO estimates
                (car_request_id, status, low_price, high_price, currency, reasoning, raw_response, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                car_request_id,
                status,
                low_price,
                high_price,
                currency,
                reasoning,
                raw_response,
                datetime.utcnow().isoformat(),
            ),
        )
        return cursor.lastrowid


def save_negotiation(estimate_id: int, opening_message: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO negotiations (estimate_id, opening_message, posted_at)
            VALUES (?, ?, ?)
            """,
            (estimate_id, opening_message, datetime.utcnow().isoformat()),
        )
