# v2: Add main layout structure with sidebar and content area
import sys

import qtawesome as qta
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
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
        content.addStretch()

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())