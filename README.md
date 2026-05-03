# Net Support School (Simplified)

## 1) System Architecture Diagram (Text)

```text
                        +-----------------------------+
                        |        Tutor UI (PyQt5)     |
                        |  - Dashboard                |
                        |  - Lock/Unlock/Start Exam   |
                        +--------------+--------------+
                                       |
                                 HTTP REST API
                                       |
                    +------------------v------------------+
                    |       FastAPI Backend Server        |
                    | - Student registry (SQLite)         |
                    | - Exams + results store             |
                    | - Command dispatcher                |
                    | - UDP discovery listener            |
                    +---------+--------------------+------+
                              |                    |
                     WebSocket commands      SQLite database
                              |                    |
                   +----------v---------+      +---v------------------+
                   | Student Client #1  |      | students/exams/results|
                   | Student Client #N  |      +-----------------------+
                   | - heartbeat         |
                   | - lock/unlock       |
                   | - exam mode         |
                   +---------------------+

      Exam Designer (CLI) ---> JSON files ---> POST /exams (or preload sample JSON)
```

## 2) Folder Structure

```text
backend/
  main.py
  database.py
  discovery.py
  ws_manager.py
student_client/
  service.py
  exam_session.py
  install_service_windows.ps1
exam_designer/
  designer.py
  designer_window.py
  sample_exam.json
tutor_ui/
  api_client.py
  exam_selection_window.py
  exam_monitor_window.py
  reports_window.py
  ws_client.py
reports/
  report_printer.py
tutor_ui.py
requirements.txt
```

## 3) Run

```bash
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
python student_client/service.py
python tutor_ui.py
```
