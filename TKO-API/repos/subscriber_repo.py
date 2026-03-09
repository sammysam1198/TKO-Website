from config.db import get_db_conn


def create_subscriber(first_name, email, message):
    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO newsletter_subscribers (first_name, email, message)
        VALUES (%s, %s, %s)
        RETURNING id, first_name, email, message, created_at;
        """,
        (first_name, email, message),
    )

    row = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return row
