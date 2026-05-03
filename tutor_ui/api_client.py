from typing import Dict, List, Optional

import requests


class TutorApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: Dict):
        return requests.post(f"{self.base_url}{path}", json=payload, timeout=5)

    def list_students(self) -> List[Dict]:
        response = requests.get(f"{self.base_url}/students", timeout=5)
        response.raise_for_status()
        return response.json().get("students", [])

    def list_exams(self) -> List[Dict]:
        response = requests.get(f"{self.base_url}/exams", timeout=5)
        response.raise_for_status()
        return response.json().get("exams", [])

    def lock(self, student_ids: Optional[List[str]] = None):
        response = self._post("/lock", {"student_ids": student_ids or []})
        response.raise_for_status()
        return response.json()

    def unlock(self, student_ids: Optional[List[str]] = None):
        response = self._post("/unlock", {"student_ids": student_ids or []})
        response.raise_for_status()
        return response.json()

    def start_exam(self, exam_id: str, duration_minutes: int, student_ids: Optional[List[str]] = None):
        response = self._post(
            "/start-exam",
            {
                "student_ids": student_ids or [],
                "exam_id": exam_id,
                "duration_minutes": duration_minutes,
            },
        )
        response.raise_for_status()
        return response.json()

    def request_login(self, student_ids: Optional[List[str]] = None):
        response = self._post("/request-login", {"student_ids": student_ids or []})
        response.raise_for_status()
        return response.json()

    def stop_exam(self, student_ids: Optional[List[str]] = None):
        response = self._post("/stop-exam", {"student_ids": student_ids or []})
        response.raise_for_status()
        return response.json()

    def join_exam_session(self, session_id: str, student_ids: Optional[List[str]] = None):
        response = self._post(
            "/join-exam-session",
            {
                "session_id": session_id,
                "student_ids": student_ids or [],
            },
        )
        response.raise_for_status()
        return response.json()

    def list_results(self) -> List[Dict]:
        response = requests.get(f"{self.base_url}/results", timeout=5)
        response.raise_for_status()
        return response.json().get("results", [])

    def reports_history(self) -> List[Dict]:
        response = requests.get(f"{self.base_url}/reports/history", timeout=5)
        response.raise_for_status()
        return response.json().get("history", [])

    def report_exam_details(self, exam_title: str, exam_date: str) -> List[Dict]:
        response = requests.get(
            f"{self.base_url}/reports/exam-details",
            params={"exam_title": exam_title, "exam_date": exam_date},
            timeout=5,
        )
        response.raise_for_status()
        return response.json().get("rows", [])

    def save_exam(self, exam_id: str, title: str, duration_minutes: int, exam: Dict):
        response = self._post(
            "/exams",
            {
                "exam_id": exam_id,
                "title": title,
                "duration_minutes": duration_minutes,
                "exam": exam,
            },
        )
        response.raise_for_status()
        return response.json()
