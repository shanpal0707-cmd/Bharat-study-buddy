
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "data", "users.db")


def get_connection():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def init_database():
    connection = get_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS study_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                subjects TEXT NOT NULL,
                exam_date TEXT NOT NULL,
                daily_hours REAL NOT NULL,
                weak_subjects TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS study_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                task_date TEXT NOT NULL,
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                start_time TEXT DEFAULT '',
                duration_minutes INTEGER NOT NULL DEFAULT 60,
                is_completed INTEGER NOT NULL DEFAULT 0,
                completed_at TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES study_plans(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS pending_signups (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                otp_hash TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                last_sent_at INTEGER NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS guru_exam_dates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                exam_date TEXT NOT NULL,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS paper_analyzer_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                subject TEXT NOT NULL DEFAULT '',
                exam_name TEXT DEFAULT '',
                year TEXT DEFAULT '',
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL DEFAULT 0,
                extracted_text TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS paper_analyzer_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                total_papers INTEGER NOT NULL DEFAULT 0,
                years_covered TEXT DEFAULT '',
                report_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)

        connection.commit()

    finally:
        connection.close()
