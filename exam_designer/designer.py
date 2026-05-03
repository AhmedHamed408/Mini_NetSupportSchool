import json
import uuid
from pathlib import Path


def ask_question(index: int):
    print(f"\nالسؤال رقم {index + 1}")
    question = input("نص السؤال: ").strip()
    options = []
    for i in range(4):
        options.append(input(f"الخيار {i + 1}: ").strip())
    correct_answer = int(input("رقم الإجابة الصحيحة (1-4): ").strip()) - 1
    return {
        "question": question,
        "options": options,
        "correct_answer": correct_answer,
    }


def main():
    print("Exam Designer (MCQ)")
    title = input("عنوان الامتحان: ").strip()
    duration = int(input("مدة الامتحان بالدقائق: ").strip())
    count = int(input("عدد الأسئلة: ").strip())

    questions = [ask_question(i) for i in range(count)]
    exam = {
        "exam_id": f"exam-{uuid.uuid4().hex[:8]}",
        "title": title,
        "duration_minutes": duration,
        "questions": questions,
    }

    out_dir = Path(__file__).resolve().parent
    file_path = out_dir / f"{exam['exam_id']}.json"
    file_path.write_text(json.dumps(exam, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nتم حفظ الامتحان في: {file_path}")


if __name__ == "__main__":
    main()
