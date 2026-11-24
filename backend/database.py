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


# Seed data for existing registered users so they persist across fresh/ephemeral deployments.
# Uses exact original password hashes and creation timestamps.
INITIAL_USERS = [
    (
        2,
        "S",
        "s@gmail.com",
        "scrypt:32768:8:1$XX8GaLfNqKIuiKKS$5c5542d2b1b8e6e8285547a03dddccc8d9543265fab6017fe2ce446eb493a1c169e1a7add6a0d04b1f73a77220488ab79016e82d33b46a87da08eb8e74d9456a",
        "2026-10-11 13:57:42"
    ),
    (
        3,
        "d",
        "d@gmail.com",
        "scrypt:32768:8:1$pYi10itcpoKzAyW7$a391b7aee46d1c94f998a82daddf55a7a75d8259dd81c6697f23f9fbcc7a9afaf8c1b5968d2f35eaa19ef69fe4b085a810f4fefa99d963e7e956f091df3632fa",
        "2026-10-11 14:25:39"
    ),
    (
        4,
        "wow",
        "wow.digitalmarketing77@gmail.com",
        "scrypt:32768:8:1$q0SjnMMrt9bJABnx$54b4ed4f562b029028d5943a8da33922315490bb0b232fdf7d8e24b32b79b1581ff24b19f8560e65365c41a838e4214e614ec551053931c10b75341205358534",
        "2026-10-12 09:14:37"
    ),
    (
        8,
        "shivani",
        "shivanipal63435@gmail.com",
        "scrypt:32768:8:1$22MFGl4lJhsOfC0G$b4becd033f20d37e7dc4b947adebfa69628405e763c535aef93d7460519dd3975f8efb3d042efb4ea9604e1efdfe442d9675b124bee1c978189ca2f0a011d53c",
        "2026-10-13 18:47:09"
    )
]

INITIAL_PLANS = [
    (
        5,
        3,
        "Study Plan",
        '["DBMS"]',
        "2026-11-28",
        3.0,
        '["SQL Commands"]',
        "2026-11-24 08:04:39"
    )
]

INITIAL_TASKS = [
    (85, 5, 3, "2026-11-25", "DBMS", "SQL SELECT basics", "18:00", 60, 0, None),
    (86, 5, 3, "2026-11-25", "DBMS", "SQL WHERE & ORDER BY", "19:00", 60, 0, None),
    (87, 5, 3, "2026-11-25", "DBMS", "Normalization introduction", "20:00", 60, 0, None),
    (88, 5, 3, "2026-11-26", "DBMS", "1NF concepts", "18:00", 45, 0, None),
    (89, 5, 3, "2026-11-26", "DBMS", "2NF concepts", "18:45", 45, 0, None),
    (90, 5, 3, "2026-11-26", "DBMS", "3NF concepts", "19:30", 45, 0, None),
    (91, 5, 3, "2026-11-26", "DBMS", "SQL JOINs practice", "20:15", 45, 0, None),
    (92, 5, 3, "2026-11-27", "DBMS", "Normalization exercises", "18:00", 90, 0, None),
    (93, 5, 3, "2026-11-27", "DBMS", "SQL Commands practice", "19:30", 90, 0, None),
    (94, 5, 3, "2026-11-28", "DBMS", "Normalization revision", "18:00", 60, 0, None),
    (95, 5, 3, "2026-11-28", "DBMS", "SQL Commands quick review", "19:00", 60, 0, None),
    (96, 5, 3, "2026-11-28", "DBMS", "Mock test (DBMS)", "20:00", 60, 0, None)
]


def _seed_initial_data(conn):
    """Safely populates initial seed records using INSERT OR IGNORE.
    Ensures existing registered accounts and initial study data persist on fresh/ephemeral deployments.
    Never overwrites or alters existing rows.
    """
    for user in INITIAL_USERS:
        conn.execute("""
            INSERT OR IGNORE INTO users (id, name, email, password, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, user)

    for plan in INITIAL_PLANS:
        conn.execute("""
            INSERT OR IGNORE INTO study_plans
                (id, user_id, title, subjects, exam_date, daily_hours, weak_subjects, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, plan)

    for task in INITIAL_TASKS:
        conn.execute("""
            INSERT OR IGNORE INTO study_tasks
                (id, plan_id, user_id, task_date, subject, topic, start_time, duration_minutes, is_completed, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, task)


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
            _seed_initial_data(conn)
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
                _seed_initial_data(conn)
                conn.commit()
                logger.info("Created missing tables successfully.")
            else:
                user_count = conn.execute("SELECT count(*) FROM users").fetchone()[0]
                if user_count == 0:
                    logger.info("Seeding initial users into empty users table...")
                    _seed_initial_data(conn)
                    conn.commit()
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
