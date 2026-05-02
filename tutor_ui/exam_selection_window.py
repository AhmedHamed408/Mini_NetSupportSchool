# Hero header + Card with exam QComboBox and duration QSpinBox (QFormLayout).
from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)


class ExamSelectionDialog(QDialog):
    def __init__(self, exams: List[dict], students: List[dict], parent=None):
        super().__init__(parent)
        self.exams = exams
        self.students = students
        self.result_payload = None
        self.setWindowTitle("اختيار الامتحان")
        self.resize(760, 680)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        hero = QFrame()
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(16, 14, 16, 14)
        title = QLabel("إعداد جلسة الامتحان")
        hint = QLabel("اختر الامتحان والمدة وحدد الطلاب ثم اضغط بدء الامتحان")
        hero_layout.addWidget(title)
        hero_layout.addWidget(hint)
        layout.addWidget(hero)

        config_card = QFrame()
        config_layout = QVBoxLayout(config_card)
        config_layout.setContentsMargins(12, 12, 12, 12)
        config_layout.setSpacing(10)
        section = QLabel("إعدادات الامتحان")
        config_layout.addWidget(section)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.exam_combo = QComboBox()
        for exam in self.exams:
            self.exam_combo.addItem(f"{exam.get('title')} ({exam.get('exam_id')})", exam)
        form.addRow("الامتحان:", self.exam_combo)

        self.duration_input = QSpinBox()
        self.duration_input.setRange(1, 300)
        self.duration_input.setValue(30)
        form.addRow("المدة (دقيقة):", self.duration_input)

        config_layout.addLayout(form)
        layout.addWidget(config_card)

        self.setLayout(layout)
