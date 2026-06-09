"""AI question generation service.

The ASR and LLM integrations are intentionally left as replaceable placeholders.
Wire real providers in ``transcribe_video`` and ``call_question_llm`` when the
vendor/API choice is ready.
"""

from collections import Counter
from pathlib import Path
from typing import Any

from app.core.config import settings

SUPPORTED_TYPES = ("single", "multiple", "true_false")
DIFFICULTY_TO_SCORE = {"L1": 1, "L2": 3, "L3": 5}
DIFFICULTY_LABELS = {"L1": "基础理解", "L2": "场景应用", "L3": "综合判断"}


async def transcribe_video(video_file_url: str) -> str:
    """Extract subtitles or transcribe audio from a video.

    TODO: Fill in the ASR provider here. Typical inputs are the local file path
    resolved from ``video_file_url`` or a public URL if the provider supports it.
    Return plain text transcript.
    """
    _ = resolve_upload_path(video_file_url)
    return ""


async def call_question_llm(prompt: dict[str, Any]) -> list[dict[str, Any]]:
    """Call an LLM to generate question drafts.

    TODO: Fill in the LLM provider here. The function should return a list of
    dictionaries with content/type/options/answer/analysis fields.
    """
    return []


async def generate_questions(
    *,
    video_title: str,
    video_file_url: str,
    count: int,
    difficulty_level: str,
    question_type_ratios: dict[str, int],
    category_id: int | None = None,
    video_id: int | None = None,
    product_category_id: int | None = None,
    knowledge_points: list[str] | None = None,
    topic: str | None = None,
    transcript: str | None = None,
    product_knowledge: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Generate reviewable question drafts without persisting them."""
    transcript_text = (transcript or "").strip() or await transcribe_video(video_file_url)
    knowledge_points = [item.strip() for item in (knowledge_points or []) if item.strip()]
    product_knowledge = product_knowledge or []
    question_types = expand_question_types(question_type_ratios, count)
    difficulty = DIFFICULTY_TO_SCORE.get(difficulty_level, 3)

    prompt = {
        "video": {"id": video_id, "title": video_title},
        "transcript": transcript_text,
        "topic": topic or "",
        "product_category_id": product_category_id,
        "knowledge_points": knowledge_points,
        "product_knowledge": product_knowledge,
        "count": count,
        "difficulty_level": difficulty_level,
        "question_types": question_types,
        "template": {
            "content": "题干",
            "options": {"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"},
            "answer": "正确答案",
            "analysis": "解析说明",
            "tags": ["产品知识", "销售话术", "异议处理"],
        },
    }

    llm_questions = await call_question_llm(prompt)
    if llm_questions:
        return [
            normalize_generated_question(
                item,
                fallback_type=question_types[index % len(question_types)],
                difficulty=difficulty,
                category_id=category_id,
                video_id=video_id,
                fallback_tags=build_tags(video_title, difficulty_level, knowledge_points, topic),
            )
            for index, item in enumerate(llm_questions[:count])
        ]

    return build_placeholder_questions(
        video_title=video_title,
        transcript=transcript_text,
        count=count,
        difficulty=difficulty,
        difficulty_level=difficulty_level,
        question_types=question_types,
        category_id=category_id,
        video_id=video_id,
        knowledge_points=knowledge_points,
        topic=topic,
        product_knowledge=product_knowledge,
    )


def resolve_upload_path(file_url: str) -> Path | None:
    """Resolve /uploads URLs to local files when possible."""
    prefix = "/uploads/"
    if not file_url.startswith(prefix):
        return None
    return Path(settings.upload_dir) / file_url.removeprefix(prefix)


def expand_question_types(ratios: dict[str, int], count: int) -> list[str]:
    """Expand type ratios/weights into a deterministic list of question types."""
    weights = {
        type_: max(0, int(ratios.get(type_, 0) or 0))
        for type_ in SUPPORTED_TYPES
    }
    if not any(weights.values()):
        weights = {"single": 60, "multiple": 30, "true_false": 10}

    raw_counts = {
        type_: int(count * weight / sum(weights.values()))
        for type_, weight in weights.items()
    }
    remaining = count - sum(raw_counts.values())
    for type_, _weight in sorted(weights.items(), key=lambda item: item[1], reverse=True):
        if remaining <= 0:
            break
        raw_counts[type_] += 1
        remaining -= 1

    result: list[str] = []
    for type_ in SUPPORTED_TYPES:
        result.extend([type_] * raw_counts[type_])
    return result[:count] or ["single"]


def normalize_generated_question(
    item: dict[str, Any],
    *,
    fallback_type: str,
    difficulty: int,
    category_id: int | None,
    video_id: int | None,
    fallback_tags: list[str],
) -> dict[str, Any]:
    q_type = item.get("type") if item.get("type") in SUPPORTED_TYPES else fallback_type
    return {
        "content": str(item.get("content") or item.get("question") or "").strip(),
        "type": q_type,
        "options": normalize_options(item.get("options"), q_type),
        "answer": normalize_answer(item.get("answer"), q_type),
        "analysis": str(item.get("analysis") or item.get("explanation") or "").strip(),
        "difficulty": int(item.get("difficulty") or difficulty),
        "category_id": item.get("category_id") or category_id,
        "video_id": item.get("video_id") or video_id,
        "source": "ai",
        "tags": item.get("tags") if isinstance(item.get("tags"), list) else fallback_tags,
    }


def normalize_options(options: Any, q_type: str) -> dict[str, str] | None:
    if q_type == "true_false":
        return {"A": "正确", "B": "错误"}
    if q_type not in ("single", "multiple"):
        return None
    if isinstance(options, dict):
        return {str(key): str(value) for key, value in options.items()}
    return {"A": "", "B": "", "C": "", "D": ""}


def normalize_answer(answer: Any, q_type: str) -> str:
    if isinstance(answer, list):
        return ",".join(str(item) for item in answer)
    if answer is None and q_type == "true_false":
        return "A"
    return str(answer or "A")


def build_placeholder_questions(
    *,
    video_title: str,
    transcript: str,
    count: int,
    difficulty: int,
    difficulty_level: str,
    question_types: list[str],
    category_id: int | None,
    video_id: int | None,
    knowledge_points: list[str],
    topic: str | None,
    product_knowledge: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return runnable template data until real ASR/LLM providers are configured."""
    tags = build_tags(video_title, difficulty_level, knowledge_points, topic)
    context = summarize_context(transcript, product_knowledge, topic)
    questions = []

    for index in range(count):
        q_type = question_types[index % len(question_types)]
        point = knowledge_points[index % len(knowledge_points)] if knowledge_points else "课程核心知识点"
        label = DIFFICULTY_LABELS.get(difficulty_level, "场景应用")
        content = f"基于视频《{video_title}》的{label}要求，关于“{point}”，以下说法哪一项最合适？"
        options = {
            "A": f"结合客户需求讲清{point}的价值",
            "B": "只强调价格优惠，避免解释产品特点",
            "C": "客户提出疑问时直接结束推荐",
            "D": "忽略视频中的产品知识点",
        }
        answer = "A"
        if q_type == "multiple":
            content = f"基于视频《{video_title}》，关于“{point}”的销售表达，哪些做法更合理？"
            options = {
                "A": f"围绕{point}解释客户收益",
                "B": "结合产品知识库内容补充证据",
                "C": "不确认客户需求就直接推荐",
                "D": "面对异议时回到场景和价值说明",
            }
            answer = "A,B,D"
        elif q_type == "true_false":
            content = f"视频《{video_title}》中涉及“{point}”时，销售人员应结合客户场景和产品知识库进行说明。"
            options = {"A": "正确", "B": "错误"}
            answer = "A"

        questions.append(
            {
                "content": f"{content}（AI占位草稿 {index + 1}）",
                "type": q_type,
                "options": options,
                "answer": answer,
                "analysis": f"占位解析：题目依据视频内容、产品知识库与生成配置生成。当前上下文摘要：{context}",
                "difficulty": difficulty,
                "category_id": category_id,
                "video_id": video_id,
                "source": "ai",
                "tags": tags,
            }
        )
    return questions


def summarize_context(transcript: str, product_knowledge: list[dict[str, Any]], topic: str | None) -> str:
    pieces = []
    if topic:
        pieces.append(topic.strip())
    if transcript:
        pieces.append(transcript.strip()[:80])
    if product_knowledge:
        names = [str(item.get("name") or item.get("title")) for item in product_knowledge[:3]]
        pieces.append("、".join(name for name in names if name))
    return "；".join(pieces) or "待接入 ASR/LLM 后由真实视频转写与知识库生成"


def build_tags(
    video_title: str,
    difficulty_level: str,
    knowledge_points: list[str],
    topic: str | None,
) -> list[str]:
    counter = Counter(["产品知识", difficulty_level, video_title])
    if topic:
        counter[topic.strip()] += 1
    for point in knowledge_points:
        counter[point] += 1
    return [tag for tag in counter if tag]
