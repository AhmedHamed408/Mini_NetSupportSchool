import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import urlencode

import qtawesome as qta
import websockets
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


# PERSON 4 OWNERSHIP (student exam runtime side):
# Student navigation, answer tracking, submit, and realtime progress updates.
class ExamWindow(QMainWindow):
    def __init__(self, payload: dict, stop_signal_path: str = ""):
        super().__init__()
        self.payload = payload
        self.session_id = payload["session_id"]
        self.exam_id = payload["exam_id"]
        self.exam_title = payload.get("exam_title", payload["exam_id"])
        self.duration_minutes = int(payload.get("duration_minutes", 30))
        self.questions = payload["exam"]["questions"]
        self.student_id = payload["student_id"]
        self.student_name = payload["student_name"]
        self.server_url = payload["server_url"]
        self.stop_signal_path = Path(stop_signal_path) if stop_signal_path else None
        self.current_index = 0
        self.answers = [None] * len(self.questions)
        self.remaining_seconds = int(payload.get("remaining_seconds", self.duration_minutes * 60))
        self.loop = asyncio.new_event_loop()
        self.prev_btn = None
        self.next_btn = None
        self.first_btn = None
        self.last_btn = None
        self._build_ui()
        self._load_question()
        self._notify_started()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def _build_ui(self):
        self.setWindowTitle("وضع الامتحان")
        self.showFullScreen()
        self.showMaximized()
        self.setWindowFlags(self.windowFlags() | Qt.CustomizeWindowHint)

        root = QWidget()
        root.setStyleSheet(
            """
            QWidget { background-color: #eef2ff; font-size: 16px; }
            QLabel#TitleLabel { font-size: 30px; font-weight: bold; color: #111827; }
            QLabel#TimerLabel { font-size: 24px; font-weight: bold; color: #b91c1c; }
            QLabel#ProgressLabel { font-size: 18px; color: #374151; }
            QLabel#StatsLabel {
                font-size: 15px;
                color: #1e3a8a;
                background: #dbeafe;
                border-radius: 10px;
                padding: 8px 10px;
            }
            QLabel#QuestionLabel {
                background: white; border-radius: 12px; padding: 18px;
                font-size: 22px; font-weight: 600; color: #111827;
            }
            QLineEdit {
                background: white; border: 1px solid #d1d5db; border-radius: 8px;
                padding: 10px; font-size: 16px;
            }
            QRadioButton {
                background: white; border: 1px solid #e5e7eb; border-radius: 10px;
                padding: 12px; margin-top: 8px;
            }
            QPushButton {
                color: white; border-radius: 10px; padding: 10px 18px; font-weight: bold;
                min-width: 54px;
                max-width: 54px;
                min-height: 46px;
            }
            QPushButton#PrevBtn { background: #6b7280; }
            QPushButton#NextBtn { background: #2563eb; }
            QPushButton#SubmitBtn { background: #16a34a; }
            QPushButton#FirstBtn, QPushButton#LastBtn { background: #7c3aed; }
            QPushButton:hover { opacity: 0.9; }
            QFrame#Panel {
                background: #ffffff;
                border: 1px solid #dbeafe;
                border-radius: 14px;
            }
            QListWidget {
                background: #ffffff;
                border: 1px solid #dbeafe;
                border-radius: 12px;
                padding: 6px;
            }
            QListWidget::item {
                margin: 4px 0;
                border-radius: 8px;
                padding: 8px;
            }
            QListWidget::item:selected { background: #bfdbfe; color: #1e3a8a; }
            """
        )
        layout = QGridLayout(root)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(12)

        side_panel = QFrame()
        side_panel.setObjectName("Panel")
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(12, 12, 12, 12)
        side_layout.setSpacing(8)
        side_title = QLabel("حالة الأسئلة")
        side_title.setStyleSheet("font-size:18px; font-weight:700; color:#1f2937;")
        side_layout.addWidget(side_title)
        self.stats_label = QLabel("")
        self.stats_label.setObjectName("StatsLabel")
        side_layout.addWidget(self.stats_label)
        self.questions_status_list = QListWidget()
        self.questions_status_list.itemClicked.connect(self._jump_from_list)
        side_layout.addWidget(self.questions_status_list)
        layout.addWidget(side_panel, 0, 0, 4, 1)

        main_panel = QFrame()
        main_panel.setObjectName("Panel")
        main_layout = QVBoxLayout(main_panel)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(10)
        self.title_label = QLabel(self.exam_title)
        self.title_label.setObjectName("TitleLabel")
        self.timer_label = QLabel("")
        self.timer_label.setObjectName("TimerLabel")
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("ProgressLabel")
        main_layout.addWidget(self.title_label)
        main_layout.addWidget(self.timer_label)
        main_layout.addWidget(self.progress_label)

        self.question_label = QLabel("")
        self.question_label.setObjectName("QuestionLabel")
        self.question_label.setWordWrap(True)
        main_layout.addWidget(self.question_label)

        self.options_group = QButtonGroup(self)
        self.option_buttons = []
        for _ in range(4):
            rb = QRadioButton("")
            self.options_group.addButton(rb)
            self.option_buttons.append(rb)
            main_layout.addWidget(rb)

        actions = QHBoxLayout()
        self.first_btn = QPushButton("")
        self.first_btn.setObjectName("FirstBtn")
        self.first_btn.setIcon(qta.icon("fa5s.angle-double-right", color="white"))
        self.first_btn.setToolTip("أول سؤال")
        self.prev_btn = QPushButton("")
        self.prev_btn.setObjectName("PrevBtn")
        self.prev_btn.setIcon(qta.icon("fa5s.chevron-right", color="white"))
        self.prev_btn.setToolTip("السابق")
        self.next_btn = QPushButton("")
        self.next_btn.setObjectName("NextBtn")
        self.next_btn.setIcon(qta.icon("fa5s.chevron-left", color="white"))
        self.next_btn.setToolTip("التالي")
        self.last_btn = QPushButton("")
        self.last_btn.setObjectName("LastBtn")
        self.last_btn.setIcon(qta.icon("fa5s.angle-double-left", color="white"))
        self.last_btn.setToolTip("آخر سؤال")
        submit_btn = QPushButton("")
        submit_btn.setObjectName("SubmitBtn")
        submit_btn.setIcon(qta.icon("fa5s.paper-plane", color="white"))
        submit_btn.setToolTip("تسليم الامتحان")
        self.first_btn.clicked.connect(self._first_question)
        self.prev_btn.clicked.connect(self._prev_question)
        self.next_btn.clicked.connect(self._next_question)
        self.last_btn.clicked.connect(self._last_question)
        submit_btn.clicked.connect(self._submit)
        actions.addWidget(self.first_btn)
        actions.addWidget(self.prev_btn)
        actions.addWidget(self.next_btn)
        actions.addWidget(self.last_btn)
        actions.addWidget(submit_btn)
        main_layout.addLayout(actions)
        layout.addWidget(main_panel, 0, 1, 4, 3)
        self.setCentralWidget(root)
        self.setLayoutDirection(Qt.RightToLeft)

    def closeEvent(self, event):
        event.ignore()

    def _tick(self):
        if self.stop_signal_path and self.stop_signal_path.exists():
            try:
                self.stop_signal_path.unlink(missing_ok=True)
            except Exception:
                pass
            self._submit()
            return
        self.remaining_seconds -= 1
        self._save_current_answer()
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        self.timer_label.setText(f"الوقت المتبقي: {minutes:02d}:{seconds:02d}")
        if self.remaining_seconds <= 0:
            self._submit()

    def _load_question(self):
        q = self.questions[self.current_index]
        self.question_label.setText(f"س{self.current_index + 1}: {q['question']}")
        self.progress_label.setText(
            f"السؤال {self.current_index + 1} من {len(self.questions)}"
        )
        self.options_group.setExclusive(False)
        for i, rb in enumerate(self.option_buttons):
            if i < len(q["options"]):
                option = q["options"][i]
                rb.setVisible(True)
                rb.setText(option)
                rb.setChecked(self.answers[self.current_index] == option)
            else:
                rb.setVisible(False)
                rb.setText("")
                rb.setChecked(False)
        self.options_group.setExclusive(True)
        self._refresh_questions_panel()
        self._refresh_nav_buttons()

    def _save_current_answer(self):
        selected = None
        for rb in self.option_buttons:
            if rb.isChecked():
                selected = rb.text()
                break
        self.answers[self.current_index] = selected
        self._send_progress_for_current(selected)

    def _prev_question(self):
        self._save_current_answer()
        if self.current_index > 0:
            self.current_index -= 1
            self._load_question()

    def _next_question(self):
        self._save_current_answer()
        if self.current_index < len(self.questions) - 1:
            self.current_index += 1
            self._load_question()

    def _first_question(self):
        self._save_current_answer()
        self.current_index = 0
        self._load_question()

    def _last_question(self):
        self._save_current_answer()
        self.current_index = len(self.questions) - 1
        self._load_question()

    def _refresh_nav_buttons(self):
        is_first = self.current_index == 0
        is_last = self.current_index == len(self.questions) - 1
        self.first_btn.setEnabled(not is_first)
        self.prev_btn.setEnabled(not is_first)
        self.next_btn.setEnabled(not is_last)
        self.last_btn.setEnabled(not is_last)

    def _refresh_questions_panel(self):
        answered = sum(1 for a in self.answers if a is not None)
        remaining = len(self.answers) - answered
        self.stats_label.setText(f"✅ المنجزة: {answered}    🕓 المتبقية: {remaining}")
        self.questions_status_list.blockSignals(True)
        self.questions_status_list.clear()
        for idx in range(len(self.questions)):
            done = self.answers[idx] is not None
            icon = "✅" if done else "🕓"
            item = QListWidgetItem(f"{icon} السؤال {idx + 1}")
            self.questions_status_list.addItem(item)
        self.questions_status_list.setCurrentRow(self.current_index)
        self.questions_status_list.blockSignals(False)

    def _jump_from_list(self, item):
        self._save_current_answer()
        row = self.questions_status_list.row(item)
        if row >= 0:
            self.current_index = row
            self._load_question()

    def _calc_stats(self):
        answered_count = sum(1 for a in self.answers if a is not None)
        unanswered_count = len(self.answers) - answered_count
        correct_count = 0
        wrong_count = 0
        result_answers = []
        for i, q in enumerate(self.questions):
            selected = self.answers[i]
            correct = q["correct_answer"]
            is_correct = selected == correct if selected is not None else False
            if selected is None:
                pass
            elif is_correct:
                correct_count += 1
            else:
                wrong_count += 1
            result_answers.append(
                {
                    "question_index": i + 1,
                    "question_text": q["question"],
                    "selected_answer": selected,
                    "correct_answer": correct,
                    "is_correct": is_correct,
                    "skipped": selected is None,
                }
            )
        return {
            "answered_count": answered_count,
            "unanswered_count": unanswered_count,
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "answers": result_answers,
        }

    def _send_progress_for_current(self, selected):
        q = self.questions[self.current_index]
        stats = self._calc_stats()
        payload = {
            "type": "exam_progress",
            "payload": {
                "session_id": self.session_id,
                "exam_id": self.exam_id,
                "exam_title": self.exam_title,
                "current_question": self.current_index + 1,
                "selected_answer": selected,
                "correct_answer": q["correct_answer"],
                "is_correct": selected == q["correct_answer"] if selected else False,
                "remaining_seconds": self.remaining_seconds,
                **stats,
            },
        }
        self._send_ws_message(payload)

    def _notify_started(self):
        payload = {
            "type": "exam_started",
            "payload": {
                "session_id": self.session_id,
                "exam_id": self.exam_id,
                "exam_title": self.exam_title,
                "total_questions": len(self.questions),
                "remaining_seconds": self.remaining_seconds,
            },
        }
        self._send_ws_message(payload)

    def _submit(self):
        self.timer.stop()
        self._save_current_answer()
        stats = self._calc_stats()
        payload = {
            "type": "exam_submitted",
            "payload": {
                "session_id": self.session_id,
                "exam_id": self.exam_id,
                "exam_title": self.exam_title,
                "duration_minutes": self.duration_minutes,
                "score": stats["correct_count"],
                "total_grade": len(self.questions),
                **stats,
            },
        }
        self._send_ws_message(payload)
        QMessageBox.information(self, "انتهى الامتحان", "تم تسليم الامتحان")
        QApplication.quit()

    def _ws_url(self):
        params = urlencode(
            {
                "student_name": self.student_name,
                "machine_name": self.payload["machine_name"],
            }
        )
        return f"{self.server_url}/ws/student-events/{self.student_id}?{params}"

    async def _send_async(self, message: dict):
        ws_url = self._ws_url().replace("http://", "ws://").replace("https://", "wss://")
        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps(message, ensure_ascii=False))

    def _send_ws_message(self, message: dict):
        try:
            self.loop.run_until_complete(self._send_async(message))
        except Exception:
            # Keep the exam window running even if transient socket error happens.
            pass


def main():
    payload_path = sys.argv[1]
    stop_signal_path = sys.argv[2] if len(sys.argv) > 2 else ""
    payload = json.loads(open(payload_path, "r", encoding="utf-8").read())
    app = QApplication(sys.argv)
    window = ExamWindow(payload, stop_signal_path=stop_signal_path)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
