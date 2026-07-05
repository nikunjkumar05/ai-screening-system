import sqlite3

def migrate():
    conn = sqlite3.connect("candidate_screening.db")
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE interview_sessions ADD COLUMN difficulty VARCHAR DEFAULT 'Mid-Level'")
        cursor.execute("ALTER TABLE interview_sessions ADD COLUMN question_count INTEGER DEFAULT 5")
        cursor.execute("ALTER TABLE interview_sessions ADD COLUMN time_limit INTEGER DEFAULT 120")
        conn.commit()
        print("Migration successful")
    except Exception as e:
        print("Migration failed:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
