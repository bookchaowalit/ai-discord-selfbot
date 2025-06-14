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
    try:
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            cursor_factory=RealDictCursor,
        )
    except Exception as e:
        print(f"[DB ERROR] Could not connect to database: {e}")
        raise


def init_db():
    try:
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
                        channel_name TEXT,
                        user_id BIGINT,
                        user_name TEXT,
                        message TEXT,
                        replied_user BIGINT,
                        timestamp TIMESTAMPTZ DEFAULT NOW(),
                        tagged_me BOOLEAN,
                        is_owner BOOLEAN
                    );
                    """
                )
            conn.commit()
    except Exception as e:
        print(f"[DB ERROR] init_db failed: {e}")


def add_channel(channel_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO channels (id) VALUES (%s) ON CONFLICT DO NOTHING",
                    (channel_id,),
                )
            conn.commit()
    except Exception as e:
        print(f"[DB ERROR] add_channel failed: {e}")


def remove_channel(channel_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM channels WHERE id = %s", (channel_id,))
            conn.commit()
    except Exception as e:
        print(f"[DB ERROR] remove_channel failed: {e}")


def get_channels():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM channels")
                rows = cur.fetchall()
                return [row["id"] for row in rows]
    except Exception as e:
        print(f"[DB ERROR] get_channels failed: {e}")
        return []


def add_ignored_user(user_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO ignored_users (id) VALUES (%s) ON CONFLICT DO NOTHING",
                    (user_id,),
                )
            conn.commit()
    except Exception as e:
        print(f"[DB ERROR] add_ignored_user failed: {e}")


def remove_ignored_user(user_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM ignored_users WHERE id = %s", (user_id,))
            conn.commit()
    except Exception as e:
        print(f"[DB ERROR] remove_ignored_user failed: {e}")


def get_ignored_users():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM ignored_users")
                rows = cur.fetchall()
                return [row["id"] for row in rows]
    except Exception as e:
        print(f"[DB ERROR] get_ignored_users failed: {e}")
        return []


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
    try:
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
    except Exception as e:
        print(f"[DB ERROR] add_message_history failed: {e}")


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
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] get_message_history failed: {e}")
        return []


def count_consecutive_bot_replies(channel_id, bot_user_id, limit=10):
    """
    Returns the number of consecutive messages sent by the bot in the given channel,
    starting from the most recent message and stopping at the first non-bot message.
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_id, is_owner
                    FROM message_history
                    WHERE channel_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                    """,
                    (channel_id, limit),
                )
                rows = cur.fetchall()
                count = 0
                for row in rows:
                    # If the message is from the bot (is_owner True or user_id == bot_user_id)
                    if row["is_owner"] or str(row["user_id"]) == str(bot_user_id):
                        count += 1
                    else:
                        break  # Stop counting at the first non-bot message
                return count
    except Exception as e:
        print(f"[DB ERROR] count_consecutive_bot_replies failed: {e}")
        return 0


def count_bot_replies_today(bot_user_id):
    """
    Returns the number of messages sent by the bot (is_owner True or user_id == bot_user_id)
    for today (UTC).
    """
    try:
        today = datetime.datetime.utcnow().date()
        tomorrow = today + datetime.timedelta(days=1)
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM message_history
                    WHERE (is_owner = TRUE OR user_id = %s)
                    AND timestamp >= %s AND timestamp < %s
                    """,
                    (bot_user_id, today, tomorrow),
                )
                row = cur.fetchone()
                return row["count"] if row else 0
    except Exception as e:
        print(f"[DB ERROR] count_bot_replies_today failed: {e}")
        return 0
