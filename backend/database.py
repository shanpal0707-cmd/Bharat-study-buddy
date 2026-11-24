import sqlite3
import os
import logging

logger = logging.getLogger("bharat_study_buddy.database")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [DB] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATABASE_PATH = os.path.join(BASE_DIR, "data", "users.db")
DATABASE = os.getenv("DATABASE_PATH", DEFAULT_DATABASE_PATH)

_initialized = False

REQUIRED_TABLES = (
    "users",
    "study_plans",
    "study_tasks",
    "pending_signups",
    "guru_exam_dates",
    "paper_analyzer_files",
    "paper_analyzer_reports",
)


def get_database_path():
    """Returns the absolute path to the configured SQLite database file."""
    return DATABASE


def _connect_raw():
    db_path = get_database_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _create_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
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

    conn.execute("""
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

    conn.execute("""
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

    conn.execute("""
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

    conn.execute("""
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

    conn.execute("""
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


def init_database():
    """Initializes the database schema if tables do not exist.
    Completely idempotent: creates missing tables without altering or resetting existing data.
    """
    global _initialized
    db_path = get_database_path()
    logger.info("Checking and initializing database schema at: %s", db_path)

    try:
        conn = _connect_raw()
        try:
            _create_schema(conn)
            conn.commit()
            _initialized = True
            logger.info("Database schema initialized successfully.")
        finally:
            conn.close()
    except Exception as exc:
        logger.error("Database initialization failed at %s: %s", db_path, exc, exc_info=True)
        raise


def ensure_database(force=False):
    """Ensures all required tables exist in the database.
    Checks sqlite_master and creates any missing tables.
    """
    global _initialized
    if _initialized and not force:
        return

    try:
        conn = _connect_raw()
        try:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            existing = {r["name"] for r in rows}
            missing = [t for t in REQUIRED_TABLES if t not in existing]
            if missing:
                logger.warning("Missing database tables detected: %s. Creating schema...", missing)
                _create_schema(conn)
                conn.commit()
                logger.info("Created missing tables successfully.")
            _initialized = True
        finally:
            conn.close()
    except Exception as exc:
        logger.error("Failed to ensure database schema: %s", exc, exc_info=True)
        raise


def get_connection():
    """Returns an active SQLite connection with row_factory and foreign keys enabled,
    ensuring that database tables are initialized.
    """
    ensure_database()
    return _connect_raw()
