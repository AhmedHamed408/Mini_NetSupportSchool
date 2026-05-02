from typing import Dict, List

import qtawesome as qta
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tutor_ui.api_client import TutorApiClient
from tutor_ui.ws_client import TutorWSClient


# PERSON 4 OWNERSHIP:
# Live tracking dashboard, login/start/finish controls, and student progress monitoring.
class ExamMonitorWindow(QMainWindow):
    def __init__(
        self,
        api: TutorApiClient,
        server_base_url: str,
        exam_title: str,
        exam_id: str,
        duration_minutes: int,
        students: List[dict],
        parent=None,
    ):
        super().__init__(parent)
        self.api = api
        self.session_id = ""
        self.exam_title = exam_title
        self.exam_id = exam_id
        self.duration_minutes = duration_minutes
        self.students = list(students)
        self.student_ids = [s.get("student_id") for s in self.students if s.get("student_id")]
        self.student_rows: Dict[str, int] = {}
        self.question_states: Dict[str, List[str]] = {}
        self.final_stats: Dict[str, dict] = {}
        self.login_ready_students = set()
        self.total_questions = 0
        self.submitted_students = set()
        self.summary_opened = False
        self.remaining_seconds = self.duration_minutes * 60
        self.session_started = False
        self.started_student_ids = set()
        self.setWindowTitle(f"Test Console - {exam_title}")
        self.resize(1250, 700)
        self._build_ui()
        self._add_students()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick_timer)
        ws_url = server_base_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws/tutor"
        self.ws_client = TutorWSClient(ws_url)
        self.ws_client.message_received.connect(self.handle_event)
        self.ws_client.start()

    def closeEvent(self, event):
        if hasattr(self, "ws_client"):
            self.ws_client.stop()
            self.ws_client.wait(1000)
        super().closeEvent(event)

    def _build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        root.setStyleSheet(
            """
            QWidget { background:#f8fafc; }
            QFrame#Card { background:white; border-radius:12px; border:1px solid #dbeafe; }
            QLabel#TopTitle { font-size:20px; font-weight:700; color:#0f172a; }
            QLabel#TopHint { font-size:13px; color:#64748b; }
            QTableWidget {
                background:white;
                border:1px solid #cbd5e1;
                border-radius:10px;
                gridline-color:#e2e8f0;
                selection-background-color:#dbeafe;
            }
            QPushButton {
                color:white;
                border:none;
                border-radius:10px;
                min-height:36px;
                font-weight:700;
                padding:6px 12px;
            }
            """
        )
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        top_card = QFrame()
        top_card.setObjectName("Card")
        top_shadow = QGraphicsDropShadowEffect()
        top_shadow.setBlurRadius(18)
        top_shadow.setYOffset(3)
        top_shadow.setColor(QColor(15, 23, 42, 35))
        top_card.setGraphicsEffect(top_shadow)
        top_layout = QVBoxLayout(top_card)
        title = QLabel(f"Test Console - {self.exam_title}")
        title.setObjectName("TopTitle")
        self.session_label = QLabel("Session: Pending")
        self.session_label.setObjectName("TopHint")
        self.time_label = QLabel(f"Time Left: {self._format_seconds(self.remaining_seconds)}")
        self.time_label.setObjectName("TopHint")
        top_layout.addWidget(title)
        top_layout.addWidget(self.session_label)
        top_layout.addWidget(self.time_label)

        actions = QHBoxLayout()
        self.login_btn = QPushButton("Login Test")
        self.login_btn.setStyleSheet("QPushButton{background:#0ea5e9;} QPushButton:hover{background:#0284c7;}")
        self.login_btn.setIcon(qta.icon("fa5s.user-check", color="white"))
        self.start_btn = QPushButton("Start Test")
        self.start_btn.setStyleSheet("QPushButton{background:#22c55e;} QPushButton:hover{background:#16a34a;}")
        self.start_btn.setIcon(qta.icon("fa5s.play", color="white"))
        self.finish_btn = QPushButton("Finish Test")
        self.finish_btn.setStyleSheet("QPushButton{background:#ef4444;} QPushButton:hover{background:#dc2626;}")
        self.finish_btn.setIcon(qta.icon("fa5s.stop", color="white"))
        self.login_btn.clicked.connect(self.request_login_for_students)
        self.start_btn.clicked.connect(self.start_exam_for_students)
        self.finish_btn.clicked.connect(self.finish_exam_for_students)
        actions.addWidget(self.login_btn)
        actions.addWidget(self.start_btn)
        actions.addWidget(self.finish_btn)
        actions.addStretch()
        top_layout.addLayout(actions)
        layout.addWidget(top_card)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Name", "Login Name", "Description", "Progress"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)
        self.setCentralWidget(root)
        self.setLayoutDirection(Qt.LeftToRight)

    def _add_students(self):
        for st in self.students:
            sid = st.get("student_id", "")
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.student_rows[sid] = row
            self.table.setItem(row, 0, QTableWidgetItem(st.get("machine_name", sid)))
            self.table.setItem(row, 1, QTableWidgetItem(self._clean_login_name(st.get("student_name", ""))))
            self.table.setItem(row, 2, QTableWidgetItem("Waiting student login..."))
            self.table.setItem(row, 3, QTableWidgetItem("Remaining"))

    def _clean_login_name(self, student_name: str) -> str:
        normalized = (student_name or "").strip()
        if normalized.lower() == "student demo":
            return ""
        return normalized

    def _get_row(self, student_id: str) -> int:
        if student_id in self.student_rows:
            return self.student_rows[student_id]
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.student_rows[student_id] = row
        self.table.setItem(row, 0, QTableWidgetItem(student_id))
        self.table.setItem(row, 1, QTableWidgetItem(""))
        self.table.setItem(row, 2, QTableWidgetItem("Waiting login"))
        self.table.setItem(row, 3, QTableWidgetItem("Remaining"))
        return row

    def _set(self, row: int, col: int, value):
        self.table.setItem(row, col, QTableWidgetItem(str(value)))

    def _render_circles(self, states: List[str]) -> str:
        if not states:
            return ""
        chunks = []
        for state in states:
            if state == "correct":
                chunks.append("<span style='color:#16a34a;font-size:18px'>●</span>")
            elif state == "wrong":
                chunks.append("<span style='color:#dc2626;font-size:18px'>●</span>")
            else:
                chunks.append("<span style='color:#ffffff;font-size:18px'>●</span>")
        return " ".join(chunks)

    def _ensure_states(self, student_id: str):
        if student_id not in self.question_states:
            count = self.total_questions if self.total_questions > 0 else 1
            self.question_states[student_id] = ["unanswered"] * count

    def _set_circles(self, row: int, html: str):
        label = QLabel()
        label.setTextFormat(Qt.RichText)
        label.setText(html)
        label.setWordWrap(True)
        label.setStyleSheet("background:#1f2937; border-radius:6px; padding:4px; color:white;")
        self.table.setCellWidget(row, 3, label)

    def request_login_for_students(self):
        try:
            response = self.api.request_login(self.student_ids)
            if int(response.get("target_count", 0)) == 0:
                self._show_error("لا يوجد طلاب متصلون حاليا لاستقبال تسجيل الدخول")
            else:
                for sid in self.student_ids:
                    row = self._get_row(sid)
                    self._set(row, 2, "Waiting student login...")
        except Exception as ex:
            self._show_error(str(ex))

    def start_exam_for_students(self):
        if self.session_started and self.session_id:
            self._join_ready_students_to_running_session()
            return
        target_ids = [sid for sid in self.student_ids if sid in self.login_ready_students]
        if not target_ids:
            self._show_error("لا يمكن بدء الامتحان قبل تسجيل الطلاب أسماءهم")
            return
        try:
            response = self.api.start_exam(self.exam_id, self.duration_minutes, target_ids)
            if int(response.get("target_count", 0)) == 0:
                self._show_error("لم يتم إرسال الامتحان لأي طالب")
                return
            self.student_ids = target_ids
            self.session_id = response.get("session_id", "")
            self.session_started = True
            self.started_student_ids.update(target_ids)
            self.remaining_seconds = self.duration_minutes * 60
            self.session_label.setText(f"Session: {self.session_id}")
            self.time_label.setText(f"Time Left: {self._format_seconds(self.remaining_seconds)}")
            if not self.timer.isActive():
                self.timer.start(1000)
            waiting_ids = [sid for sid in self.student_ids if sid not in self.started_student_ids]
            for sid in waiting_ids:
                row = self._get_row(sid)
                self._set(row, 2, "Waiting login to join running exam")
        except Exception as ex:
            self._show_error(str(ex))

    def _join_ready_students_to_running_session(self):
        target_ids = [
            sid for sid in self.student_ids if sid in self.login_ready_students and sid not in self.started_student_ids
        ]
        if not target_ids:
            self.statusBar().showMessage("لا يوجد طلاب جاهزون للانضمام حاليا", 3000)
            return
        try:
            response = self.api.join_exam_session(self.session_id, target_ids)
            if int(response.get("target_count", 0)) == 0:
                self.statusBar().showMessage("لا يوجد طلاب متصلون للانضمام", 3000)
                return
            self.started_student_ids.update(target_ids)
            for sid in target_ids:
                row = self._get_row(sid)
                self._set(row, 2, "Joining running exam...")
        except Exception as ex:
            self._show_error(str(ex))

    def finish_exam_for_students(self):
        confirm = QMessageBox.question(
            self,
            "Finish Test",
            "هل تريد إنهاء الامتحان الآن لجميع الطلاب؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        target_ids = list(self.student_ids)
        try:
            response = self.api.stop_exam(target_ids)
            if int(response.get("target_count", 0)) == 0:
                self._show_error("لم يتم إنهاء الامتحان لأي طالب")
                return
            self.session_started = False
            if self.timer.isActive():
                self.timer.stop()
            self.time_label.setText("Time Left: 00:00")
            for sid in target_ids:
                row = self._get_row(sid)
                self._set(row, 2, "Finished by tutor")
            self.statusBar().showMessage("تم إنهاء الامتحان لجميع الطلاب", 4000)
        except Exception as ex:
            self._show_error(str(ex))

    def _format_seconds(self, total_seconds: int) -> str:
        safe_seconds = max(int(total_seconds), 0)
        minutes = safe_seconds // 60
        seconds = safe_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def _tick_timer(self):
        if not self.session_started:
            return
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
        self.time_label.setText(f"Time Left: {self._format_seconds(self.remaining_seconds)}")
        if self.remaining_seconds <= 0 and self.timer.isActive():
            self.timer.stop()

    def _show_error(self, msg: str):
        dialog = QDialog(self)
        dialog.setWindowTitle("خطأ")
        ly = QVBoxLayout(dialog)
        ly.addWidget(QLabel(msg))
        btn = QPushButton("إغلاق")
        btn.setStyleSheet("QPushButton{background:#ef4444;}")
        btn.clicked.connect(dialog.accept)
        ly.addWidget(btn)
        dialog.exec_()

    def _maybe_show_summary(self):
        if self.summary_opened:
            return
        tracked_ids = list(self.started_student_ids) if self.started_student_ids else list(self.student_ids)
        if not tracked_ids:
            return
        if not all(sid in self.submitted_students for sid in tracked_ids):
            return
        self.summary_opened = True
        dialog = ExamSummaryDialog(self)
        for sid in tracked_ids:
            stats = self.final_stats.get(sid, {})
            dialog.add_row(
                student_name=stats.get("student_name", sid),
                answered=str(stats.get("answered_count", 0)),
                correct=str(stats.get("correct_count", 0)),
                wrong=str(stats.get("wrong_count", 0)),
                result=f"{stats.get('score', 0)}/{stats.get('total_grade', 0)}",
            )
        dialog.exec_()

    def handle_event(self, event: dict):
        event_type = event.get("type")
        payload = event.get("payload", {})
        if event_type != "student_login" and self.session_id and payload.get("session_id") != self.session_id:
            return
        if event_type == "student_login":
            sid = payload.get("student_id", "")
            row = self._get_row(sid)
            self._set(row, 1, self._clean_login_name(payload.get("student_name", "")))
            self._set(row, 2, "Student entered name")
            self._set(row, 3, "Remaining")
            self.login_ready_students.add(sid)
            if self.session_started and self.session_id and sid in self.student_ids and sid not in self.started_student_ids:
                try:
                    response = self.api.join_exam_session(self.session_id, [sid])
                    if int(response.get("target_count", 0)) > 0:
                        self.started_student_ids.add(sid)
                        self._set(row, 2, "Joining running exam...")
                except Exception:
                    pass
            return
        if event_type == "exam_session_started":
            self.total_questions = int(payload.get("total_questions", self.total_questions or 0))
            self.session_id = payload.get("session_id", self.session_id)
            self.session_started = True
            self.session_label.setText(f"Session: {self.session_id}")
            self.remaining_seconds = int(payload.get("duration_minutes", self.duration_minutes)) * 60
            if payload.get("remaining_seconds") is not None:
                self.remaining_seconds = int(payload.get("remaining_seconds"))
            self.time_label.setText(f"Time Left: {self._format_seconds(self.remaining_seconds)}")
            if not self.timer.isActive():
                self.timer.start(1000)
            for sid in self.student_ids:
                self._ensure_states(sid)
                row = self._get_row(sid)
                self._set_circles(row, self._render_circles(self.question_states[sid]))
            return
        row = self._get_row(payload.get("student_id", ""))
        student_id = payload.get("student_id", "")
        self._set(row, 1, self._clean_login_name(payload.get("student_name")) or student_id)
        if payload.get("total_questions") and not self.total_questions:
            self.total_questions = int(payload.get("total_questions"))
        self._ensure_states(student_id)

        if event_type == "exam_started":
            self.started_student_ids.add(student_id)
            self._set(row, 2, "Started")
            incoming_remaining = payload.get("remaining_seconds")
            if incoming_remaining is not None:
                self.remaining_seconds = int(incoming_remaining)
                self.time_label.setText(f"Time Left: {self._format_seconds(self.remaining_seconds)}")
            self._set_circles(row, self._render_circles(self.question_states[student_id]))
        elif event_type == "exam_progress":
            self._set(row, 2, "In progress")
            incoming_remaining = payload.get("remaining_seconds")
            if incoming_remaining is not None:
                self.remaining_seconds = int(incoming_remaining)
                self.time_label.setText(f"Time Left: {self._format_seconds(self.remaining_seconds)}")
            idx = max(int(payload.get("current_question", 1)) - 1, 0)
            if idx < len(self.question_states[student_id]):
                if payload.get("selected_answer") is None:
                    self.question_states[student_id][idx] = "unanswered"
                elif payload.get("is_correct"):
                    self.question_states[student_id][idx] = "correct"
                else:
                    self.question_states[student_id][idx] = "wrong"
            self._set_circles(row, self._render_circles(self.question_states[student_id]))
        elif event_type == "exam_submitted":
            self._set(row, 2, "Finished")
            answers = payload.get("answers", [])
            for ans in answers:
                idx = max(int(ans.get("question_index", 1)) - 1, 0)
                if idx < len(self.question_states[student_id]):
                    if ans.get("skipped"):
                        self.question_states[student_id][idx] = "unanswered"
                    elif ans.get("is_correct"):
                        self.question_states[student_id][idx] = "correct"
                    else:
                        self.question_states[student_id][idx] = "wrong"
            self._set_circles(row, self._render_circles(self.question_states[student_id]))
            self.final_stats[student_id] = {
                "student_name": payload.get("student_name", student_id),
                "answered_count": payload.get("answered_count", 0),
                "correct_count": payload.get("correct_count", 0),
                "wrong_count": payload.get("wrong_count", 0),
                "score": payload.get("score", 0),
                "total_grade": payload.get("total_grade", 0),
            }
            self.submitted_students.add(student_id)
            tracked_ids = list(self.started_student_ids) if self.started_student_ids else list(self.student_ids)
            if tracked_ids and all(sid in self.submitted_students for sid in tracked_ids):
                self.session_started = False
                if self.timer.isActive():
                    self.timer.stop()
                self.time_label.setText("Time Left: 00:00")
            self._maybe_show_summary()


class ExamSummaryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("نتيجة الامتحان")
        self.resize(900, 500)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("ملخص نتائج الطلاب"))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["الطالب", "أجاب", "صح", "خطأ", "النتيجة"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        close_btn = QPushButton("إغلاق")
        close_btn.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close_btn)
        layout.addLayout(row)
        self.setLayoutDirection(Qt.RightToLeft)

    def add_row(self, student_name: str, answered: str, correct: str, wrong: str, result: str):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(student_name)))
        self.table.setItem(row, 1, QTableWidgetItem(str(answered)))
        self.table.setItem(row, 2, QTableWidgetItem(str(correct)))
        self.table.setItem(row, 3, QTableWidgetItem(str(wrong)))
        self.table.setItem(row, 4, QTableWidgetItem(str(result)))
