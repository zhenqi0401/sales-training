"""AI question generation service backed by 火山引擎方舟 Doubao (Responses API).

整体流程：视频 → ffmpeg 提取音频 → Doubao 转写（带时间戳）→ Doubao 出题。
出题 / ASR / 方法论统一走方舟 Responses API（官方 volcenginesdkarkruntime SDK）。
话术演练 Agent 仍走 chat/completions，见 practice_agent.py。
"""

import asyncio
import base64
import json
import mimetypes
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.video_processing import probe_video, resolve_video_tool

SUPPORTED_TYPES = ("single", "multiple", "true_false")
DIFFICULTY_TO_SCORE = {"L1": 1, "L2": 3, "L3": 5}
DIFFICULTY_LABELS = {"L1": "基础理解", "L2": "场景应用", "L3": "综合判断"}

# Doubao Base64 音频上限 25MB、时长 ≤120 分钟。这里压到 15MB 留足余量。
MAX_AUDIO_BYTES = 15 * 1024 * 1024


class AIQuestionGenerationError(RuntimeError):
    """Raised when the configured LLM cannot return usable question drafts."""


# ─────────────────────────── 方舟 Responses API 客户端 ───────────────────────────

_ark_client: Any = None


def _get_client() -> Any:
    """Lazily build a singleton AsyncArk client."""
    global _ark_client
    if _ark_client is None:
        try:
            from volcenginesdkarkruntime import AsyncArk
        except ImportError as exc:  # pragma: no cover - 依赖缺失时给出清晰提示
            raise AIQuestionGenerationError(
                "未安装 volcengine-python-sdk[ark]，无法调用火山方舟"
            ) from exc
        _ark_client = AsyncArk(
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
            timeout=settings.ai_request_timeout_seconds,
        )
    return _ark_client


def _extract_output_text(resp: Any) -> str:
    """Pull plain text out of a Responses API result (object or dict form)."""
    if resp is None:
        return ""
    text = getattr(resp, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    output = getattr(resp, "output", None)
    if output is None and isinstance(resp, dict):
        output = resp.get("output")

    parts: list[str] = []
    for item in output or []:
        content = getattr(item, "content", None)
        if content is None and isinstance(item, dict):
            content = item.get("content")
        for block in content or []:
            block_text = getattr(block, "text", None)
            if block_text is None and isinstance(block, dict):
                block_text = block.get("text")
            if block_text:
                parts.append(str(block_text))
    return "".join(parts).strip()


async def _call_responses(
    *,
    instructions: str,
    content: list[dict[str, Any]],
    temperature: float = 0.3,
    max_output_tokens: int | None = None,
    model: str | None = None,
) -> str:
    """Single seam for all Responses API calls — patched in tests."""
    if not settings.ai_api_key:
        raise AIQuestionGenerationError("AI_API_KEY 未配置")

    client = _get_client()
    kwargs: dict[str, Any] = {
        "model": model or settings.ai_model,
        "instructions": instructions,
        "input": [{"role": "user", "content": content}],
        "temperature": temperature,
    }
    if max_output_tokens:
        kwargs["max_output_tokens"] = max_output_tokens

    try:
        resp = await client.responses.create(**kwargs)
    except AIQuestionGenerationError:
        raise
    except Exception as exc:  # SDK / 网络 / 服务端错误统一收口
        raise AIQuestionGenerationError(f"火山方舟接口调用失败：{exc}") from exc

    return _extract_output_text(resp)


# ─────────────────────────────── 语音转写（ASR） ───────────────────────────────


async def transcribe_video_audio(video_path: Path) -> str:
    """Extract audio from video and transcribe via Doubao (Responses API).

    Returns transcript with sentence-level timestamps:
        [00:00] 第一句内容
        [00:15] 第二句内容
    """
    import logging
    logger = logging.getLogger(__name__)

    if not video_path.exists():
        raise AIQuestionGenerationError(f"视频文件不存在：{video_path}")

    ffmpeg = resolve_video_tool("ffmpeg")
    if not ffmpeg:
        raise AIQuestionGenerationError("ffmpeg 未安装，无法提取视频音频")

    audio_path = video_path.with_suffix(".asr.mp3")
    try:
        # 用 ffprobe 快速获取视频时长，预计算合适码率，避免二次编码
        try:
            meta = await asyncio.to_thread(probe_video, video_path)
            duration_sec = meta.duration
        except Exception:
            duration_sec = 0

        # 计算刚好不超过 15MB 的最大码率（留 10% 余量）
        bitrate = "24k"  # 默认
        if duration_sec > 0:
            max_bps = int((MAX_AUDIO_BYTES * 8) / duration_sec * 0.9)
            for candidate in ["64k", "48k", "32k", "24k", "16k"]:
                candidate_bps = int(candidate.replace("k", "")) * 1000
                if candidate_bps <= max_bps:
                    bitrate = candidate
                    break

        cmd = [
            ffmpeg, "-y", "-i", str(video_path),
            "-map", "0:a:0?",  # 只取音频流，跳过视频解码
            "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1",
            "-b:a", bitrate,
            str(audio_path),
        ]
        logger.info("提取音频 bitrate=%s duration=%ss", bitrate, duration_sec)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise AIQuestionGenerationError(f"音频提取失败：{(result.stderr or '')[-300:]}")

        file_size = audio_path.stat().st_size
        if file_size > MAX_AUDIO_BYTES:
            raise AIQuestionGenerationError(
                f"音频文件过大（{file_size} bytes），超过 Doubao Base64 25MB 限制，请上传更短的视频"
            )

        logger.info("正在使用 Doubao 转写 video_path=%s", video_path)
        transcript = await _call_asr_doubao(audio_path, logger)
        logger.info("ASR 转写完成 chars=%s", len(transcript))
        return transcript
    except subprocess.TimeoutExpired:
        raise AIQuestionGenerationError("音频提取超时，视频可能过长")
    finally:
        audio_path.unlink(missing_ok=True)


async def _call_asr_doubao(audio_path: Path, logger) -> str:
    """Transcribe an audio file via Doubao Responses API with per-sentence timestamps.

    Returns formatted transcript:
        [MM:SS] sentence text
    """
    mime_type = mimetypes.guess_type(audio_path.name)[0] or "audio/mpeg"
    base64_str = base64.b64encode(audio_path.read_bytes()).decode("ascii")
    data_uri = f"data:{mime_type};base64,{base64_str}"

    instructions = (
        "你是一个多语种语音识别专家，能够准确转写语音并捕捉其中的时序关系。"
        "你必须严格按用户给定的模板输出，不要输出任何无关的内容。"
    )
    template = (
        "请转录这段音频，按句子切分，每个句子单独占一行。"
        "每行格式严格为：开始秒-结束秒-句子文本。"
        "开始秒、结束秒为从音频起点起算的秒数，可保留一位小数。"
        "示例：0.0-3.2-大家好，今天讲镜片销售技巧。"
        "只输出转录结果，每行一句，不要输出任何额外说明、标题、编号或标点修饰。"
    )
    content = [
        {"type": "input_audio", "audio_url": data_uri},
        {"type": "input_text", "text": template},
    ]
    raw = await _call_responses(
        instructions=instructions,
        content=content,
        temperature=0.0,
        model=settings.ai_model,
    )
    if not raw:
        raise AIQuestionGenerationError("语音转写失败：模型返回空结果")

    transcript = _format_asr_timestamps(raw)
    if not transcript:
        raise AIQuestionGenerationError("语音转写结果为空，请确认音频包含有效语音内容")
    logger.info("Doubao ASR 转写完成 chars=%s", len(transcript))
    return transcript


_ASR_LINE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*[-–]\s*(.+?)\s*$")


def _format_asr_timestamps(raw: str) -> str:
    """Convert Doubao '{start}-{end}-{text}' lines into '[MM:SS] text' lines.

    Lines that don't match the template are kept verbatim (graceful fallback).
    """
    lines: list[str] = []
    for raw_line in raw.splitlines():
        line = raw_line.strip().rstrip(";；")
        if not line:
            continue
        match = _ASR_LINE_RE.match(line)
        if not match:
            cleaned = strip_json_fence(line)
            if cleaned:
                lines.append(cleaned)
            continue
        start = float(match.group(1))
        text = match.group(3).strip()
        if not text:
            continue
        minutes = int(start // 60)
        seconds = int(start % 60)
        lines.append(f"[{minutes:02d}:{seconds:02d}] {text}")
    return "\n".join(lines)


# ─────────────────────────────── 通用 LLM 调用 ───────────────────────────────


async def call_llm(messages: list[dict[str, str]], max_tokens: int = 1024) -> str:
    """Generic LLM call returning the assistant text (Responses API)."""
    instructions_parts: list[str] = []
    user_parts: list[str] = []
    for message in messages:
        role = message.get("role")
        text = message.get("content") or ""
        if not isinstance(text, str):
            text = str(text)
        if role == "system":
            instructions_parts.append(text)
        else:
            user_parts.append(text)

    content = [{"type": "input_text", "text": "\n".join(user_parts)}]
    return await _call_responses(
        instructions="\n".join(instructions_parts),
        content=content,
        temperature=0.3,
        max_output_tokens=max_tokens,
    )


# ─────────────────────────────── 出题 ───────────────────────────────


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
    """Generate reviewable question drafts (manual ai-generate path).

    管理员手动出题：提取视频音频 → Doubao 转写 → 基于转录稿 + 知识点/要求生成题目。
    """
    if not (video_file_url or "").strip():
        raise AIQuestionGenerationError("视频文件地址为空，无法读取视频内容生成题目")

    video_path = resolve_upload_path(video_file_url.strip())
    if video_path is None or not video_path.exists():
        raise AIQuestionGenerationError("AI 出题需要 /uploads 下的本地视频文件以提取音频")

    transcript = await transcribe_video_audio(video_path)
    if not transcript.strip():
        raise AIQuestionGenerationError("视频转录文本为空，无法生成题目")

    user_requirements_text = (user_requirements or "").strip()
    knowledge_points = [item.strip() for item in (knowledge_points or []) if item.strip()]
    product_knowledge = product_knowledge or []
    question_types = expand_question_types(question_type_ratios, count)
    difficulty = DIFFICULTY_TO_SCORE.get(difficulty_level, 3)

    system_prompt, user_prompt = build_question_prompt(
        video_title=video_title,
        transcript=transcript,
        count=count,
        difficulty_level=difficulty_level,
        question_types=question_types,
        knowledge_points=knowledge_points,
        user_requirements=user_requirements_text,
        product_knowledge=product_knowledge,
    )

    content = [{"type": "input_text", "text": user_prompt}]
    text = await _call_responses(
        instructions=system_prompt,
        content=content,
        temperature=0.2,
        max_output_tokens=min(32768, max(8192, count * 1200)),
    )
    if not text:
        raise AIQuestionGenerationError("大模型返回空响应，请稍后重试或调整生成内容")

    llm_questions = parse_questions_from_content(text)
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


async def generate_questions_from_transcript(
    *,
    transcript: str,
    video_title: str,
    count: int,
    difficulty_level: str,
    question_type_ratios: dict[str, int],
    category_id: int | None = None,
    video_id: int | None = None,
) -> list[dict[str, Any]]:
    """Generate questions from a text transcript (auto pipeline path)."""
    if not transcript.strip():
        raise AIQuestionGenerationError("视频转录文本为空，无法生成题目")

    question_types = expand_question_types(question_type_ratios, count)
    difficulty = DIFFICULTY_TO_SCORE.get(difficulty_level, 3)

    system_prompt, user_prompt = build_question_prompt(
        video_title=video_title,
        transcript=transcript,
        count=count,
        difficulty_level=difficulty_level,
        question_types=question_types,
        knowledge_points=[],
        user_requirements="",
        product_knowledge=[],
    )

    content = [{"type": "input_text", "text": user_prompt}]
    text = await _call_responses(
        instructions=system_prompt,
        content=content,
        temperature=0.2,
        max_output_tokens=min(32768, max(8192, count * 1200)),
    )
    if not text:
        raise AIQuestionGenerationError("大模型返回空响应，请稍后重试")

    questions = parse_questions_from_content(text)
    if not questions:
        raise AIQuestionGenerationError("大模型未返回题目，请补充视频文本或知识点后重试")

    normalized = [
        normalize_generated_question(
            item,
            fallback_type=question_types[index % len(question_types)],
            difficulty=difficulty,
            category_id=category_id,
            video_id=video_id,
            fallback_tags=[video_title, difficulty_level],
        )
        for index, item in enumerate(questions[:count])
    ]
    normalized = [item for item in normalized if item["content"] and item["answer"]]
    if not normalized:
        raise AIQuestionGenerationError("大模型返回内容格式无效，未生成可入库题目")
    return normalized


def build_question_prompt(
    *,
    video_title: str,
    transcript: str,
    count: int,
    difficulty_level: str,
    question_types: list[str],
    knowledge_points: list[str],
    user_requirements: str,
    product_knowledge: list[dict[str, Any]],
) -> tuple[str, str]:
    """Build (system_prompt, user_prompt) for transcript-based question generation."""
    system_prompt = (
        "你是销售培训系统的题库生成助手。必须只输出 JSON，不要输出 Markdown。"
        "JSON 顶层字段必须是 questions。题型只允许 single、multiple、true_false。"
        "single 和 true_false 的 answer 只能是单个选项字母；multiple 的 answer 使用逗号分隔选项字母。"
        "题目必须严格依据下面提供的视频音频转录文本生成，不得编造转录中没有的事实。"
        "user_requirements 只是出题角度建议，不能作为事实依据，不能覆盖或补充转录中不存在的事实；"
        "如与转录内容冲突必须忽略建议。"
        "单选题只能使用 A/B/C/D 中的一个作为 answer。"
        "多选题只能使用 A/B/C/D，多个答案用英文逗号分隔。"
        "true_false 只能使用 A 或 B，A=正确，B=错误，禁止返回 C 或 D。"
        "analysis 必须和题目及答案严格对应，必须引用转录文本中的时间戳证据（如 [02:15]），"
        "并逐项说明每个选项正确或错误的原因；判断题也必须说明该陈述为何正确或错误。"
    )

    user_payload = {
        "task": "根据视频音频转录文本生成题库",
        "video_title": video_title,
        "count": count,
        "difficulty": DIFFICULTY_LABELS.get(difficulty_level, "场景应用"),
        "question_types_in_order": question_types,
        "knowledge_points": knowledge_points,
        "user_requirements": truncate_text(user_requirements, 1000),
        "product_knowledge": product_knowledge,
        "true_false_options": {"A": "正确", "B": "错误"},
        "transcript_with_timestamps": transcript,
        "output_schema": {
            "questions": [{
                "content": "题干",
                "type": "single|multiple|true_false",
                "options": {"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"},
                "answer": "A 或 A,B",
                "analysis": "解析，引用 [MM:SS] 时间段证据",
                "tags": ["标签"],
            }],
        },
    }
    return system_prompt, json.dumps(user_payload, ensure_ascii=False)


# ─────────────────────────────── 响应解析 ───────────────────────────────


def parse_questions_from_content(content: str) -> list[dict[str, Any]]:
    """Parse LLM response into question dicts. Handles common LLM JSON errors."""
    import logging
    logger = logging.getLogger(__name__)

    cleaned = strip_json_fence(content)

    def _try_parse(text: str) -> list[dict[str, Any]] | None:
        """Try parsing, return None if failed."""
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            # Try to fix common LLM JSON issues
            fixed = _fix_llm_json(text)
            if fixed is not None:
                try:
                    payload = json.loads(fixed)
                except json.JSONDecodeError:
                    # Fallback: regex extract
                    match = re.search(r"\{.*\}", text, re.DOTALL)
                    if match:
                        try:
                            payload = json.loads(match.group(0))
                        except json.JSONDecodeError:
                            fixed_sub = _fix_llm_json(match.group(0))
                            if fixed_sub:
                                try:
                                    payload = json.loads(fixed_sub)
                                except json.JSONDecodeError:
                                    return None
                            else:
                                return None
                    else:
                        return None
            else:
                return None

        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        questions = payload.get("questions") if isinstance(payload, dict) else None
        if isinstance(questions, list):
            return [item for item in questions if isinstance(item, dict)]
        # Check if top-level object IS a question
        if isinstance(payload, dict) and "content" in payload:
            return [payload]
        return None

    questions = _try_parse(cleaned)
    if questions is not None:
        # 成功解析为 questions 数组（即使为空）也直接返回，由上层判定"未返回题目"
        return questions

    # Last resort: try to extract individual question objects from the text
    logger.warning("JSON 解析失败，尝试逐个提取题目对象。原始内容前500字符: %s", content[:500])
    questions = _extract_question_objects(cleaned)
    if questions:
        logger.info("逐个提取成功，获得 %s 道题目", len(questions))
        return questions

    raise AIQuestionGenerationError(
        f"大模型返回内容不是有效 JSON。原始内容前300字符: {content[:300]}"
    )


def _fix_llm_json(text: str) -> str | None:
    """Fix common LLM JSON formatting errors. Returns None if unfixable."""
    import re as regex
    changed = False

    # 1. Remove trailing commas before ] or }
    fixed = regex.sub(r",\s*([}\]])", r"\1", text)
    if fixed != text:
        changed = True
        text = fixed

    # 2. Remove trailing comma at end of file
    fixed = regex.sub(r",\s*$", "", text)
    if fixed != text:
        changed = True
        text = fixed

    return text if changed else None


def _extract_question_objects(text: str) -> list[dict[str, Any]]:
    """Extract individual question objects by tracking brace depth (handles nested JSON)."""
    import re as regex
    results: list[dict[str, Any]] = []

    # Find start of each question object: { followed by a known question key
    start_pattern = regex.compile(
        r'\{\s*"(?:content|type|options|answer|analysis|difficulty|tags)"\s*:',
        regex.DOTALL,
    )

    for match in start_pattern.finditer(text):
        start_idx = match.start()
        depth = 0
        in_string = False
        escape = False
        for i in range(start_idx, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    obj_str = text[start_idx:i + 1]
                    try:
                        fixed = _fix_llm_json(obj_str)
                        obj = json.loads(fixed if fixed else obj_str)
                        if isinstance(obj, dict) and "content" in obj:
                            results.append(obj)
                    except json.JSONDecodeError:
                        pass
                    break

    return results


def strip_json_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def truncate_text(text: str, max_chars: int) -> str:
    text = text.strip()
    return text if len(text) <= max_chars else text[:max_chars]


# ─────────────────────────────── 方法论生成 ───────────────────────────────


async def call_methodology_llm(audio_path: Path) -> dict[str, str]:
    """ASR + LLM pipeline for sales methodology extraction (both on Doubao).

    Step 1 — ASR via Doubao Responses API.
    Step 2 — methodology extraction via Doubao Responses API.
    Returns ``{"title": "...", "content": "..."}``.
    """
    if not audio_path.exists():
        raise AIQuestionGenerationError(f"音频文件不存在：{audio_path}")

    import logging
    logger = logging.getLogger(__name__)
    transcript = await _call_asr_doubao(audio_path, logger)
    if not transcript:
        raise AIQuestionGenerationError("语音转写结果为空，请确认音频包含有效语音内容")

    return await _call_methodology_llm_from_text(transcript)


async def _call_methodology_llm_from_text(transcript: str) -> dict[str, str]:
    """Generate methodology from transcript via Doubao."""
    system_prompt = (
        "你是一位资深的销售培训专家。请根据以下销售对话的语音转写内容，"
        "提炼出一条可复用的销售方法论。"
        "只输出纯 JSON，格式：{\"title\": \"方法论标题\", \"content\": \"详细的方法论内容\"}。"
        "不要输出 Markdown 代码块。"
    )

    content = [{
        "type": "input_text",
        "text": f"以下是销售录音的转写文本，请提炼方法论：\n\n{transcript}",
    }]
    text = await _call_responses(
        instructions=system_prompt,
        content=content,
        temperature=0.3,
        max_output_tokens=2048,
    )
    if not text:
        raise AIQuestionGenerationError("大模型返回空响应，请稍后重试")

    cleaned = strip_json_fence(text)
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise AIQuestionGenerationError("大模型返回内容不是有效 JSON")
        result = json.loads(match.group(0))

    title = str(result.get("title") or "").strip()
    content_val = str(result.get("content") or "").strip()
    if not title and not content_val:
        raise AIQuestionGenerationError("大模型未返回方法论内容")

    return {"title": title or "未命名方法论", "content": content_val}


# ─────────────────────────────── 工具函数 ───────────────────────────────


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
        return ",".join(sorted(str(item).strip() for item in answer if str(item).strip()))
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
