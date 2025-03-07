"""Add prep_attended column to members table."""

import sqlite3
import os


def upgrade():
    """Add prep_attended column to members table."""
    db_path = os.getenv("DB_PATH", "message_log.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "ALTER TABLE members ADD COLUMN prep_attended BOOLEAN NOT NULL DEFAULT FALSE"
    )
    conn.commit()
    conn.close()


def downgrade():
    """Remove prep_attended column from members table."""
    db_path = os.getenv("DB_PATH", "message_log.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE members DROP COLUMN prep_attended")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    upgrade()
