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
from app.services.video_processing import probe_video, resolve_video_tool

SUPPORTED_TYPES = ("single", "multiple", "true_false")
DIFFICULTY_TO_SCORE = {"L1": 1, "L2": 3, "L3": 5}
DIFFICULTY_LABELS = {"L1": "基础理解", "L2": "场景应用", "L3": "综合判断"}


class AIQuestionGenerationError(RuntimeError):
    """Raised when the configured LLM cannot return usable question drafts."""


async def transcribe_video_audio(video_path: Path) -> str:
    """Extract audio from video and transcribe via DashScope paraformer-v2.

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
    # DashScope data-uri 限制 20MB，base64 膨胀约 33%，原始 mp3 需 < 15MB
    MAX_AUDIO_BYTES = 15 * 1024 * 1024
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
                f"音频文件过大（{file_size} bytes），超过 DashScope 20MB 限制，请上传更短的视频"
            )

        logger.info("正在使用 paraformer-v2 转写 video_path=%s", video_path)
        transcript = await _call_asr_paraformer(audio_path, logger)
        logger.info("ASR 转写完成 chars=%s", len(transcript))
        return transcript
    except subprocess.TimeoutExpired:
        raise AIQuestionGenerationError("音频提取超时，视频可能过长")
    finally:
        audio_path.unlink(missing_ok=True)


async def _call_asr_paraformer(audio_path: Path, logger) -> str:
    """Transcribe audio via DashScope paraformer-v2 (supports word-level timestamps).

    Returns formatted transcript with sentence-level timestamps:
        [MM:SS] sentence text
    """
    import dashscope
    from dashscope.audio.asr import Transcription

    mime_type = mimetypes.guess_type(audio_path.name)[0] or "audio/mpeg"
    base64_str = base64.b64encode(audio_path.read_bytes()).decode("ascii")
    data_uri = f"data:{mime_type};base64,{base64_str}"

    # Submit sync transcription with model fallback
    models = ["paraformer-v2", "paraformer-v1", "paraformer-8k-v2", "paraformer-8k-v1", "paraformer-mtl-v1"]
    last_error = ""
    response = None
    for model_name in models:
        try:
            response = await asyncio.to_thread(
                Transcription.call,
                model=model_name,
                file_urls=[data_uri],
                api_key=settings.ai_api_key,
            )
            resp_output = response.output if hasattr(response, 'output') and response.output else {}
            if resp_output and resp_output.get("results"):
                logger.info("ASR 模型 %s 调用成功", model_name)
                break
            last_error = getattr(response, 'message', '') or getattr(response, 'code', '')
            logger.warning("ASR 模型 %s 返回空结果（%s），尝试下一个", model_name, last_error)
        except Exception as exc:
            last_error = str(exc)
            logger.warning("ASR 模型 %s 异常: %s，尝试下一个", model_name, last_error)

    output = response.output if response and hasattr(response, 'output') and response.output else {}
    if not output:
        raise AIQuestionGenerationError(
            f"所有 ASR 模型均失败，最后错误：{last_error}"
        )

    # Get transcription JSON URL
    results = output.get("results", [])
    if not results:
        raise AIQuestionGenerationError("语音转写失败：无结果返回")

    transcription_url = results[0].get("transcription_url", "")
    if not transcription_url:
        code = results[0].get("code", "")
        msg = results[0].get("message", "")
        raise AIQuestionGenerationError(f"语音转写失败：{code} - {msg}")

    # Download and parse the transcription JSON
    transcript_data = await asyncio.to_thread(_download_transcription_json, transcription_url)

    # Format sentences with timestamps
    transcripts = transcript_data.get("transcripts", [])
    lines: list[str] = []
    for t in transcripts:
        for sent in t.get("sentences", []):
            start_ms = sent.get("begin_time", 0)
            start_min = int(start_ms // 60000)
            start_sec = int((start_ms % 60000) // 1000)
            timestamp = f"[{start_min:02d}:{start_sec:02d}]"
            text = sent.get("text", "").strip()
            if text:
                lines.append(f"{timestamp} {text}")

    transcript = "\n".join(lines)
    logger.info("paraformer-v2 转写完成 chars=%s sentences=%s", len(transcript), len(lines))
    return transcript


def _download_transcription_json(url: str) -> dict[str, Any]:
    """Download and parse the transcription result JSON from OSS URL."""
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise AIQuestionGenerationError(f"无法下载转写结果：{exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise AIQuestionGenerationError("转写结果 JSON 解析失败") from exc


async def call_llm(messages: list[dict[str, str]], max_tokens: int = 1024) -> str:
    """Generic LLM call returning the first assistant message text."""
    if not settings.ai_api_key:
        raise AIQuestionGenerationError("AI_API_KEY 未配置")

    payload = {
        "model": settings.ai_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    response = await asyncio.to_thread(
        _post_chat_completion,
        payload,
        settings.ai_request_timeout_seconds,
    )
    return extract_message_content(response)


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
    """Generate questions from a text transcript (after ASR), using a text-only model."""
    if not transcript.strip():
        raise AIQuestionGenerationError("视频转录文本为空，无法生成题目")

    question_types = expand_question_types(question_type_ratios, count)
    difficulty = DIFFICULTY_TO_SCORE.get(difficulty_level, 3)
    difficulty_label = DIFFICULTY_LABELS.get(difficulty_level, "场景应用")

    system_prompt = (
        "你是销售培训系统的题库生成助手。必须只输出 JSON，不要输出 Markdown。"
        "JSON 顶层字段必须是 questions。题型只允许 single、multiple、true_false。"
        "single 和 true_false 的 answer 只能是单个选项字母；multiple 的 answer 使用逗号分隔选项字母。"
        "题目必须严格依据下面提供的视频转录文本生成，不得编造视频中没有的事实。"
        "单选题只能使用 A/B/C/D 中的一个作为 answer。"
        "多选题只能使用 A/B/C/D，多个答案用英文逗号分隔。"
        "true_false 只能使用 A 或 B，A=正确，B=错误，禁止返回 C 或 D。"
        "analysis 必须和题目及答案严格对应，必须引用转录文本中的时间戳证据（如 [02:15]），"
        "并逐项说明每个选项正确或错误的原因。"
    )

    user_prompt = json.dumps({
        "task": "根据视频转录文本生成题库",
        "video_title": video_title,
        "count": count,
        "difficulty": difficulty_label,
        "question_types_in_order": question_types,
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
    }, ensure_ascii=False)

    payload = {
        "model": settings.ai_question_text_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": min(32768, max(8192, count * 1200)),
        "stream": True,
    }

    response = await asyncio.to_thread(
        _post_chat_completion,
        payload,
        settings.ai_request_timeout_seconds,
    )
    content = extract_message_content(response)
    if not content:
        raise AIQuestionGenerationError("大模型返回空响应，请稍后重试")

    questions = parse_questions_from_content(content)
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
        "max_tokens": min(32768, max(8192, count * 1200)),
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
    if questions:
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

    # 3. Fix single quotes used instead of double quotes (inside arrays/objects only)
    # Skip this for now as it could break content with apostrophes

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


async def call_methodology_llm(audio_path: Path) -> dict[str, str]:
    """ASR + LLM pipeline for sales methodology extraction.

    Step 1 — ASR via paraformer-v2 (DashScope Transcription).
    Step 2 — LLM via qwen3.6-flash (OpenAI-compatible Chat Completions).
    Returns ``{"title": "...", "content": "..."}``.
    """
    if not audio_path.exists():
        raise AIQuestionGenerationError(f"音频文件不存在：{audio_path}")

    # ── Step 1: ASR ───────────────────────────────────────────────────
    import logging
    logger = logging.getLogger(__name__)
    transcript = await _call_asr_paraformer(audio_path, logger)
    if not transcript:
        raise AIQuestionGenerationError("语音转写结果为空，请确认音频包含有效语音内容")

    # ── Step 2: LLM methodology extraction ────────────────────────────
    return await _call_methodology_llm_from_text(transcript)


async def _call_methodology_llm_from_text(transcript: str) -> dict[str, str]:
    """Generate methodology from transcript via qwen3.6-flash."""
    system_prompt = (
        "你是一位资深的销售培训专家。请根据以下销售对话的语音转写内容，"
        "提炼出一条可复用的销售方法论。"
        "只输出纯 JSON，格式：{\"title\": \"方法论标题\", \"content\": \"详细的方法论内容\"}。"
        "不要输出 Markdown 代码块。"
    )

    payload = {
        "model": settings.methodology_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"以下是销售录音的转写文本，请提炼方法论：\n\n{transcript}"},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
        "stream": True,
    }

    response = await asyncio.to_thread(
        _post_chat_completion,
        payload,
        settings.ai_request_timeout_seconds,
    )
    content = extract_message_content(response)
    if not content:
        raise AIQuestionGenerationError("大模型返回空响应，请稍后重试")

    # Parse JSON from response
    cleaned = strip_json_fence(content)
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
