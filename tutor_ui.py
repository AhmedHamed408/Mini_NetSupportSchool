import sys

import qtawesome as qta
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
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

from exam_designer.designer_window import ExamDesignerWindow
from tutor_ui.api_client import TutorApiClient
from tutor_ui.exam_monitor_window import ExamMonitorWindow
from tutor_ui.exam_selection_window import ExamSelectionDialog
from tutor_ui.exams_page import ExamsPageWindow
from tutor_ui.reports_window import ReportsWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api = TutorApiClient()
        self.students_cache = []
        self.exams_cache = []
        self.connected_only_mode = False
        self.monitor_windows = []
        self.reports_window = None
        self.designer_window = None
        self.exams_page_window = None
        self._build_ui()
        self.refresh_data()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(4000)

    def _build_ui(self):
        self.setWindowTitle("NetSupport School - Tutor")
        self.resize(1200, 700)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_widget.setStyleSheet(
            """
            QWidget { background-color: #f1f5f9; color: #0f172a; }
            QLabel#MainTitle { font-size: 24px; font-weight: 800; color: #0f172a; }
            QTableWidget {
                background: #ffffff;
                border: 1px solid #dbeafe;
                border-radius: 14px;
                gridline-color: #e2e8f0;
                selection-background-color: #dbeafe;
            }
            QHeaderView::section {
                background: #f8fafc;
                border: none;
                border-bottom: 1px solid #e2e8f0;
                padding: 8px;
                font-weight: 700;
            }
            """
        )
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        sidebar = QVBoxLayout()
        self.btn_exams_page = self._menu_btn("الامتحانات", "fa5s.file-alt")
        sidebar.addWidget(self.btn_exams_page)
        self.btn_reports_page = self._menu_btn("التقارير", "fa5s.chart-bar")
        self.btn_exam_designer = self._menu_btn("إنشاء امتحان", "fa5s.plus-square")
        sidebar.addWidget(self.btn_reports_page)
        sidebar.addWidget(self.btn_exam_designer)
        sidebar.addStretch()
        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setFixedWidth(230)
        sidebar_widget.setStyleSheet(
            """
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #0f2027,
                stop:1 #2c5364
            );
            """
        )

        content = QVBoxLayout()
        content.setSpacing(20)
        title = QLabel("لوحة التحكم")
        title.setObjectName("MainTitle")
        content.addWidget(title)

        cards_layout = QHBoxLayout()
        total_card, self.total_students_label = self._create_card(
            "إجمالي الطلاب", 0, "#27ae60", "fa5s.users"
        )
        connected_card, self.connected_students_label = self._create_card(
            "المتصلين", 0, "#2980b9", "fa5s.desktop"
        )
        self.btn_connected_only = QPushButton("عرض المتصلين فقط")
        self.btn_connected_only.setIcon(qta.icon("fa5s.sync", color="white"))
        self.btn_connected_only.setFixedHeight(100)
        self.btn_connected_only.setMinimumWidth(210)
        self.btn_connected_only.setStyleSheet(
            """
            QPushButton {
                background-color:#f39c12;
                color:white;
                border-radius:15px;
                font-size:15px;
                font-weight:bold;
                text-align:center;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color:#e08e0b;
            }
            """
        )
        cards_layout.addWidget(total_card)
        cards_layout.addWidget(connected_card)
        cards_layout.addWidget(self.btn_connected_only)
        content.addLayout(cards_layout)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["اسم الطالب", "الجهاز", "الحالة", "إجراء"])
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("QTableWidget { padding: 8px; alternate-background-color: #f8fafc; }")
        content.addWidget(self.table)

        actions = QHBoxLayout()
        self.btn_start = self._action_btn("بدء امتحان", "#27ae60", "fa5s.play")
        self.btn_lock = self._action_btn("قفل الأجهزة", "#2980b9", "fa5s.lock")
        self.btn_unlock = self._action_btn("فتح الأجهزة", "#e74c3c", "fa5s.unlock")
        actions.addWidget(self.btn_start)
        actions.addWidget(self.btn_lock)
        actions.addWidget(self.btn_unlock)
        content.addLayout(actions)

        self.btn_lock.clicked.connect(lambda: self.send_bulk_command("lock"))
        self.btn_unlock.clicked.connect(lambda: self.send_bulk_command("unlock"))
        self.btn_start.clicked.connect(self.open_exam_selection)
        self.btn_reports_page.clicked.connect(self.open_reports_page)
        self.btn_exam_designer.clicked.connect(self.open_exam_designer)
        self.btn_exams_page.clicked.connect(self.open_exams_page)
        self.btn_connected_only.clicked.connect(self.toggle_connected_only)

        content_widget = QWidget()
        content_widget.setLayout(content)
        main_layout.addWidget(content_widget)
        main_layout.addWidget(sidebar_widget)
        QApplication.instance().setLayoutDirection(Qt.RightToLeft)

    def _menu_btn(self, text, icon):
        btn = QPushButton(text)
        btn.setIcon(qta.icon(icon, color="white"))
        btn.setMinimumHeight(52)
        btn.setStyleSheet(
            """
            QPushButton {
                text-align: right;
                padding: 12px 14px;
                color: white;
                border: none;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.1);
            }
            """
        )
        return btn

    def _create_card(self, title, value, color, icon):
        card = QFrame()
        card.setFixedHeight(100)
        card.setStyleSheet("background-color: white; border-radius: 15px;")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 50))
        card.setGraphicsEffect(shadow)

        layout = QHBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon, color="white").pixmap(35, 35))
        icon_label.setStyleSheet(
            f"background-color:{color}; border-radius:18px; padding:8px;"
        )
        text_layout = QVBoxLayout()
        text_layout.addWidget(QLabel(title))
        value_label = QLabel(str(value))
        value_label.setStyleSheet("font-size:18px; font-weight:bold;")
        text_layout.addWidget(value_label)
        layout.addWidget(icon_label)
        layout.addLayout(text_layout)
        card.setLayout(layout)
        return card, value_label

    def _action_btn(self, text, color, icon):
        b = QPushButton(text)
        b.setIcon(qta.icon(icon, color="white"))
        b.setMinimumHeight(52)
        b.setMinimumWidth(165)
        b.setStyleSheet(
            f"""
            QPushButton {{
                background-color:{color};
                color:white;
                border-radius:12px;
                font-weight:bold;
                font-size:15px;
                padding: 8px 12px;
            }}
            """
        )
        return b

    def refresh_data(self):
        try:
            self.students_cache = self.api.list_students()
            self.exams_cache = self.api.list_exams()
            self.render_students()
            self.total_students_label.setText(str(len(self.students_cache)))
            connected = sum(1 for s in self.students_cache if s.get("status") == "online")
            self.connected_students_label.setText(str(connected))
        except Exception as ex:
            self.statusBar().showMessage(f"تعذر الاتصال بالخادم: {ex}")

    def render_students(self):
        students = self.students_cache
        if self.connected_only_mode:
            students = [s for s in self.students_cache if s.get("status") == "online"]
        self.table.setRowCount(len(students))
        for row, student in enumerate(students):
            student_name = (student.get("student_name", "") or "").strip()
            if student_name.lower() == "student demo":
                student_name = ""
            self.table.setItem(row, 0, QTableWidgetItem(student_name))
            self.table.setItem(row, 1, QTableWidgetItem(student.get("machine_name", "")))
            is_online = student.get("status") == "online"
            status_label = QLabel("● متصل" if is_online else "● غير متصل")
            status_label.setStyleSheet("color: green;" if is_online else "color: red;")
            self.table.setCellWidget(row, 2, status_label)

            action = QPushButton()
            locked = bool(student.get("locked"))
            action.setIcon(qta.icon("fa5s.unlock" if locked else "fa5s.lock", color="white"))
            action.setStyleSheet("background-color:#e67e22; border-radius:10px; padding:8px;")
            action.setProperty("student_id", student.get("student_id"))
            action.clicked.connect(self.toggle_lock_from_button)
            self.table.setCellWidget(row, 3, action)

    def toggle_connected_only(self):
        self.connected_only_mode = not self.connected_only_mode
        if self.connected_only_mode:
            self.btn_connected_only.setText("عرض كل الطلاب")
            self.statusBar().showMessage("تم تحديث القائمة: عرض المتصلين فقط", 3000)
        else:
            self.btn_connected_only.setText("عرض المتصلين فقط")
            self.statusBar().showMessage("تم تحديث القائمة: عرض كل الطلاب", 3000)
        self.refresh_data()

    def toggle_lock_from_button(self):
        sender = self.sender()
        student_id = sender.property("student_id") if sender else None
        if not student_id:
            return
        student = next((s for s in self.students_cache if s.get("student_id") == student_id), None)
        is_locked = bool(student.get("locked")) if student else False
        try:
            if is_locked:
                self.api.unlock([student_id])
            else:
                self.api.lock([student_id])
            self.refresh_data()
        except Exception as ex:
            QMessageBox.warning(self, "خطأ", str(ex))

    def send_bulk_command(self, cmd):
        try:
            if cmd == "lock":
                self.api.lock([])
            elif cmd == "unlock":
                self.api.unlock([])
            self.refresh_data()
        except Exception as ex:
            QMessageBox.warning(self, "خطأ", str(ex))

    def open_exam_selection(self):
        if not self.exams_cache:
            QMessageBox.information(self, "تنبيه", "لا يوجد امتحانات محفوظة")
            return
        dialog = ExamSelectionDialog(self.exams_cache, self.students_cache, self)
        if dialog.exec_() != dialog.Accepted:
            return
        payload = dialog.result_payload
        try:
            selected_students = [
                s for s in self.students_cache if s.get("student_id") in payload["student_ids"]
            ]
            monitor = ExamMonitorWindow(
                self.api,
                self.api.base_url,
                payload["exam_title"],
                payload["exam_id"],
                payload["duration_minutes"],
                selected_students,
                self,
            )
            monitor.show()
            self.monitor_windows.append(monitor)
        except Exception as ex:
            QMessageBox.warning(self, "خطأ", str(ex))

    def open_reports_page(self):
        self.reports_window = ReportsWindow(self.api, self)
        self.reports_window.show()

    def open_exam_designer(self):
        self.designer_window = ExamDesignerWindow(self.api, self)
        self.designer_window.show()

    def open_exams_page(self):
        self.exams_page_window = ExamsPageWindow(self.api, self)
        self.exams_page_window.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())