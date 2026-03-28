from psycopg2.extras import RealDictCursor
from config.db import get_db_conn


def create_contact_message(name: str, email: str, subject: str, message: str):
    conn = get_db_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO contact_messages (name, email, subject, message)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, name, email, subject, message, created_at, is_read;
                    """,
                    (name, email, subject, message),
                )
                return cur.fetchone()
    finally:
        conn.close()


def get_contact_messages(limit: int = 100):
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, name, email, subject, message, created_at, is_read
                FROM contact_messages
                ORDER BY created_at DESC
                LIMIT %s;
                """,
                (limit,),
            )
            return cur.fetchall()
    finally:
        conn.close()


def mark_contact_message_read(message_id: int, is_read: bool = True):
    conn = get_db_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE contact_messages
                    SET is_read = %s
                    WHERE id = %s
                    RETURNING id, is_read;
                    """,
                    (is_read, message_id),
                )
                return cur.fetchone()
    finally:
        conn.close()
