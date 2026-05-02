import json
import socket
import threading
from typing import Optional

from backend.database import upsert_student


class UDPDiscoveryServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 50555):
        self.host = host
        self.port = port
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        while self._running:
            data, addr = sock.recvfrom(4096)
            try:
                payload = json.loads(data.decode("utf-8"))
                if payload.get("type") != "student_announce":
                    continue
                upsert_student(
                    student_id=payload["student_id"],
                    student_name=payload["student_name"],
                    machine_name=payload["machine_name"],
                    ip=addr[0],
                    status="online",
                )
            except (json.JSONDecodeError, KeyError):
                continue
