# Students Card — QListWidget rows with QCheckBox + name/machine labels per student.
from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
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

        students_card = QFrame()
        students_card_layout = QVBoxLayout(students_card)
        students_card_layout.setContentsMargins(12, 12, 12, 12)
        students_card_layout.setSpacing(10)
        students_card_layout.addWidget(QLabel("قائمة الطلاب"))

        self.students_list = QListWidget()
        self.students_list.setAlternatingRowColors(True)
        for student in self.students:
            item = QListWidgetItem(self.students_list)
            row_widget = QWidget()
            row_widget.setMinimumHeight(52)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(10, 6, 10, 6)
            row_layout.setSpacing(10)
            display_name = (student.get("student_name") or "").strip() or "بدون اسم"
            machine_name = student.get("machine_name", "")
            checkbox = QCheckBox("")
            checkbox.setChecked(False)
            checkbox.setProperty("student_id", student.get("student_id"))
            name_label = QLabel(display_name)
            machine_label = QLabel(machine_name or "جهاز غير معروف")
            identity_col = QVBoxLayout()
            identity_col.setContentsMargins(0, 0, 0, 0)
            identity_col.setSpacing(1)
            identity_col.addWidget(name_label)
            identity_col.addWidget(machine_label)
            row_layout.addWidget(checkbox)
            row_layout.addLayout(identity_col)
            row_layout.addStretch()
            item.setSizeHint(row_widget.sizeHint())
            self.students_list.addItem(item)
            self.students_list.setItemWidget(item, row_widget)

        students_card_layout.addWidget(self.students_list)
        layout.addWidget(students_card)

        self.setLayout(layout)
