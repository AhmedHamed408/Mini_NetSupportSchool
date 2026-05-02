import asyncio
import json
import os
import socket
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import BOTH, Label, Tk, messagebox, simpledialog
from urllib.parse import urlencode

import websockets


@dataclass
class StudentConfig:
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    discovery_port: int = 50555
    heartbeat_interval: int = 5
    student_name: str = ""
    machine_name: str = socket.gethostname()
    student_id: str = ""

    def __post_init__(self):
        if not self.student_id:
            self.student_id = get_or_create_device_id()


def get_or_create_device_id() -> str:
    base_dir = Path(__file__).resolve().parent
    id_file = base_dir / "device_id.txt"
    if id_file.exists():
        value = id_file.read_text(encoding="utf-8").strip()
        if value:
            return value
    # Stable fallback id derived from machine identity.
    machine = socket.gethostname().strip().replace(" ", "_")
    value = f"student-{machine.lower()}"
    id_file.write_text(value, encoding="utf-8")
    return value


class OverlayWindow:
    def __init__(self):
        self.root = None
        self._thread = None

    def show(self, message: str, color: str = "#111111") -> None:
        if self.root:
            self.update_message(message, color)
            return
        self._thread = threading.Thread(target=self._run, args=(message, color), daemon=True)
        self._thread.start()

    def _run(self, message: str, color: str):
        root = Tk()
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)
        root.configure(bg=color)
        root.protocol("WM_DELETE_WINDOW", lambda: None)
        label = Label(
            root,
            text=message,
            font=("Arial", 36, "bold"),
            fg="white",
            bg=color,
            anchor="center",
            justify="center",
        )
        label.pack(fill=BOTH, expand=True)
        root.label = label
        self.root = root
        root.mainloop()
        self.root = None

    def update_message(self, message: str, color: str) -> None:
        if self.root:
            self.root.configure(bg=color)
            self.root.label.configure(text=message, bg=color)

    def hide(self) -> None:
        if self.root:
            self.root.after(0, self.root.destroy)


class StudentService:
    def __init__(self, config: StudentConfig):
        self.config = config
        self.overlay = OverlayWindow()
        self.exam_process = None
        self.log_file = Path(__file__).resolve().parent / "student_client.log"
        self.stop_signal_path = Path(__file__).resolve().parent / "stop_exam.signal"

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with self.log_file.open("a", encoding="utf-8") as fp:
            fp.write(f"[{timestamp}] {message}\n")

    @property
    def websocket_url(self) -> str:
        query = urlencode(
            {
                "student_name": self.config.student_name,
                "machine_name": self.config.machine_name,
            }
        )
        return (
            f"ws://{self.config.server_host}:{self.config.server_port}"
            f"/ws/student/{self.config.student_id}?{query}"
        )

    def broadcast_announce(self) -> None:
        payload = {
            "type": "student_announce",
            "student_id": self.config.student_id,
            "student_name": self.config.student_name,
            "machine_name": self.config.machine_name,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(data, ("<broadcast>", self.config.discovery_port))
        sock.close()

    async def heartbeat_loop(self, ws) -> None:
        while True:
            self.broadcast_announce()
            await ws.send(json.dumps({"type": "heartbeat"}))
            await asyncio.sleep(self.config.heartbeat_interval)

    async def handle_command(self, ws, command: dict) -> None:
        command_type = command.get("type")
        self.log(f"Received command: {command_type}")
        if command_type == "lock":
            self.overlay.show("تم قفل الجهاز بواسطة المعلم", color="#1f2937")
        elif command_type == "unlock":
            self.overlay.hide()
        elif command_type == "request_login":
            await self.request_login(ws)
        elif command_type == "start_exam":
            await self.start_exam_process(command)
        elif command_type == "stop_exam":
            self.overlay.hide()
            if self.exam_process and self.exam_process.poll() is None:
                self.log("Stop exam requested by tutor; asking exam window to submit and close.")
                self.stop_signal_path.write_text("stop", encoding="utf-8")
                try:
                    self.exam_process.wait(timeout=6)
                except Exception:
                    self.log("Exam window did not close in time; forcing terminate.")
                    self.exam_process.terminate()
                    try:
                        self.exam_process.wait(timeout=2)
                    except Exception:
                        self.exam_process.kill()
            self.exam_process = None

    async def request_login(self, ws) -> None:
        entered_name = self._ask_student_name()
        if entered_name:
            self.config.student_name = entered_name
        self.overlay.show("تم تسجيل الدخول بنجاح.\nيرجى الانتظار حتى يبدأ المعلم الامتحان.", color="#1d4ed8")
        await ws.send(
            json.dumps(
                {
                    "type": "student_login",
                    "payload": {
                        "student_name": self.config.student_name,
                    },
                },
                ensure_ascii=False,
            )
        )

    def _ask_student_name(self) -> str:
        while True:
            root = Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            name = simpledialog.askstring(
                "تسجيل دخول الامتحان",
                "أدخل اسم الطالب (إجباري):",
                parent=root,
            )
            normalized = (name or "").strip()
            if normalized:
                root.destroy()
                return normalized
            messagebox.showwarning("تنبيه", "اسم الطالب مطلوب ولا يمكن تركه فارغا.", parent=root)
            root.destroy()

    async def start_exam_process(self, command: dict) -> None:
        if self.exam_process and self.exam_process.poll() is None:
            self.log("Exam process already running, skipping new start.")
            return
        if self.stop_signal_path.exists():
            self.stop_signal_path.unlink(missing_ok=True)
        payload = {
            **command,
            "student_id": self.config.student_id,
            "student_name": self.config.student_name,
            "machine_name": self.config.machine_name,
            "server_url": f"http://{self.config.server_host}:{self.config.server_port}",
        }
        payload_path = Path(__file__).resolve().parent / "active_exam_payload.json"
        payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        exam_script = Path(__file__).resolve().parent / "exam_session.py"
        self.log(f"Launching exam window: {exam_script}")
        self.exam_process = subprocess.Popen(
            [os.sys.executable, str(exam_script), str(payload_path), str(self.stop_signal_path)],
            cwd=str(Path(__file__).resolve().parent),
        )
        await asyncio.sleep(0.8)
        if self.exam_process.poll() is not None:
            self.log(f"Exam process exited early with code {self.exam_process.returncode}")
            self.overlay.show("فشل بدء نافذة الامتحان - راجع student_client.log", color="#7f1d1d")

    async def run(self) -> None:
        while True:
            try:
                async with websockets.connect(self.websocket_url) as ws:
                    self.log(f"Connected to backend: {self.websocket_url}")
                    heartbeat = asyncio.create_task(self.heartbeat_loop(ws))
                    async for message in ws:
                        command = json.loads(message)
                        await self.handle_command(ws, command)
                    heartbeat.cancel()
            except Exception as ex:
                self.log(f"Connection error: {ex}")
                await asyncio.sleep(3)


if __name__ == "__main__":
    cfg = StudentConfig()
    service = StudentService(cfg)
    asyncio.run(service.run())
