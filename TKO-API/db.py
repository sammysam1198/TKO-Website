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

            CREATE TABLE IF NOT EXISTS tko_guestbook_posts (
                id SERIAL PRIMARY KEY,
                display_name VARCHAR(120) NOT NULL,
                mood_tag VARCHAR(120),
                message TEXT NOT NULL,
                upvotes INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

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
      
            CREATE TABLE IF NOT EXISTS newsletter_subscribers (
                id SERIAL PRIMARY KEY,
                first_name VARCHAR(100),
                email VARCHAR(255) NOT NULL UNIQUE,
                message TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
       
            CREATE TABLE IF NOT EXISTS dev_messages (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES tko_users(id) ON DELETE SET NULL,
                username VARCHAR(50),
                message TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        
            CREATE TABLE IF NOT EXISTS dev_issues (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                severity VARCHAR(20) DEFAULT 'normal',
                created_by VARCHAR(50),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
       
            CREATE TABLE IF NOT EXISTS dev_logs (
                id SERIAL PRIMARY KEY,
                message TEXT NOT NULL,
                level VARCHAR(20) DEFAULT 'info',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
       
            CREATE TABLE IF NOT EXISTS tko_forum_categories (
                id SERIAL PRIMARY KEY,
                slug VARCHAR(50) NOT NULL UNIQUE,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                display_order INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        
            CREATE TABLE IF NOT EXISTS tko_forum_posts (
                id SERIAL PRIMARY KEY,
                category_id INTEGER NOT NULL REFERENCES tko_forum_categories(id),
                user_id INTEGER REFERENCES tko_users(id) ON DELETE SET NULL,
                parent_id INTEGER REFERENCES tko_forum_posts(id) ON DELETE CASCADE,
                display_name VARCHAR(120) NOT NULL,
                title VARCHAR(255),
                content TEXT NOT NULL,
                depth INTEGER NOT NULL DEFAULT 0,
                reply_count INTEGER NOT NULL DEFAULT 0,
                score INTEGER NOT NULL DEFAULT 0,
                is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
     
            CREATE TABLE IF NOT EXISTS tko_forum_votes (
                id SERIAL PRIMARY KEY,
                post_id INTEGER NOT NULL REFERENCES tko_forum_posts(id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES tko_users(id) ON DELETE CASCADE,
                voter_fingerprint VARCHAR(64),
                vote_type SMALLINT NOT NULL CHECK (vote_type IN (-1, 1)),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
      
            CREATE INDEX IF NOT EXISTS idx_forum_posts_category ON tko_forum_posts(category_id);
            CREATE INDEX IF NOT EXISTS idx_forum_posts_parent ON tko_forum_posts(parent_id);
            CREATE INDEX IF NOT EXISTS idx_forum_posts_created ON tko_forum_posts(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_forum_votes_post ON tko_forum_votes(post_id);
  
            INSERT INTO tko_forum_categories (slug, name, description, display_order)
            VALUES
                ('general', 'General', 'General discussion about TKO', 1),
                ('music', 'Music', 'Music releases, artists, and soundtrack discussion', 2),
                ('announcements', 'Announcements', 'Official project updates and news', 3)
            ON CONFLICT (slug) DO NOTHING;
     
            ALTER TABLE tko_users
                ADD COLUMN IF NOT EXISTS role VARCHAR(30) NOT NULL DEFAULT 'user',
                ADD COLUMN IF NOT EXISTS theme_preference VARCHAR(20) NOT NULL DEFAULT 'dark',
                ADD COLUMN IF NOT EXISTS colorblind_mode BOOLEAN NOT NULL DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS two_factor_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS two_factor_method VARCHAR(20),
                ADD COLUMN IF NOT EXISTS two_factor_secret TEXT,
                ADD COLUMN IF NOT EXISTS phone_number VARCHAR(30),
                ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN NOT NULL DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP;
     
            CREATE TABLE IF NOT EXISTS tko_password_reset_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES tko_users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tko_two_factor_backup_codes (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES tko_users(id) ON DELETE CASCADE,
                code_hash TEXT NOT NULL,
                used_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tko_email_campaigns (
                id SERIAL PRIMARY KEY,
                subject TEXT NOT NULL,
                body_html TEXT,
                body_text TEXT,
                created_by INTEGER REFERENCES tko_users(id) ON DELETE SET NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'draft',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tko_email_campaign_recipients (
                id SERIAL PRIMARY KEY,
                campaign_id INTEGER NOT NULL REFERENCES tko_email_campaigns(id) ON DELETE CASCADE,
                email VARCHAR(255) NOT NULL,
                delivery_status VARCHAR(20) NOT NULL DEFAULT 'pending',
                error_message TEXT,
                sent_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS CG_contact_messages (
                id SERIAL PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                email VARCHAR(255) NOT NULL,
                subject VARVHAR(255) NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_read BOOLEAN NOT NULL DEFAULT FALSE
            );
            """
        )

        

        conn.commit()
    finally:
        cur.close()
        conn.close()
