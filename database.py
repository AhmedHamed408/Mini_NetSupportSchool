import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "nss.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            student_name TEXT,
            machine_name TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            exam_id TEXT PRIMARY KEY,
            title TEXT,
            duration_minutes INTEGER
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            exam_id TEXT,
            score INTEGER
        )
        """)