"""Practice agent — core agent loop with SSE streaming and MCP tool calling.

Architecture:
  1. Build system prompt with user profile + session context + long-term memories
  2. Send user message to LLM (qwen3.6-plus via DashScope-compatible API)
  3. Stream SSE events: text tokens, tool_call events, tool_result events, evaluation
  4. If LLM returns tool_calls → execute tools → feed results back → continue loop
  5. On final response, evaluate user answer and save memories
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.practice_session import PracticeMessage, PracticeSession
from app.services.practice_memory import (
    extract_insights_from_session,
    format_memories_for_prompt,
    get_session_context,
    retrieve_memories,
    save_memory,
)
from app.services.practice_tools import (
    ToolDef,
    get_all_tool_definitions,
    get_tool,
)
from app.services.user_profile import (
    build_user_profile,
    profile_to_system_prompt,
)

# ── Scenario system prompts ────────────────────────────────────────────────

SCENARIO_PROMPTS: dict[str, str] = {
    "reception": (
        "你扮演一位进店顾客。学员需按接待流程（迎宾→问好→引导→了解需求）接待你。\n"
        "模拟真实顾客的言行和需求，在适当时候给出反馈。"
    ),
    "question": (
        "你扮演一位有视力问题的顾客。学员需通过专业问诊了解你的用眼习惯、佩戴史和预算。\n"
        "模拟具体视力需求场景（长时间用电脑、开车、阅读等），给学员充分练习机会。"
    ),
    "product": (
        "你扮演一位对镜片/镜架有疑问的顾客。学员需用FAB方法介绍产品卖点。\n"
        "可调用 search_scripts/get_product_info 获取话术和产品资料。"
    ),
    "objection": (
        "你扮演一位对价格/效果/品牌有疑虑的顾客。学员需用「理解+转折+解决」三步法应对。\n"
        "提出常见顾客异议（太贵了、和网上比价、担心效果等），可调用 search_scripts 查找话术。"
    ),
    "closing": (
        "你扮演一位犹豫不决的顾客。学员需用促单技巧推动成交。\n"
        "表现出犹豫、需要再考虑等信号，考验学员的促单能力。"
    ),
    "fitting": (
        "你扮演一位需要验光配镜的顾客。学员需模拟验光配镜全流程。\n"
        "模拟顾客的视力问题和佩戴需求，关注学员的专业性和服务态度。"
    ),
    "aftercare": (
        "你扮演一位需要售后服务的顾客。学员需处理投诉并尝试转化复购。\n"
        "提出售后常见问题（佩戴不适、镜片划痕、度数不准等）。"
    ),
    "general": (
        "你是眼镜销售培训 AI 教练，负责解答学员的销售相关问题。\n"
        "不要扮演顾客，而是以教练身份回复：回答问题、提供话术建议、解释方法论。\n"
        "可调用 search_scripts/get_product_info/get_methodology 获取资料。\n"
        "不需要评估学员，只提供有帮助的专业回复。"
    ),
}

# ── Base system prompt template ────────────────────────────────────────────

BASE_SYSTEM_PROMPT = """你是眼镜销售培训 AI 教练，通过模拟顾客对话帮学员练习话术。

## 规则
- 扮演真实顾客，根据场景提出具体需求和疑问
- 可用工具：search_scripts（查话术）get_product_info（查产品）get_methodology（查方法论），需要时主动调用
- 中文对话，专业有温度，每次回复 100-300 字
- 不要在回复中打分或写【评分】——系统会自动评估
"""


# ── SSE event builder ──────────────────────────────────────────────────────

def _sse_event(event: str, data: Any) -> str:
    """Build a single SSE event string."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


# ── LLM call ───────────────────────────────────────────────────────────────

async def _call_llm_stream(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Stream LLM response chunks. Each yielded dict is a partial delta.

    Uses urllib with line-by-line reading for true SSE streaming.
    The sync reader runs in a thread and pushes lines into an asyncio Queue
    so we can yield deltas immediately without buffering.
    """
    import urllib.request
    import urllib.error
    import queue
    import threading

    payload: dict[str, Any] = {
        "model": settings.agent_model,
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.7,
        "stream": True,
    }

    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    url = f"{settings.ai_base_url.rstrip('/')}/chat/completions"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.ai_api_key}",
            "Content-Type": "application/json",
        },
    )

    line_queue: queue.Queue[tuple[str, str | None]] = queue.Queue()
    """Thread-safe queue: each item is (line_content, error_message_or_None)."""

    def _thread_read():
        """Read SSE lines in a background thread, pushing to queue."""
        try:
            resp = urllib.request.urlopen(req, timeout=settings.ai_request_timeout_seconds)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            line_queue.put(("", f"LLM API 错误 HTTP {exc.code}: {detail}"))
            return
        except urllib.error.URLError as exc:
            line_queue.put(("", f"无法连接 LLM API: {exc.reason}"))
            return

        try:
            for line_bytes in resp:
                line = line_bytes.decode("utf-8", errors="ignore").strip()
                if line:
                    line_queue.put((line, None))
            line_queue.put(("__DONE__", None))  # signal EOF
        except Exception as exc:
            line_queue.put(("", str(exc)))
        finally:
            resp.close()

    thread = threading.Thread(target=_thread_read, daemon=True)
    thread.start()

    # Consume from queue, yielding deltas
    while True:
        line, error = await asyncio.to_thread(line_queue.get)

        if error:
            raise RuntimeError(error)

        if line == "__DONE__":
            return

        if not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if not data or data == "[DONE]":
            continue
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            continue
        for choice in parsed.get("choices") or []:
            delta = choice.get("delta") or {}
            yield delta


# ── Tool executor ──────────────────────────────────────────────────────────

async def _execute_tool_calls(
    tool_calls: list[dict[str, Any]],
    session: AsyncSession,
) -> list[dict[str, Any]]:
    """Execute MCP tool calls and return results."""
    results: list[dict[str, Any]] = []

    for tc in tool_calls:
        func_info = tc.get("function", {})
        tool_name = func_info.get("name", "")
        tool_args_str = func_info.get("arguments", "{}")

        try:
            tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
        except json.JSONDecodeError:
            tool_args = {}

        tool: ToolDef | None = get_tool(tool_name)
        if tool is None:
            results.append({
                "tool_call_id": tc.get("id", ""),
                "role": "tool",
                "content": json.dumps({"error": f"未知工具: {tool_name}"}, ensure_ascii=False),
            })
            continue

        try:
            # Inject session for tools that need DB access
            if "session" in tool.execute.__code__.co_varnames[:3]:
                tool_args["session"] = session
            result_content = await tool.execute(**tool_args)
        except Exception as exc:
            result_content = json.dumps({"error": f"工具执行失败: {str(exc)}"}, ensure_ascii=False)

        results.append({
            "tool_call_id": tc.get("id", ""),
            "role": "tool",
            "content": result_content,
        })

    return results


# ── Main agent stream ──────────────────────────────────────────────────────

async def run_practice_agent(
    session: AsyncSession,
    session_id: int,
    user_id: int,
    user_message: str,
    module_code: str = "general",
) -> AsyncGenerator[str, None]:
    """Run the practice agent and yield SSE event strings.

    The generator yields SSE-formatted strings that can be written directly
    to a StreamingResponse body.

    Args:
        session: Async DB session.
        session_id: Current practice session ID.
        user_id: The learner's user ID.
        user_message: The user's latest message text.
        module_code: Practice scenario code.

    Yields:
        SSE event strings: text, tool_call, tool_result, evaluation, error, done.
    """
    # ── 1. Load context ──────────────────────────────────────────────
    practice_session = await session.get(PracticeSession, session_id)
    if not practice_session:
        yield _sse_event("error", {"message": "会话不存在"})
        return

    turn_number = (practice_session.total_turns or 0) + 1

    # Save user message
    user_msg = PracticeMessage(
        session_id=session_id,
        role="user",
        content=user_message,
        turn_number=turn_number,
    )
    session.add(user_msg)
    await session.flush()

    # ── 2. Build profile & memories ──────────────────────────────────
    profile = await build_user_profile(user_id, session)
    profile_text = profile_to_system_prompt(profile)

    session_context = await get_session_context(session, session_id, max_turns=8)
    memories = await retrieve_memories(
        session, user_id,
        query_hints=[module_code, user_message[:80]],
        top_k=5,
    )
    memories_text = format_memories_for_prompt(memories)

    # ── 3. Build system prompt ───────────────────────────────────────
    scenario_prompt = SCENARIO_PROMPTS.get(module_code, SCENARIO_PROMPTS["general"])
    system_content = (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        f"## 当前演练场景\n{scenario_prompt}\n\n"
        f"{profile_text}\n\n"
        f"{memories_text}"
    )

    # ── 4. Build messages array ──────────────────────────────────────
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_content},
    ]

    # Add recent session context
    for ctx_msg in session_context[-16:]:  # Last ~8 turns
        entry: dict[str, Any] = {"role": ctx_msg["role"]}
        if ctx_msg.get("content"):
            entry["content"] = ctx_msg["content"]
        if ctx_msg.get("tool_calls"):
            entry["tool_calls"] = ctx_msg["tool_calls"]
        if ctx_msg.get("tool_results"):
            entry["content"] = ctx_msg["tool_results"].get("content", json.dumps(ctx_msg["tool_results"], ensure_ascii=False)) if isinstance(ctx_msg["tool_results"], dict) else str(ctx_msg["tool_results"])
            entry["role"] = "tool"
        messages.append(entry)

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    # ── 5. Agent loop (unbounded — stops when LLM no longer calls tools) ──
    llm_tools = [t for t in get_all_tool_definitions() if t["function"]["name"] != "evaluate_response"]
    full_response_text = ""
    all_tool_calls: list[dict[str, Any]] = []
    all_tool_results: list[dict[str, Any]] = []
    first_iteration = True

    while True:
        delta_text = ""
        tool_call_deltas: dict[int, dict[str, Any]] = {}

        # First iteration: no tools → stream text directly (fast path)
        # Subsequent iterations: pass tools, LLM decides whether to call them
        active_tools = None if first_iteration else llm_tools

        try:
            async for delta in _call_llm_stream(messages, active_tools):
                # Handle text content
                content = delta.get("content")
                if content:
                    if isinstance(content, str):
                        delta_text += content
                        full_response_text += content
                        yield _sse_event("text", {"content": content})
                    elif isinstance(content, list):
                        for item in content:
                            text = item.get("text", "")
                            if text:
                                delta_text += text
                                full_response_text += text
                                yield _sse_event("text", {"content": text})

                # Handle tool calls
                tc_list = delta.get("tool_calls")
                if tc_list:
                    for tc in tc_list:
                        idx = tc.get("index", 0)
                        if idx not in tool_call_deltas:
                            tool_call_deltas[idx] = {
                                "id": tc.get("id", ""),
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        if tc.get("id"):
                            tool_call_deltas[idx]["id"] = tc["id"]
                        func = tc.get("function", {})
                        if func.get("name"):
                            tool_call_deltas[idx]["function"]["name"] += func["name"]
                        if func.get("arguments"):
                            tool_call_deltas[idx]["function"]["arguments"] += func["arguments"]
        except RuntimeError as exc:
            yield _sse_event("error", {"message": str(exc)})
            return

        # ── If there are tool calls, execute them ────────────────────
        if tool_call_deltas:
            tool_calls_list = list(tool_call_deltas.values())
            for tc in tool_calls_list:
                yield _sse_event("tool_call", {
                    "name": tc["function"]["name"],
                    "arguments": tc["function"]["arguments"],
                })
                all_tool_calls.append(tc)

            # Execute tools
            tool_results = await _execute_tool_calls(tool_calls_list, session)
            all_tool_results.extend(tool_results)

            for tr in tool_results:
                yield _sse_event("tool_result", {
                    "tool_call_id": tr["tool_call_id"],
                    "content": tr["content"],
                })

            # Add assistant message with tool calls to messages
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": delta_text or None}
            if tool_calls_list:
                assistant_msg["tool_calls"] = tool_calls_list
            messages.append(assistant_msg)

            # Add tool result messages
            for tr in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tr["tool_call_id"],
                    "content": tr["content"],
                })

            # Save tool messages
            tool_msg = PracticeMessage(
                session_id=session_id,
                role="assistant",
                content=delta_text or None,
                tool_calls=tool_calls_list,
                tool_results=tool_results,
                turn_number=turn_number,
            )
            session.add(tool_msg)
            await session.flush()

            # Continue loop for LLM to process tool results
            first_iteration = False
            continue
        else:
            # No tool calls — final response
            break

    # ── 6. Save assistant message ────────────────────────────────────
    assistant_msg_db = PracticeMessage(
        session_id=session_id,
        role="assistant",
        content=full_response_text,
        tool_calls=all_tool_calls if all_tool_calls else None,
        tool_results=all_tool_results if all_tool_results else None,
        turn_number=turn_number,
    )
    session.add(assistant_msg_db)
    await session.flush()

    # ── 7. Evaluate user response (skip for general/coach mode) ─────
    if module_code != "general":
        eval_tool = get_tool("evaluate_response")
        if eval_tool and not any(
            tc.get("function", {}).get("name") == "evaluate_response"
            for tc in all_tool_calls
        ):
            try:
                eval_result = await eval_tool.execute(
                    user_response=user_message,
                    scenario=module_code,
                )
                evaluation = json.loads(eval_result)
                yield _sse_event("evaluation", evaluation)

                # Update the user message with evaluation
                user_msg.evaluation = evaluation
                assistant_msg_db.evaluation = evaluation

                # Check if this is a weakness (score ≤ 2)
                if evaluation.get("score", 3) <= 2:
                    for imp in evaluation.get("improvements", []):
                        await save_memory(
                            session, user_id,
                            memory_type="weakness",
                            value=str(imp),
                            importance=7,
                            source_session_id=session_id,
                        )
            except Exception:
                pass  # Evaluation is best-effort

    # ── 8. Update session ────────────────────────────────────────────
    practice_session.total_turns = turn_number

    # Recalculate average score from message evaluations
    from sqlalchemy import select as sa_select
    eval_result = await session.execute(
        sa_select(PracticeMessage.evaluation)
        .where(
            PracticeMessage.session_id == session_id,
            PracticeMessage.evaluation.isnot(None),
        )
    )
    evals = [e[0] for e in eval_result.all() if e[0]]
    if evals:
        scores = [e.get("score", 0) for e in evals if isinstance(e, dict)]
        if scores:
            practice_session.average_score = round(sum(scores) / len(scores), 1)

    await session.flush()

    # ── 9. Done ──────────────────────────────────────────────────────
    yield _sse_event("done", {
        "session_id": session_id,
        "turn": turn_number,
        "average_score": practice_session.average_score,
    })
