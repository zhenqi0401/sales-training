"""AI question generation service (stub).

This module provides a placeholder implementation for AI-powered question
generation. It returns templated questions instead of real AI output.
Replace the stub with an actual LLM call (e.g. OpenAI, local model) when
the AI backend is ready.
"""

from typing import Optional


async def generate_questions(
    topic: str,
    count: int = 5,
    difficulty: int = 2,
    question_types: list[str] | None = None,
    category_id: Optional[int] = None,
) -> list[dict]:
    """Generate questions on a given topic using AI (stub).

    Parameters
    ----------
    topic : str
        The topic or knowledge point to generate questions about.
    count : int
        Number of questions to generate (default 5).
    difficulty : int
        Difficulty level 1-5 (default 2).
    question_types : list[str] | None
        Allowed question types (default: single, multiple, true_false).
    category_id : int | None
        Optional category ID to assign.

    Returns
    -------
    list[dict]
        List of question dicts ready for ORM insertion.
    """
    if question_types is None:
        question_types = ["single", "multiple", "true_false"]

    questions = []
    type_cycle = question_types * (count // len(question_types) + 1)

    for i in range(count):
        q_type = type_cycle[i]
        question = {
            "content": f"关于「{topic}」的第{i + 1}题（{q_type}，难度{difficulty}）",
            "type": q_type,
            "options": {
                "A": "选项A",
                "B": "选项B",
                "C": "选项C",
                "D": "选项D",
            } if q_type in ("single", "multiple") else {
                "true": "正确",
                "false": "错误",
            } if q_type == "true_false" else None,
            "answer": "A" if q_type in ("single", "multiple", "true_false") else "示例答案",
            "analysis": "这是AI生成的答案解析（占位内容）",
            "difficulty": difficulty,
            "category_id": category_id,
            "source": "ai",
            "tags": [topic, f"难度{difficulty}"],
            "is_active": True,
        }
        questions.append(question)

    return questions
