import datetime
import os

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

# Load environment variables from .env
load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "ai_selfbot")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "")


def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        cursor_factory=RealDictCursor,
    )


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS channels (
                    id BIGINT PRIMARY KEY
                );
            """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ignored_users (
                    id BIGINT PRIMARY KEY
                );
            """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS message_history (
                    id SERIAL PRIMARY KEY,
                    channel_id BIGINT,
                    user_id BIGINT,
                    message TEXT,
                    replied_me BOOLEAN,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    tagged_me BOOLEAN,
                    is_owner BOOLEAN
                );
            """
            )
        conn.commit()


def add_channel(channel_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO channels (id) VALUES (%s) ON CONFLICT DO NOTHING",
                (channel_id,),
            )
        conn.commit()


def remove_channel(channel_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM channels WHERE id = %s", (channel_id,))
        conn.commit()


def get_channels():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM channels")
            rows = cur.fetchall()
            return [row["id"] for row in rows]


def add_ignored_user(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ignored_users (id) VALUES (%s) ON CONFLICT DO NOTHING",
                (user_id,),
            )
        conn.commit()


def remove_ignored_user(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ignored_users WHERE id = %s", (user_id,))
        conn.commit()


def get_ignored_users():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM ignored_users")
            rows = cur.fetchall()
            return [row["id"] for row in rows]


def add_message_history(
    channel_id,
    channel_name,
    user_id,
    user_name,
    message,
    replied_user,
    tagged_me,
    is_owner,
    timestamp=None,
):
    if timestamp is None:
        timestamp = datetime.datetime.now(datetime.timezone.utc)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO message_history (
                    channel_id, channel_name, user_id, user_name, message,
                    replied_user, timestamp, tagged_me, is_owner
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    channel_id,
                    channel_name,
                    user_id,
                    user_name,
                    message,
                    replied_user,
                    timestamp,
                    tagged_me,
                    is_owner,
                ),
            )
        conn.commit()


def get_message_history(channel_id=None, user_id=None, limit=50):
    query = "SELECT * FROM message_history"
    params = []
    conditions = []
    if channel_id is not None:
        conditions.append("channel_id = %s")
        params.append(channel_id)
    if user_id is not None:
        conditions.append("user_id = %s")
        params.append(user_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY timestamp DESC LIMIT %s"
    params.append(limit)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            return cur.fetchall()
