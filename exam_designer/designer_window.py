import uuid

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame,
    QFormLayout,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tutor_ui.api_client import TutorApiClient


class ExamDesignerWindow(QMainWindow):
    def __init__(self, api: TutorApiClient, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("إنشاء امتحان")
        self.resize(1100, 700)
        self.questions = []
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        root.setStyleSheet(
            """
            QWidget { background:#f8fafc; font-size:14px; }
            QFrame#Card { background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; }
            QLabel#Title { font-size:22px; font-weight:700; color:#0f172a; }
            QLabel#Section { font-size:16px; font-weight:700; color:#1e293b; }
            QLineEdit, QSpinBox {
                background:white;
                border:1px solid #cbd5e1;
                border-radius:10px;
                min-height:34px;
                padding:4px 8px;
            }
            QTableWidget {
                background:white;
                border:1px solid #dbe3ef;
                border-radius:10px;
                gridline-color:#edf2f7;
                selection-background-color:#dbeafe;
            }
            QPushButton {
                color:white;
                border:none;
                border-radius:10px;
                min-height:38px;
                font-weight:700;
                padding:6px 12px;
            }
            """
        )
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)
        title = QLabel("إنشاء امتحان")
        title.setObjectName("Title")
        layout.addWidget(title)

        header_card = QFrame()
        header_card.setObjectName("Card")
        header_shadow = QGraphicsDropShadowEffect()
        header_shadow.setBlurRadius(18)
        header_shadow.setYOffset(3)
        header_shadow.setColor(QColor(15, 23, 42, 35))
        header_card.setGraphicsEffect(header_shadow)
        header_layout = QVBoxLayout(header_card)
        form = QFormLayout()

        self.exam_title = QLineEdit()
        self.duration = QSpinBox()
        self.duration.setRange(1, 300)
        self.duration.setValue(30)
        form.addRow("عنوان الامتحان:", self.exam_title)
        form.addRow("المدة (دقيقة):", self.duration)
        header_layout.addLayout(form)
        layout.addWidget(header_card)

        add_title = QLabel("إضافة سؤال جديد")
        add_title.setObjectName("Section")
        layout.addWidget(add_title)
        form_card = QFrame()
        form_card.setObjectName("Card")
        form_shadow = QGraphicsDropShadowEffect()
        form_shadow.setBlurRadius(18)
        form_shadow.setYOffset(3)
        form_shadow.setColor(QColor(15, 23, 42, 30))
        form_card.setGraphicsEffect(form_shadow)
        form_layout = QVBoxLayout(form_card)
        self.question_input = QLineEdit()
        self.correct_input = QLineEdit()
        self.wrong_1 = QLineEdit()
        self.wrong_2 = QLineEdit()
        self.wrong_3 = QLineEdit()

        qf = QFormLayout()
        qf.addRow("السؤال:", self.question_input)
        qf.addRow("الإجابة الصحيحة:", self.correct_input)
        qf.addRow("إجابة خاطئة 1:", self.wrong_1)
        qf.addRow("إجابة خاطئة 2:", self.wrong_2)
        qf.addRow("إجابة خاطئة 3:", self.wrong_3)
        form_layout.addLayout(qf)

        actions = QHBoxLayout()
        add_btn = QPushButton("إضافة السؤال")
        save_btn = QPushButton("حفظ الامتحان")
        add_btn.setStyleSheet("QPushButton{background:#0ea5e9;} QPushButton:hover{background:#0284c7;}")
        save_btn.setStyleSheet("QPushButton{background:#22c55e;} QPushButton:hover{background:#16a34a;}")
        add_btn.clicked.connect(self.add_question)
        save_btn.clicked.connect(self.save_exam)
        actions.addWidget(add_btn)
        actions.addWidget(save_btn)
        form_layout.addLayout(actions)
        layout.addWidget(form_card)

        self.questions_table = QTableWidget(0, 2)
        self.questions_table.setHorizontalHeaderLabels(["السؤال", "الإجابة الصحيحة"])
        layout.addWidget(self.questions_table)

        self.setCentralWidget(root)
        self.setLayoutDirection(Qt.RightToLeft)

    def add_question(self):
        question = self.question_input.text().strip()
        correct = self.correct_input.text().strip()
        wrongs = [self.wrong_1.text().strip(), self.wrong_2.text().strip(), self.wrong_3.text().strip()]
        if not question or not correct or any(not w for w in wrongs):
            QMessageBox.warning(self, "تنبيه", "الرجاء إدخال جميع بيانات السؤال")
            return
        options = [correct, *wrongs]
        self.questions.append(
            {
                "question": question,
                "options": options,
                "correct_answer": correct,
            }
        )
        row = self.questions_table.rowCount()
        self.questions_table.insertRow(row)
        self.questions_table.setItem(row, 0, QTableWidgetItem(question))
        self.questions_table.setItem(row, 1, QTableWidgetItem(correct))
        for w in [self.question_input, self.correct_input, self.wrong_1, self.wrong_2, self.wrong_3]:
            w.clear()

    def save_exam(self):
        title = self.exam_title.text().strip()
        if not title or not self.questions:
            QMessageBox.warning(self, "تنبيه", "أدخل عنوانا وأضف سؤالا واحدا على الأقل")
            return
        exam_id = f"exam-{uuid.uuid4().hex[:8]}"
        exam_payload = {
            "exam_id": exam_id,
            "title": title,
            "duration_minutes": int(self.duration.value()),
            "questions": self.questions,
        }
        try:
            self.api._post(
                "/exams",
                {
                    "exam_id": exam_id,
                    "title": title,
                    "duration_minutes": int(self.duration.value()),
                    "exam": exam_payload,
                },
            ).raise_for_status()
            QMessageBox.information(self, "نجاح", "تم حفظ الامتحان")
            self.questions.clear()
            self.questions_table.setRowCount(0)
        except Exception as ex:
            QMessageBox.warning(self, "خطأ", str(ex))
