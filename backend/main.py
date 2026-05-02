import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.database import (
    get_exam,
    init_db,
    list_exam_history,
    list_exam_scores,
    list_exams,
    list_results,
    list_students,
    save_exam,
    save_result_with_answers,
    set_students_exam_state,
    set_students_lock,
    upsert_student,
)
from backend.discovery import UDPDiscoveryServer
from backend.ws_manager import WSManager


class CommandRequest(BaseModel):
    student_ids: List[str] = Field(default_factory=list)


class StartExamRequest(CommandRequest):
    exam_id: str
    duration_minutes: int = 30


class SaveExamRequest(BaseModel):
    exam_id: str
    title: str
    duration_minutes: int
    exam: Dict[str, Any]


class JoinExamSessionRequest(CommandRequest):
    session_id: str


app = FastAPI(title="Net Support School Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

discovery_server = UDPDiscoveryServer()
ws_manager = WSManager()
active_exam_sessions: Dict[str, Dict[str, Any]] = {}
def compute_remaining_seconds(session: Dict[str, Any]) -> int:
    started_at = float(session.get("started_at", time.time()))
    duration_seconds = int(session.get("duration_minutes", 30)) * 60
    elapsed = max(int(time.time() - started_at), 0)
    return max(duration_seconds - elapsed, 0)




def target_students(student_ids: List[str]) -> List[str]:
    if student_ids:
        return [sid for sid in student_ids if sid in ws_manager.student_connections]
    return list(ws_manager.student_connections.keys())


async def process_student_event(student_id: str, student_name: str, payload_message: Dict[str, Any]) -> None:
    message_type = payload_message.get("type")
    if message_type not in {"exam_started", "exam_progress", "exam_submitted", "student_login"}:
        return
    payload = payload_message.get("payload", {})
    effective_name = payload.get("student_name") or student_name
    payload["student_id"] = student_id
    payload["student_name"] = effective_name
    await ws_manager.broadcast_to_tutors({"type": message_type, "payload": payload})
    if message_type == "student_login":
        return

    if message_type == "exam_submitted":
        set_students_exam_state([student_id], False)
        save_result_with_answers(
            session_id=payload.get("session_id", ""),
            student_id=student_id,
            exam_id=payload.get("exam_id", ""),
            exam_title=payload.get("exam_title", payload.get("exam_id", "")),
            score=int(payload.get("score", 0)),
            total_grade=int(payload.get("total_grade", 0)),
            answered_count=int(payload.get("answered_count", 0)),
            correct_count=int(payload.get("correct_count", 0)),
            wrong_count=int(payload.get("wrong_count", 0)),
            duration_minutes=int(payload.get("duration_minutes", 0)),
            answers=payload.get("answers", []),
        )


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    discovery_server.start()
    sample_path = Path(__file__).resolve().parents[1] / "exam_designer" / "sample_exam.json"
    if sample_path.exists():
        payload = json.loads(sample_path.read_text(encoding="utf-8"))
        save_exam(
            exam_id=payload.get("exam_id", "sample_exam"),
            title=payload.get("title", "Sample Exam"),
            duration_minutes=payload.get("duration_minutes", 20),
            payload=payload,
        )


@app.get("/students")
def get_students():
    return {"students": list_students()}


@app.get("/results")
def get_results():
    return {"results": list_results()}


@app.get("/reports/history")
def get_reports_history():
    return {"history": list_exam_history()}


@app.get("/reports/exam-details")
def get_exam_details(exam_title: str, exam_date: str):
    return {"rows": list_exam_scores(exam_title, exam_date)}


@app.get("/exams")
def get_exams():
    return {"exams": list_exams()}


@app.post("/exams")
def create_exam(payload: SaveExamRequest):
    save_exam(payload.exam_id, payload.title, payload.duration_minutes, payload.exam)
    return {"ok": True}


@app.post("/lock")
async def lock_students(req: CommandRequest):
    ids = target_students(req.student_ids)
    set_students_lock(ids, True)
    for sid in ids:
        await ws_manager.send_to_student(sid, {"type": "lock"})
    return {"ok": True, "target_count": len(ids)}


@app.post("/unlock")
async def unlock_students(req: CommandRequest):
    ids = target_students(req.student_ids)
    set_students_lock(ids, False)
    for sid in ids:
        await ws_manager.send_to_student(sid, {"type": "unlock"})
    return {"ok": True, "target_count": len(ids)}


@app.post("/start-exam")
async def start_exam(req: StartExamRequest):
    exam = get_exam(req.exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    ids = target_students(req.student_ids)
    session_id = f"session-{uuid.uuid4().hex[:8]}"
    active_exam_sessions[session_id] = {
        "session_id": session_id,
        "exam_id": req.exam_id,
        "exam_title": exam.get("title", req.exam_id),
        "duration_minutes": req.duration_minutes,
        "student_ids": ids,
        "total_questions": len(exam.get("payload", {}).get("questions", [])),
        "started_at": time.time(),
    }
    set_students_exam_state(ids, True)
    command = {
        "type": "start_exam",
        "session_id": session_id,
        "exam_id": req.exam_id,
        "exam_title": exam.get("title", req.exam_id),
        "duration_minutes": req.duration_minutes,
        "remaining_seconds": req.duration_minutes * 60,
        "exam": exam["payload"],
    }
    for sid in ids:
        await ws_manager.send_to_student(sid, command)

    await ws_manager.broadcast_to_tutors(
        {
            "type": "exam_session_started",
            "payload": {
                **active_exam_sessions[session_id],
                "remaining_seconds": compute_remaining_seconds(active_exam_sessions[session_id]),
            },
        }
    )
    return {"ok": True, "target_count": len(ids), "session_id": session_id}


@app.post("/join-exam-session")
async def join_exam_session(req: JoinExamSessionRequest):
    session = active_exam_sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    exam = get_exam(session.get("exam_id", ""))
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    ids = target_students(req.student_ids)
    if not ids:
        return {"ok": True, "target_count": 0, "session_id": req.session_id}

    current_members = set(session.get("student_ids", []))
    current_members.update(ids)
    session["student_ids"] = list(current_members)
    remaining_seconds = compute_remaining_seconds(session)
    set_students_exam_state(ids, True)

    command = {
        "type": "start_exam",
        "session_id": req.session_id,
        "exam_id": session.get("exam_id", ""),
        "exam_title": session.get("exam_title", session.get("exam_id", "")),
        "duration_minutes": int(session.get("duration_minutes", 30)),
        "remaining_seconds": remaining_seconds,
        "exam": exam["payload"],
    }
    for sid in ids:
        await ws_manager.send_to_student(sid, command)

    await ws_manager.broadcast_to_tutors(
        {
            "type": "exam_session_started",
            "payload": {
                **session,
                "remaining_seconds": remaining_seconds,
            },
        }
    )
    return {"ok": True, "target_count": len(ids), "session_id": req.session_id}


@app.post("/request-login")
async def request_login(req: CommandRequest):
    ids = target_students(req.student_ids)
    for sid in ids:
        await ws_manager.send_to_student(sid, {"type": "request_login"})
    return {"ok": True, "target_count": len(ids)}


@app.post("/stop-exam")
async def stop_exam(req: CommandRequest):
    ids = target_students(req.student_ids)
    set_students_exam_state(ids, False)
    for sid in ids:
        await ws_manager.send_to_student(sid, {"type": "stop_exam"})
    return {"ok": True, "target_count": len(ids)}


@app.websocket("/ws/tutor")
async def tutor_ws(websocket: WebSocket):
    await ws_manager.connect_tutor(websocket)
    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_tutor(websocket)


@app.websocket("/ws/student/{student_id}")
async def student_ws(
    websocket: WebSocket,
    student_id: str,
    student_name: str,
    machine_name: str,
):
    ip = websocket.client.host if websocket.client else ""
    await ws_manager.connect_student(student_id, websocket)
    upsert_student(student_id, student_name, machine_name, ip, status="online")
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            message_type = data.get("type")
            if message_type == "heartbeat":
                upsert_student(student_id, student_name, machine_name, ip, status="online")
            else:
                await process_student_event(student_id, student_name, data)
    except WebSocketDisconnect:
        upsert_student(student_id, student_name, machine_name, ip, status="offline")
    finally:
        ws_manager.disconnect_student(student_id)


@app.websocket("/ws/student-events/{student_id}")
async def student_events_ws(
    websocket: WebSocket,
    student_id: str,
    student_name: str,
    machine_name: str,
):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            await process_student_event(student_id, student_name, data)
    except WebSocketDisconnect:
        pass
