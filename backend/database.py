import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


DB_PATH = Path(__file__).resolve().parent / "nss.db"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if not _column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                student_name TEXT NOT NULL,
                machine_name TEXT NOT NULL,
                ip TEXT,
                status TEXT DEFAULT 'online',
                locked INTEGER DEFAULT 0,
                exam_active INTEGER DEFAULT 0,
                last_heartbeat TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exams (
                exam_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                student_id TEXT NOT NULL,
                exam_id TEXT NOT NULL,
                exam_title TEXT NOT NULL,
                score INTEGER NOT NULL,
                total_grade INTEGER NOT NULL,
                answered_count INTEGER NOT NULL,
                correct_count INTEGER NOT NULL,
                wrong_count INTEGER NOT NULL,
                duration_minutes INTEGER NOT NULL,
                submitted_at TEXT NOT NULL
            )
            """
        )
        # Backward-compatible migration for older DBs created before new fields.
        _add_column_if_missing(conn, "results", "session_id", "TEXT")
        _add_column_if_missing(conn, "results", "exam_title", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "results", "total_grade", "INTEGER NOT NULL DEFAULT 0")
        _add_column_if_missing(conn, "results", "correct_count", "INTEGER NOT NULL DEFAULT 0")
        _add_column_if_missing(conn, "results", "wrong_count", "INTEGER NOT NULL DEFAULT 0")
        _add_column_if_missing(conn, "results", "duration_minutes", "INTEGER NOT NULL DEFAULT 0")

        # Normalize empty defaults in existing rows.
        conn.execute("UPDATE results SET exam_title = exam_id WHERE exam_title IS NULL OR exam_title = ''")
        conn.execute("UPDATE results SET total_grade = score WHERE total_grade IS NULL OR total_grade = 0")
        conn.execute("UPDATE results SET correct_count = score WHERE correct_count IS NULL")
        conn.execute(
            "UPDATE results SET wrong_count = MAX(answered_count - correct_count, 0) WHERE wrong_count IS NULL"
        )
        conn.execute("UPDATE results SET duration_minutes = 0 WHERE duration_minutes IS NULL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS result_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                result_id INTEGER NOT NULL,
                question_index INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                selected_answer TEXT,
                correct_answer TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                skipped INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_student(
    student_id: str,
    student_name: str,
    machine_name: str,
    ip: Optional[str],
    status: str = "online",
) -> None:
    heartbeat = utc_now()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO students (student_id, student_name, machine_name, ip, status, last_heartbeat)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_id) DO UPDATE SET
                student_name=excluded.student_name,
                machine_name=excluded.machine_name,
                ip=excluded.ip,
                status=excluded.status,
                last_heartbeat=excluded.last_heartbeat
            """,
            (student_id, student_name, machine_name, ip, status, heartbeat),
        )


def list_students() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM students ORDER BY student_name COLLATE NOCASE ASC"
        ).fetchall()
    return [dict(row) for row in rows]


def set_students_lock(student_ids: List[str], lock_state: bool) -> None:
    if not student_ids:
        return
    placeholders = ",".join("?" for _ in student_ids)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE students SET locked=? WHERE student_id IN ({placeholders})",
            [1 if lock_state else 0, *student_ids],
        )


def set_students_exam_state(student_ids: List[str], active: bool) -> None:
    if not student_ids:
        return
    placeholders = ",".join("?" for _ in student_ids)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE students SET exam_active=? WHERE student_id IN ({placeholders})",
            [1 if active else 0, *student_ids],
        )


def save_exam(exam_id: str, title: str, duration_minutes: int, payload: Dict[str, Any]) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO exams (exam_id, title, duration_minutes, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (exam_id, title, duration_minutes, json.dumps(payload, ensure_ascii=False), utc_now()),
        )


def get_exam(exam_id: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM exams WHERE exam_id=?", (exam_id,)).fetchone()
    if not row:
        return None
    data = dict(row)
    data["payload"] = json.loads(data["payload_json"])
    return data


def list_exams() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM exams ORDER BY created_at DESC").fetchall()
    items = []
    for row in rows:
        data = dict(row)
        data["payload"] = json.loads(data["payload_json"])
        items.append(data)
    return items


def save_result(student_id: str, exam_id: str, score: int, answered_count: int) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO results (
                session_id, student_id, exam_id, exam_title, score, total_grade,
                answered_count, correct_count, wrong_count, duration_minutes, submitted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                None,
                student_id,
                exam_id,
                exam_id,
                score,
                score,
                answered_count,
                score,
                max(answered_count - score, 0),
                0,
                utc_now(),
            ),
        )


def list_results() -> List[Dict[str, Any]]:
    query = """
    SELECT
        r.id,
        r.session_id,
        r.exam_id,
        r.exam_title,
        s.student_name,
        r.score,
        r.total_grade,
        r.answered_count,
        r.correct_count,
        r.wrong_count,
        r.duration_minutes,
        r.submitted_at
    FROM results r
    LEFT JOIN students s ON s.student_id = r.student_id
    ORDER BY r.submitted_at DESC
    """
    with get_conn() as conn:
        rows = conn.execute(query).fetchall()
    return [dict(row) for row in rows]


def save_result_with_answers(
    session_id: str,
    student_id: str,
    exam_id: str,
    exam_title: str,
    score: int,
    total_grade: int,
    answered_count: int,
    correct_count: int,
    wrong_count: int,
    duration_minutes: int,
    answers: List[Dict[str, Any]],
) -> int:
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO results (
                session_id, student_id, exam_id, exam_title, score, total_grade,
                answered_count, correct_count, wrong_count, duration_minutes, submitted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                student_id,
                exam_id,
                exam_title,
                score,
                total_grade,
                answered_count,
                correct_count,
                wrong_count,
                duration_minutes,
                utc_now(),
            ),
        )
        result_id = cursor.lastrowid
        for ans in answers:
            conn.execute(
                """
                INSERT INTO result_answers (
                    result_id, question_index, question_text, selected_answer,
                    correct_answer, is_correct, skipped
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result_id,
                    ans.get("question_index", 0),
                    ans.get("question_text", ""),
                    ans.get("selected_answer"),
                    ans.get("correct_answer", ""),
                    1 if ans.get("is_correct") else 0,
                    1 if ans.get("skipped") else 0,
                ),
            )
    return int(result_id)


def list_exam_history() -> List[Dict[str, Any]]:
    query = """
    SELECT
        exam_title,
        DATE(submitted_at) AS exam_date,
        COUNT(*) AS students_count,
        AVG(CASE WHEN total_grade > 0 THEN (score * 100.0 / total_grade) ELSE 0 END) AS avg_percentage
    FROM results
    GROUP BY exam_title, DATE(submitted_at)
    ORDER BY exam_date DESC
    """
    with get_conn() as conn:
        rows = conn.execute(query).fetchall()
    return [dict(row) for row in rows]


def list_exam_scores(exam_title: str, exam_date: str) -> List[Dict[str, Any]]:
    query = """
    SELECT
        s.student_name,
        r.score,
        r.total_grade,
        ROUND(CASE WHEN r.total_grade > 0 THEN (r.score * 100.0 / r.total_grade) ELSE 0 END, 2) AS percentage,
        CASE WHEN (CASE WHEN r.total_grade > 0 THEN (r.score * 100.0 / r.total_grade) ELSE 0 END) >= 50
            THEN 'passed' ELSE 'failed' END AS result_status,
        r.answered_count,
        r.correct_count,
        r.wrong_count,
        r.submitted_at
    FROM results r
    LEFT JOIN students s ON s.student_id = r.student_id
    WHERE r.exam_title = ? AND DATE(r.submitted_at) = ?
    ORDER BY s.student_name COLLATE NOCASE ASC
    """
    with get_conn() as conn:
        rows = conn.execute(query, (exam_title, exam_date)).fetchall()
    return [dict(row) for row in rows]
