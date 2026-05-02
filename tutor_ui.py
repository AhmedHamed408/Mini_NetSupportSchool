#  Add exam configuration action section (start/lock/unlock)
import sys

import qtawesome as qta
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from tutor_ui.api_client import TutorApiClient
from tutor_ui.exam_selection_window import ExamSelectionDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api = TutorApiClient()
        self.students_cache = []
        self.exams_cache = []
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle("NetSupport School - Tutor")
        self.resize(1200, 700)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        sidebar = QVBoxLayout()
        self.btn_exams_page = self._menu_btn("الامتحانات", "fa5s.file-alt")
        self.btn_reports_page = self._menu_btn("التقارير", "fa5s.chart-bar")
        self.btn_exam_designer = self._menu_btn("إنشاء امتحان", "fa5s.plus-square")
        sidebar.addWidget(self.btn_exams_page)
        sidebar.addWidget(self.btn_reports_page)
        sidebar.addWidget(self.btn_exam_designer)
        sidebar.addStretch()

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setFixedWidth(230)

        content = QVBoxLayout()
        title = QLabel("لوحة التحكم")
        content.addWidget(title)

        actions = QHBoxLayout()
        self.btn_start = self._action_btn("بدء امتحان", "#27ae60", "fa5s.play")
        self.btn_lock = self._action_btn("قفل الأجهزة", "#2980b9", "fa5s.lock")
        self.btn_unlock = self._action_btn("فتح الأجهزة", "#e74c3c", "fa5s.unlock")
        actions.addWidget(self.btn_start)
        actions.addWidget(self.btn_lock)
        actions.addWidget(self.btn_unlock)
        content.addLayout(actions)
        content.addStretch()

        self.btn_lock.clicked.connect(lambda: self.send_bulk_command("lock"))
        self.btn_unlock.clicked.connect(lambda: self.send_bulk_command("unlock"))
        self.btn_start.clicked.connect(self.open_exam_selection)

        content_widget = QWidget()
        content_widget.setLayout(content)

        main_layout.addWidget(content_widget)
        main_layout.addWidget(sidebar_widget)

        QApplication.instance().setLayoutDirection(Qt.RightToLeft)

    def _menu_btn(self, text, icon):
        btn = QPushButton(text)
        btn.setIcon(qta.icon(icon, color="white"))
        btn.setMinimumHeight(52)
        return btn

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

    def send_bulk_command(self, cmd):
        try:
            if cmd == "lock":
                self.api.lock([])
            elif cmd == "unlock":
                self.api.unlock([])
        except Exception as ex:
            QMessageBox.warning(self, "خطأ", str(ex))

    def open_exam_selection(self):
        if not self.exams_cache:
            QMessageBox.information(self, "تنبيه", "لا يوجد امتحانات محفوظة")
            return
        dialog = ExamSelectionDialog(self.exams_cache, self.students_cache, self)
        dialog.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())