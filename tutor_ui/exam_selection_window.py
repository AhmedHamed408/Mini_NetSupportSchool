from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QFrame,
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
        self.setStyleSheet(
            """
            QWidget { background:#eef2f7; color:#0f172a; font-size:14px; }
            QFrame#Hero {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #1e3a8a, stop:1 #2563eb);
                border-radius:16px;
            }
            QLabel#HeroTitle {
                font-size:24px;
                font-weight:900;
                color:white;
                background: transparent;
            }
            QLabel#HeroHint {
                color:#dbeafe;
                font-size:13px;
                background: transparent;
            }
            QFrame#Card { background:#ffffff; border:1px solid #dbeafe; border-radius:14px; }
            QLabel#SectionTitle { font-size:16px; font-weight:800; color:#1e293b; }
            QLabel#Badge {
                background:#f8fafc; border:1px solid #dbeafe; border-radius:10px;
                padding:6px 10px; font-size:12px; font-weight:700; color:#1d4ed8;
            }
            QComboBox, QSpinBox, QListWidget {
                background:#ffffff;
                border:1px solid #cbd5e1;
                border-radius:10px;
                padding:6px 8px;
            }
            QListWidget { padding:8px; }
            QListWidget::item { margin:4px 0; border-radius:10px; }
            QCheckBox {
                padding: 6px 0;
                font-weight:700;
                color:#0f172a;
            }
            QLabel#StudentName { font-size:14px; font-weight:800; color:#0f172a; }
            QLabel#MachineName { font-size:12px; color:#64748b; }
            QPushButton {
                border:none;
                border-radius:10px;
                min-height:40px;
                padding:8px 14px;
                font-weight:700;
                color:#ffffff;
            }
            QPushButton#StartBtn { background:#16a34a; }
            QPushButton#StartBtn:hover { background:#15803d; }
            QPushButton#CancelBtn { background:#64748b; }
            QPushButton#CancelBtn:hover { background:#475569; }
            QPushButton#GhostBtn {
                background:#f1f5f9;
                border:1px solid #cbd5e1;
                color:#334155;
                min-height:34px;
            }
            QPushButton#GhostBtn:hover { background:#e2e8f0; }
            QLabel#OnlineTag {
                background:#dcfce7;
                color:#15803d;
                border:1px solid #86efac;
                border-radius:9px;
                padding:2px 8px;
                font-size:11px;
                font-weight:800;
            }
            QLabel#OfflineTag {
                background:#fee2e2;
                color:#b91c1c;
                border:1px solid #fecaca;
                border-radius:9px;
                padding:2px 8px;
                font-size:11px;
                font-weight:800;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        hero = QFrame()
        hero.setObjectName("Hero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(16, 14, 16, 14)
        title = QLabel("إعداد جلسة الامتحان")
        title.setObjectName("HeroTitle")
        hint = QLabel("اختر الامتحان والمدة وحدد الطلاب ثم اضغط بدء الامتحان")
        hint.setObjectName("HeroHint")
        hero_layout.addWidget(title)
        hero_layout.addWidget(hint)
        layout.addWidget(hero)

        config_card = QFrame()
        config_card.setObjectName("Card")
        config_layout = QVBoxLayout(config_card)
        config_layout.setContentsMargins(12, 12, 12, 12)
        config_layout.setSpacing(10)
        config_layout.addWidget(self._section_title("إعدادات الامتحان"))
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
        students_card.setObjectName("Card")
        students_card_layout = QVBoxLayout(students_card)
        students_card_layout.setContentsMargins(12, 12, 12, 12)
        students_card_layout.setSpacing(10)
        top_row = QHBoxLayout()
        top_row.addWidget(self._section_title("قائمة الطلاب"))
        top_row.addStretch()
        self.total_badge = QLabel("")
        self.total_badge.setObjectName("Badge")
        self.online_badge = QLabel("")
        self.online_badge.setObjectName("Badge")
        top_row.addWidget(self.total_badge)
        top_row.addWidget(self.online_badge)
        students_card_layout.addLayout(top_row)

        filters = QHBoxLayout()
        self.select_all_btn = QPushButton("تحديد الكل")
        self.select_all_btn.setObjectName("GhostBtn")
        self.select_online_btn = QPushButton("تحديد المتصلين")
        self.select_online_btn.setObjectName("GhostBtn")
        self.clear_btn = QPushButton("إلغاء التحديد")
        self.clear_btn.setObjectName("GhostBtn")
        self.select_all_btn.clicked.connect(lambda: self._set_all_students_checked(True))
        self.select_online_btn.clicked.connect(self._set_online_students_checked)
        self.clear_btn.clicked.connect(lambda: self._set_all_students_checked(False))
        filters.addWidget(self.select_all_btn)
        filters.addWidget(self.select_online_btn)
        filters.addWidget(self.clear_btn)
        filters.addStretch()
        students_card_layout.addLayout(filters)

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
            is_online = student.get("status") == "online"
            checkbox.setChecked(is_online)
            checkbox.setProperty("student_id", student.get("student_id"))
            checkbox.setProperty("is_online", is_online)
            status_tag = QLabel("متصل" if is_online else "غير متصل")
            status_tag.setObjectName("OnlineTag" if is_online else "OfflineTag")
            name_label = QLabel(display_name)
            name_label.setObjectName("StudentName")
            machine_label = QLabel(machine_name or "جهاز غير معروف")
            machine_label.setObjectName("MachineName")
            identity_col = QVBoxLayout()
            identity_col.setContentsMargins(0, 0, 0, 0)
            identity_col.setSpacing(1)
            identity_col.addWidget(name_label)
            identity_col.addWidget(machine_label)
            row_layout.addWidget(checkbox)
            row_layout.addLayout(identity_col)
            row_layout.addStretch()
            row_layout.addWidget(status_tag)
            item.setSizeHint(row_widget.sizeHint())
            self.students_list.addItem(item)
            self.students_list.setItemWidget(item, row_widget)
        students_card_layout.addWidget(self.students_list)
        layout.addWidget(students_card)

        self._refresh_counters()

        actions = QHBoxLayout()
        start_btn = QPushButton("بدء")
        start_btn.setObjectName("StartBtn")
        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setObjectName("CancelBtn")
        start_btn.clicked.connect(self._start)
        cancel_btn.clicked.connect(self.reject)
        actions.addWidget(start_btn)
        actions.addWidget(cancel_btn)
        layout.addLayout(actions)
        self.setLayoutDirection(Qt.RightToLeft)

    def _section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionTitle")
        return label

    def _all_checkboxes(self) -> List[QCheckBox]:
        checkboxes = []
        for i in range(self.students_list.count()):
            widget = self.students_list.itemWidget(self.students_list.item(i))
            if not widget:
                continue
            checkbox = widget.findChild(QCheckBox)
            if checkbox:
                checkboxes.append(checkbox)
        return checkboxes

    def _set_all_students_checked(self, checked: bool):
        for checkbox in self._all_checkboxes():
            checkbox.setChecked(checked)

    def _set_online_students_checked(self):
        for checkbox in self._all_checkboxes():
            checkbox.setChecked(bool(checkbox.property("is_online")))

    def _refresh_counters(self):
        total = len(self.students)
        online = sum(1 for s in self.students if s.get("status") == "online")
        self.total_badge.setText(f"الكل: {total}")
        self.online_badge.setText(f"المتصلون: {online}")

    def _selected_student_ids(self):
        ids = []
        for checkbox in self._all_checkboxes():
            if checkbox and checkbox.isChecked():
                ids.append(checkbox.property("student_id"))
        return ids

    def _start(self):
        selected = self._selected_student_ids()
        if not selected:
            QMessageBox.warning(self, "تنبيه", "اختر طالبا واحدا على الأقل")
            return
        exam_data = self.exam_combo.currentData()
        self.result_payload = {
            "exam_id": exam_data.get("exam_id"),
            "exam_title": exam_data.get("title"),
            "duration_minutes": int(self.duration_input.value()),
            "student_ids": selected,
        }
        self.accept()
