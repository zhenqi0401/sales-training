"""AI question generation service backed by an OpenAI-compatible chat API."""

import asyncio
import base64
import json
import mimetypes
import re
import subprocess
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.video_processing import resolve_video_tool

SUPPORTED_TYPES = ("single", "multiple", "true_false")
DIFFICULTY_TO_SCORE = {"L1": 1, "L2": 3, "L3": 5}
DIFFICULTY_LABELS = {"L1": "基础理解", "L2": "场景应用", "L3": "综合判断"}


class AIQuestionGenerationError(RuntimeError):
    """Raised when the configured LLM cannot return usable question drafts."""


async def transcribe_video(video_file_url: str) -> str:
    """Reserved hook for a future video content extraction provider."""
    _ = resolve_upload_path(video_file_url)
    return ""


async def call_question_llm(prompt: dict[str, Any]) -> list[dict[str, Any]]:
    """Call Bailian's OpenAI-compatible chat completion API."""
    if not settings.ai_api_key:
        raise AIQuestionGenerationError("AI_API_KEY 未配置，无法调用大模型生成题目")

    payload = build_chat_completion_payload(prompt)
    response = await asyncio.to_thread(
        _post_chat_completion,
        payload,
        settings.ai_request_timeout_seconds,
    )
    content = extract_message_content(response)
    if not content:
        raise AIQuestionGenerationError("大模型返回空响应，请稍后重试或调整生成内容")

    questions = parse_questions_from_content(content)
    if not questions:
        raise AIQuestionGenerationError("大模型未返回题目，请补充视频文本或知识点后重试")
    return questions


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
    user_requirements: str | None = None,
    product_knowledge: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Generate reviewable question drafts without persisting them."""
    if not (video_file_url or "").strip():
        raise AIQuestionGenerationError("视频文件地址为空，无法读取视频内容生成题目")

    user_requirements_text = (user_requirements or "").strip()
    knowledge_points = [item.strip() for item in (knowledge_points or []) if item.strip()]
    product_knowledge = product_knowledge or []
    question_types = expand_question_types(question_type_ratios, count)
    difficulty = DIFFICULTY_TO_SCORE.get(difficulty_level, 3)

    prompt = {
        "video": {"id": video_id, "title": video_title, "file_url": video_file_url},
        "user_requirements": user_requirements_text,
        "product_category_id": product_category_id,
        "knowledge_points": knowledge_points,
        "product_knowledge": product_knowledge,
        "count": count,
        "difficulty_level": difficulty_level,
        "difficulty_label": DIFFICULTY_LABELS.get(difficulty_level, "场景应用"),
        "question_types": question_types,
        "schema": {
            "questions": [
                {
                    "content": "题干",
                    "type": "single|multiple|true_false",
                    "options": {"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"},
                    "answer": "A 或 A,B",
                    "analysis": "解析说明",
                    "tags": ["标签"],
                }
            ]
        },
    }

    llm_questions = await call_question_llm(prompt)
    if not llm_questions:
        raise AIQuestionGenerationError("大模型未返回题目，请补充视频文本或知识点后重试")
    normalized = [
        normalize_generated_question(
            item,
            fallback_type=question_types[index % len(question_types)],
            difficulty=difficulty,
            category_id=category_id,
            video_id=video_id,
            fallback_tags=build_tags(video_title, difficulty_level, knowledge_points, user_requirements_text),
        )
        for index, item in enumerate(llm_questions[:count])
    ]
    normalized = [item for item in normalized if item["content"] and item["answer"]]
    if not normalized:
        raise AIQuestionGenerationError("大模型返回内容格式无效，未生成可审核题目")
    return normalized


def build_chat_completion_payload(prompt: dict[str, Any]) -> dict[str, Any]:
    count = int(prompt.get("count") or 5)
    question_types = prompt.get("question_types") or ["single"]
    system_prompt = (
        "你是销售培训系统的题库生成助手。必须只输出 JSON，不要输出 Markdown。"
        "JSON 顶层字段必须是 questions。题型只允许 single、multiple、true_false。"
        "single 和 true_false 的 answer 只能是单个选项字母；multiple 的 answer 使用逗号分隔选项字母。"
        "题目必须严格依据随消息提供的视频画面内容和音频讲解生成。"
        "user_requirements 只是出题角度建议，不能作为事实依据，不能覆盖或补充视频中不存在的事实。"
        "如果建议与视频内容或音频讲解冲突，必须忽略建议。"
        "每道题的题干、正确答案和解析都必须能从视频画面或音频讲解中直接得到支撑。"
    )
    system_prompt += (
        "单选题只能使用 A/B/C/D 中的一个作为 answer。"
        "多选题只能使用 A/B/C/D，多个答案用英文逗号分隔。"
        "true_false 只能使用 A 或 B，A=正确，B=错误，禁止返回 C 或 D。"
        "analysis 必须和题目及答案严格对应，明确写出视频中的证据时间段（如 19:32-19:36），"
        "并逐项说明每个选项正确或错误的原因；判断题也必须说明该陈述为何正确或错误。"
    )
    text_prompt = {
        "task": "为管理员生成待审核题目草稿",
        "requirements": {
            "count": count,
            "difficulty": prompt.get("difficulty_level"),
            "difficulty_label": prompt.get("difficulty_label"),
            "question_types_in_order": question_types,
            "option_labels": ["A", "B", "C", "D"],
            "true_false_options": {"A": "正确", "B": "错误"},
            "analysis_rule": "解析必须逐项对应选项，并引用视频画面或音频讲解的时间段证据。",
        },
        "context": {
            "video": prompt.get("video") or {},
            "knowledge_points": prompt.get("knowledge_points") or [],
            "user_requirements": truncate_text(prompt.get("user_requirements") or "", 1000),
            "product_knowledge": prompt.get("product_knowledge") or [],
        },
        "output_schema": prompt.get("schema"),
    }
    video = prompt.get("video") or {}
    return {
        "model": settings.ai_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "video_url",
                        "video_url": build_video_url_payload(str(video.get("file_url") or "")),
                        "fps": settings.ai_video_fps,
                    },
                    {"type": "text", "text": json.dumps(text_prompt, ensure_ascii=False)},
                ],
            },
        ],
        "temperature": 0.2,
        "max_tokens": min(4096, max(1024, count * 450)),
        "stream": True,
        "modalities": ["text"],
    }


def build_video_url_payload(file_url: str) -> dict[str, Any]:
    file_url = file_url.strip()
    if not file_url:
        raise AIQuestionGenerationError("视频文件地址为空，无法读取视频内容生成题目")

    if file_url.startswith(("http://", "https://", "data:")):
        url = file_url
        if url.startswith("data:") and len(url) > settings.ai_video_max_data_url_chars:
            raise AIQuestionGenerationError(
                "Base64 视频超过百炼 Qwen-Omni 10MB 限制，请使用 /uploads 本地视频由系统压缩，或配置公网视频 URL"
            )
    else:
        video_path = resolve_upload_path(file_url)
        if video_path is None:
            raise AIQuestionGenerationError("视频文件地址不是可访问 URL，也不是 /uploads 本地文件")
        if not video_path.exists():
            raise AIQuestionGenerationError(f"视频文件不存在：{file_url}")
        max_bytes = max(1, int(settings.ai_video_max_inline_mb)) * 1024 * 1024
        size = video_path.stat().st_size
        if size > max_bytes:
            raise AIQuestionGenerationError(
                f"视频文件过大，当前内联上限为 {settings.ai_video_max_inline_mb}MB，请配置可公网访问的视频 URL 或调高上限"
            )
        mime_type = mimetypes.guess_type(video_path.name)[0] or "video/mp4"
        encoded = base64.b64encode(video_path.read_bytes()).decode("ascii")
        url = f"data:{mime_type};base64,{encoded}"
        if len(url) > settings.ai_video_max_data_url_chars:
            url = build_compressed_video_data_url(video_path)

    return {"url": url}


def build_compressed_video_data_url(video_path: Path) -> str:
    upload_root = Path(settings.upload_dir)
    cache_dir = upload_root / "ai-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{video_path.stem}.omni-audio.ai.mp4"
    if not cache_path.exists() or cache_path.stat().st_mtime < video_path.stat().st_mtime:
        compress_video_for_ai(video_path, cache_path)

    mime_type = mimetypes.guess_type(cache_path.name)[0] or "video/mp4"
    encoded = base64.b64encode(cache_path.read_bytes()).decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded}"
    if len(data_url) > settings.ai_video_max_data_url_chars:
        raise AIQuestionGenerationError(
            "视频压缩后仍超过百炼 Qwen-Omni Base64 10MB 限制，请配置可公网访问的视频 URL 或上传更短的视频"
        )
    return data_url


def compress_video_for_ai(source_path: Path, output_path: Path) -> None:
    ffmpeg = resolve_video_tool("ffmpeg")
    if not ffmpeg:
        raise AIQuestionGenerationError(
            "本地视频超过百炼接口大小限制，且 ffmpeg 未安装，无法自动生成 AI 识别压缩版视频"
        )

    tmp_path = output_path.with_name(f"{output_path.stem}.tmp{output_path.suffix}")
    tmp_path.unlink(missing_ok=True)
    max_width = max(160, int(settings.ai_video_compress_max_width))
    crf = min(45, max(28, int(settings.ai_video_compress_crf)))
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(source_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-vf",
        f"scale='min({max_width},iw)':-2:force_original_aspect_ratio=decrease,"
        f"fps=fps={max(1, int(settings.ai_video_fps))}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        str(crf),
        "-c:a",
        "aac",
        "-b:a",
        settings.ai_video_compress_audio_bitrate,
        "-ac",
        "1",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(tmp_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if result.returncode != 0:
        tmp_path.unlink(missing_ok=True)
        stderr_tail = (result.stderr or "")[-500:]
        raise AIQuestionGenerationError(f"AI 识别视频压缩失败：{stderr_tail}")
    tmp_path.replace(output_path)


def _post_chat_completion(payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any] | str:
    url = f"{settings.ai_base_url.rstrip('/')}/chat/completions"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.ai_api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            text = response.read().decode("utf-8")
            if payload.get("stream"):
                return text
            return json.loads(text)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise AIQuestionGenerationError(f"大模型接口返回错误：HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise AIQuestionGenerationError(f"无法连接大模型接口：{exc.reason}") from exc
    except TimeoutError as exc:
        raise AIQuestionGenerationError("大模型请求超时，请稍后重试") from exc
    except json.JSONDecodeError as exc:
        raise AIQuestionGenerationError("大模型接口返回了无法解析的响应") from exc


def extract_message_content(response: dict[str, Any] | str) -> str:
    if isinstance(response, str):
        return extract_stream_message_content(response)
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content") or message.get("reasoning_content") or ""
    if isinstance(content, list):
        return "".join(str(item.get("text") or item.get("content") or "") for item in content)
    return str(content).strip()


def extract_stream_message_content(stream_text: str) -> str:
    chunks: list[str] = []
    for raw_line in stream_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if not data or data == "[DONE]":
            continue
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        for choice in payload.get("choices") or []:
            delta = choice.get("delta") or {}
            content = delta.get("content")
            if isinstance(content, list):
                chunks.extend(str(item.get("text") or item.get("content") or "") for item in content)
            elif content:
                chunks.append(str(content))
    return "".join(chunks).strip()


def parse_questions_from_content(content: str) -> list[dict[str, Any]]:
    cleaned = strip_json_fence(content)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise AIQuestionGenerationError("大模型返回内容不是有效 JSON")
        payload = json.loads(match.group(0))

    if isinstance(payload, list):
        questions = payload
    else:
        questions = payload.get("questions") if isinstance(payload, dict) else None
    if not isinstance(questions, list):
        raise AIQuestionGenerationError("大模型返回 JSON 缺少 questions 数组")
    return [item for item in questions if isinstance(item, dict)]


def strip_json_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def truncate_text(text: str, max_chars: int) -> str:
    text = text.strip()
    return text if len(text) <= max_chars else text[:max_chars]


def resolve_upload_path(file_url: str) -> Path | None:
    """Resolve /uploads URLs to local files when possible."""
    prefix = "/uploads/"
    if not file_url.startswith(prefix):
        return None
    return Path(settings.upload_dir) / file_url.removeprefix(prefix)


def expand_question_types(ratios: dict[str, int], count: int) -> list[str]:
    """Expand type ratios/weights into a deterministic list of question types."""
    weights = {type_: max(0, int(ratios.get(type_, 0) or 0)) for type_ in SUPPORTED_TYPES}
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
    options = normalize_options(item.get("options"), q_type)
    answer = normalize_answer(item.get("answer"), q_type)
    validate_answer_for_options(answer, q_type, options)
    return {
        "content": str(item.get("content") or item.get("question") or "").strip(),
        "type": q_type,
        "options": options,
        "answer": answer,
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
        return ",".join(str(item).strip() for item in answer if str(item).strip())
    if answer is None and q_type == "true_false":
        return "A"
    return str(answer or "A").strip()


def validate_answer_for_options(answer: str, q_type: str, options: dict[str, str] | None) -> None:
    labels = set((options or {}).keys())
    if q_type == "true_false":
        labels = {"A", "B"}

    answers = [item.strip() for item in answer.split(",") if item.strip()]
    invalid = [item for item in answers if item not in labels]
    if invalid:
        if q_type == "true_false":
            raise AIQuestionGenerationError("判断题答案只能是 A/B，A=正确，B=错误")
        raise AIQuestionGenerationError(
            f"AI 返回的答案不在选项范围内：{','.join(invalid)}"
        )


def build_tags(
    video_title: str,
    difficulty_level: str,
    knowledge_points: list[str],
    user_requirements: str | None,
) -> list[str]:
    counter = Counter(["产品知识", difficulty_level, video_title])
    if user_requirements:
        counter[user_requirements.strip()] += 1
    for point in knowledge_points:
        counter[point] += 1
    return [tag for tag in counter if tag]
