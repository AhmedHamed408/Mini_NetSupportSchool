import json
from typing import Dict, List, Set

from fastapi import WebSocket


class WSManager:
    def __init__(self):
        self.student_connections: Dict[str, WebSocket] = {}
        self.tutor_connections: Set[WebSocket] = set()

    async def connect_student(self, student_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.student_connections[student_id] = websocket

    def disconnect_student(self, student_id: str) -> None:
        self.student_connections.pop(student_id, None)

    async def connect_tutor(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.tutor_connections.add(websocket)

    def disconnect_tutor(self, websocket: WebSocket) -> None:
        self.tutor_connections.discard(websocket)

    async def send_to_student(self, student_id: str, payload: dict) -> None:
        sock = self.student_connections.get(student_id)
        if sock:
            await sock.send_text(json.dumps(payload, ensure_ascii=False))

    async def broadcast_to_tutors(self, payload: dict) -> None:
        message = json.dumps(payload, ensure_ascii=False)
        dead: List[WebSocket] = []
        for sock in self.tutor_connections:
            try:
                await sock.send_text(message)
            except Exception:
                dead.append(sock)
        for sock in dead:
            self.tutor_connections.discard(sock)
