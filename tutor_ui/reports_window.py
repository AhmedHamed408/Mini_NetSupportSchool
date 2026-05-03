from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
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

from reports.report_printer import print_html_report
from tutor_ui.api_client import TutorApiClient


class ReportsWindow(QMainWindow):
    def __init__(self, api: TutorApiClient, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("التقارير")
        self.resize(1000, 650)
        self._build_ui()
        self.load_history()

    def _build_ui(self):
        root = QWidget()
        root.setStyleSheet(
            """
            QWidget { background:#f1f5f9; color:#0f172a; }
            QFrame#Card { background:#ffffff; border:1px solid #dbeafe; border-radius:14px; }
            QLabel#MainTitle { font-size:24px; font-weight:800; color:#0f172a; }
            QLabel#SectionTitle { font-size:17px; font-weight:700; color:#1e293b; }
            QTableWidget {
                background:#ffffff;
                border:1px solid #dbeafe;
                border-radius:12px;
                gridline-color:#e2e8f0;
                selection-background-color:#dbeafe;
                alternate-background-color:#f8fafc;
            }
            QHeaderView::section {
                background:#f8fafc;
                border:none;
                border-bottom:1px solid #e2e8f0;
                padding:8px;
                font-weight:700;
            }
            QPushButton {
                background:#2563eb;
                color:white;
                border:none;
                border-radius:10px;
                min-height:40px;
                padding:8px 16px;
                font-weight:700;
            }
            QPushButton:hover { background:#1d4ed8; }
            """
        )
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        title = QLabel("التقارير")
        title.setObjectName("MainTitle")
        layout.addWidget(title)

        history_card = QFrame()
        history_card.setObjectName("Card")
        history_layout = QVBoxLayout(history_card)
        history_layout.setContentsMargins(12, 12, 12, 12)
        history_layout.setSpacing(8)
        history_title = QLabel("سجل الامتحانات السابقة")
        history_title.setObjectName("SectionTitle")
        history_layout.addWidget(history_title)

        self.history_table = QTableWidget(0, 4)
        self.history_table.setHorizontalHeaderLabels(
            ["اسم الامتحان", "التاريخ", "عدد الطلاب", "متوسط النسبة"]
        )
        self.history_table.setAlternatingRowColors(True)
        self.history_table.itemSelectionChanged.connect(self.load_details)
        history_layout.addWidget(self.history_table)
        layout.addWidget(history_card)

        details_card = QFrame()
        details_card.setObjectName("Card")
        details_layout = QVBoxLayout(details_card)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setSpacing(8)
        details_title = QLabel("تفاصيل الطلاب")
        details_title.setObjectName("SectionTitle")
        details_layout.addWidget(details_title)
        self.details_table = QTableWidget(0, 7)
        self.details_table.setHorizontalHeaderLabels(
            ["الطالب", "الدرجة", "النسبة", "الحالة", "أجاب", "صح", "خطأ"]
        )
        self.details_table.setAlternatingRowColors(True)
        details_layout.addWidget(self.details_table)
        layout.addWidget(details_card)

        actions = QHBoxLayout()
        print_btn = QPushButton("Print Report")
        print_btn.clicked.connect(self.print_report)
        actions.addStretch()
        actions.addWidget(print_btn)
        layout.addLayout(actions)

        self.setCentralWidget(root)
        self.setLayoutDirection(Qt.RightToLeft)

    def load_history(self):
        try:
            rows = self.api.reports_history()
            self.history_table.setRowCount(len(rows))
            if not rows:
                self.statusBar().showMessage("لا توجد نتائج محفوظة حتى الآن", 5000)
            for r, row in enumerate(rows):
                self.history_table.setItem(r, 0, QTableWidgetItem(str(row.get("exam_title", ""))))
                self.history_table.setItem(r, 1, QTableWidgetItem(str(row.get("exam_date", ""))))
                self.history_table.setItem(r, 2, QTableWidgetItem(str(row.get("students_count", 0))))
                self.history_table.setItem(
                    r, 3, QTableWidgetItem(f"{float(row.get('avg_percentage', 0)):.2f}%")
                )
        except Exception as ex:
            QMessageBox.warning(self, "خطأ", str(ex))

    def load_details(self):
        row = self.history_table.currentRow()
        if row < 0:
            return
        exam_title = self.history_table.item(row, 0).text()
        exam_date = self.history_table.item(row, 1).text()
        try:
            rows = self.api.report_exam_details(exam_title, exam_date)
            self.details_table.setRowCount(len(rows))
            for r, item in enumerate(rows):
                self.details_table.setItem(r, 0, QTableWidgetItem(str(item.get("student_name", ""))))
                self.details_table.setItem(
                    r,
                    1,
                    QTableWidgetItem(f"{item.get('score', 0)}/{item.get('total_grade', 0)}"),
                )
                self.details_table.setItem(r, 2, QTableWidgetItem(f"{float(item.get('percentage', 0)):.2f}%"))
                status_text = "ناجح" if item.get("result_status") == "passed" else "راسب"
                self.details_table.setItem(r, 3, QTableWidgetItem(status_text))
                self.details_table.setItem(r, 4, QTableWidgetItem(str(item.get("answered_count", 0))))
                self.details_table.setItem(r, 5, QTableWidgetItem(str(item.get("correct_count", 0))))
                self.details_table.setItem(r, 6, QTableWidgetItem(str(item.get("wrong_count", 0))))
        except Exception as ex:
            QMessageBox.warning(self, "خطأ", str(ex))

    def print_report(self):
        row = self.history_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "تنبيه", "اختر امتحان من السجل")
            return
        exam_title = self.history_table.item(row, 0).text()
        exam_date = self.history_table.item(row, 1).text()
        rows = self.api.report_exam_details(exam_title, exam_date)
        html = "<table border='1' cellspacing='0' cellpadding='6'><tr><th>الطالب</th><th>الدرجة</th><th>النسبة</th><th>أجاب</th><th>صح</th><th>خطأ</th><th>النتيجة</th></tr>"
        for item in rows:
            status_text = "ناجح" if item.get("result_status") == "passed" else "راسب"
            html += (
                "<tr>"
                f"<td>{item.get('student_name','')}</td>"
                f"<td>{item.get('score',0)}/{item.get('total_grade',0)}</td>"
                f"<td>{float(item.get('percentage',0)):.2f}%</td>"
                f"<td>{item.get('answered_count',0)}</td>"
                f"<td>{item.get('correct_count',0)}</td>"
                f"<td>{item.get('wrong_count',0)}</td>"
                f"<td>{status_text}</td>"
                "</tr>"
            )
        html += "</table>"
        print_html_report(self, f"{exam_title} - {exam_date}", html)
