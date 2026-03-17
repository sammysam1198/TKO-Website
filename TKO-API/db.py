import os
import psycopg2


def get_db_conn():
    """Create a fresh PostgreSQL connection using Render's DATABASE_URL."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return psycopg2.connect(database_url)


def init_db():
    """Create required tables if they do not already exist."""
    conn = get_db_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tko_subscribers (
                id SERIAL PRIMARY KEY,
                first_name VARCHAR(120),
                email VARCHAR(255) NOT NULL UNIQUE,
                interest TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tko_guestbook_posts (
                id SERIAL PRIMARY KEY,
                display_name VARCHAR(120) NOT NULL,
                mood_tag VARCHAR(120),
                message TEXT NOT NULL,
                upvotes INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tko_users (
                id SERIAL PRIMARY KEY,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                agreed_to_terms BOOLEAN NOT NULL DEFAULT FALSE,
                profile_image_url TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS newsletter_subscribers (
                id SERIAL PRIMARY KEY,
                first_name VARCHAR(100),
                email VARCHAR(255) NOT NULL UNIQUE,
                message TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

         cur.execute(
            """
            CREATE TABLE IF NOT EXISTS dev_messages (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES tko_users(id) ON DELETE SET NULL,
                username VARCHAR(50),
                message TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS dev_issues (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                severity VARCHAR(20) DEFAULT 'normal',
                created_by VARCHAR(50),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS dev_logs (
                id SERIAL PRIMARY KEY,
                message TEXT NOT NULL,
                level VARCHAR(20) DEFAULT 'info',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()
