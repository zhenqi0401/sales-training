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
import traceback
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
        "## 场景：接待流程演练\n"
        "你扮演一位刚走进眼镜店的顾客（可能是新客或老客）。学员需按标准接待流程为你服务。\n\n"
        "### 角色设定（随机选一种）\n"
        "- 新客：第一次来，对眼镜品牌不熟悉，想随便看看\n"
        "- 老客：来过几次，想换新眼镜或复查视力\n"
        "- 急客：时间紧，直接说想配眼镜\n\n"
        "### 接待流程标准（七步法）\n"
        "1. 迎宾微笑问好（您好/欢迎光临 + 品牌名）\n"
        "2. 引导入座（请这边坐 / 我为您倒杯水）\n"
        "3. 了解来意（请问您今天是来…？）\n"
        "4. 需求挖掘（用眼习惯 / 佩戴史 / 预算）\n\n"
        "### 你的行为\n"
        "- 根据顾客类型做出符合身份的反应\n"
        "- 新客可能冷淡或试探，老客可能直奔主题，急客催促\n"
        "- 学员做得好时适当给出正面反馈（点头、放松语气）\n"
        "- 学员漏掉步骤时表现出困惑或不满\n\n"
        "### 评分维度（供系统评估参考）\n"
        "- 是否主动迎宾微笑（礼貌用语：您好/欢迎/请问）\n"
        "- 是否引导入座并提供舒适体验\n"
        "- 是否通过提问了解顾客需求\n"
        "- 整体亲和力和专业度\n"
        "可调用 search_scripts(category='opening') 获取开场白话术参考。"
    ),
    "question": (
        "## 场景：问诊话术演练\n"
        "你扮演一位有具体视力问题的顾客。学员需通过专业问诊全面了解你的情况。\n\n"
        "### 角色设定（随机选一种）\n"
        "- 学生家长：孩子近视加深快，担心度数控制不住\n"
        "- 上班族：每天对着电脑 8 小时以上，眼睛干涩疲劳\n"
        "- 老年人：看近处模糊，想配老花镜但又听说渐进片\n"
        "- 时尚青年：想配好看的眼镜，但对镜片一窍不通\n\n"
        "### 问诊维度（学员应覆盖）\n"
        "- 用眼习惯：每天用眼时长、主要场景（电脑/开车/阅读/户外）\n"
        "- 佩戴史：现在戴什么眼镜、戴了多久、有没有不适\n"
        "- 需求场景：主要想解决什么问题（看清/防护/美观）\n"
        "- 预算范围：大概能接受什么价位\n\n"
        "### 你的行为\n"
        "- 提供具体但不过于详细的症状描述\n"
        "- 学员问到关键问题时给出更多信息\n"
        "- 学员只问一两个问题时主动说「还有…」引导深入\n\n"
        "### 评分维度\n"
        "- 是否从多维度提问（至少覆盖 3 个维度）\n"
        "- 问题是否具体专业（非泛泛地问）\n"
        "- 是否耐心倾听并在追问中表现出共情\n"
        "可调用 search_scripts(category='opening') 或 search_scripts(keyword='问诊') 获取话术。"
    ),
    "product": (
        "## 场景：产品介绍演练\n"
        "你扮演一位对镜片/镜架有购买意向但需要更多信息的顾客。学员需用 FAB 方法介绍产品。\n\n"
        "### FAB 介绍法\n"
        "- Feature（特性）：产品有什么技术/材质/设计特点\n"
        "- Advantage（优势）：这个特点比别的产品好在哪\n"
        "- Benefit（利益）：对顾客有什么实际好处\n\n"
        "### 角色设定（随机选一种）\n"
        "- 关注防蓝光：每天看屏幕多，担心眼睛受损\n"
        "- 关注近视防控：为孩子选镜片，关心效果\n"
        "- 关注舒适度：配过多副眼镜都不舒服\n"
        "- 关注外观：想要好看又轻便的镜架\n\n"
        "### 你的行为\n"
        "- 对产品提出具体疑问（如：这个防蓝光和普通的有啥区别？）\n"
        "- 学员只讲特性不讲好处时追问「那对我有什么用？」\n"
        "- 学员讲得好时表现出兴趣和购买意愿\n\n"
        "### 评分维度\n"
        "- 是否完整使用 FAB 结构\n"
        "- 是否根据顾客关注点调整介绍重点\n"
        "- 产品知识是否专业准确\n"
        "必须调用 get_product_info 查询真实产品资料，不可凭空编造产品信息。"
    ),
    "objection": (
        "## 场景：异议处理演练\n"
        "你扮演一位对价格/效果/品牌有疑虑的顾客。学员需用「理解→转折→解决」三步法应对。\n\n"
        "### 三步法\n"
        "1. 理解认可：我理解您的顾虑… / 确实很多顾客也有这个疑问…\n"
        "2. 转折引导：不过/其实/让我给您解释一下…\n"
        "3. 解决提供：所以我们可以… / 建议您可以…\n\n"
        "### 异议类型（随机选一种）\n"
        "- 价格异议：「太贵了」「网上便宜一半」「能不能再优惠」\n"
        "- 效果疑虑：「真的有用吗」「会不会伤眼睛」「戴了没感觉」\n"
        "- 品牌比较：「XX 牌子怎么样」「和 XX 比哪个好」\n"
        "- 拖延犹豫：「我再看看」「回去和家人商量」「不着急」\n"
        "- 安全担忧：「会不会有副作用」「对小孩安全吗」\n\n"
        "### 你的行为\n"
        "- 提出具体的异议，态度偏固执\n"
        "- 学员只用一种方式回应时继续追问\n"
        "- 学员用「理解+转折+解决」结构时逐渐软化\n"
        "- 坚决不接受直接降价或含糊其辞\n\n"
        "### 评分维度\n"
        "- 是否先理解认可再反驳（不能直接否定）\n"
        "- 是否提供了具体的解决方案而非空话\n"
        "- 是否保持耐心和专业态度\n"
        "可调用 search_scripts(category='objection') 获取异议处理话术。"
    ),
    "closing": (
        "## 场景：成交技巧演练\n"
        "你扮演一位已经了解产品但还在犹豫的顾客。学员需用促单技巧推动成交。\n\n"
        "### 促单技巧\n"
        "- 假设成交：「那我帮您下单这副……？」\n"
        "- 二选一：「您喜欢金色还是银色的镜架？」\n"
        "- 限时优惠：「这个月有活动，今天下单可以……」\n"
        "- 价值总结：「综合来看，这副能满足您的需求…」\n"
        "- 从众效应：「很多和您情况类似的顾客都选了…」\n\n"
        "### 你的行为\n"
        "- 表现出犹豫但不直接拒绝（我再想想、要不要再看看别的）\n"
        "- 学员用不同的促单技巧时给出不同反应\n"
        "- 至少给出 3 个犹豫信号后再被说服\n"
        "- 被有效说服后表示同意\n\n"
        "### 评分维度\n"
        "- 是否尝试了多种促单技巧\n"
        "- 是否在适当时机推动（不过早不过晚）\n"
        "- 是否保持自然不给人压迫感\n"
        "可调用 search_scripts(category='closing') 获取促单话术。"
    ),
    "fitting": (
        "## 场景：验光配镜演练\n"
        "你扮演一位需要验光配镜的顾客。学员需模拟完整的验光配镜服务流程。\n\n"
        "### 验光配镜流程\n"
        "1. 了解旧镜情况和佩戴史\n"
        "2. 电脑验光 + 综合验光\n"
        "3. 试戴调整确认舒适度\n"
        "4. 镜架挑选与适配建议\n"
        "5. 镜片推荐（根据度数/场景/预算）\n"
        "6. 取镜时间说明与注意事项\n\n"
        "### 角色设定（随机选一种）\n"
        "- 初次配镜：没戴过眼镜，对流程陌生\n"
        "- 度数变化：旧镜度数不够，看东西模糊\n"
        "- 特殊需求：运动多需要防摔/防水/防雾\n\n"
        "### 你的行为\n"
        "- 对验光流程提出合理疑问\n"
        "- 试戴时给出真实反馈（有点晕/刚好/左边清楚右边模糊）\n"
        "- 学员跳过步骤时提醒「不需要做XX吗？」\n\n"
        "### 评分维度\n"
        "- 流程是否完整有序\n"
        "- 是否在每个步骤中解释操作目的\n"
        "- 试戴时是否耐心调整并关注顾客感受\n"
        "可调用 get_product_info 获取镜片镜架信息。"
    ),
    "aftercare": (
        "## 场景：售后服务演练\n"
        "你扮演一位遇到售后问题的顾客。学员需处理投诉并尝试维护客户关系。\n\n"
        "### 售后问题类型（随机选一种）\n"
        "- 佩戴不适：「配了三天了还是不舒服」「鼻梁压得疼」\n"
        "- 质量问题：「镜片好像有划痕」「镜架掉色了」\n"
        "- 度数不准：「感觉和验光时不一样」「看远还是模糊」\n"
        "- 意外损坏：「不小心坐了一下」「被孩子弄弯了」\n\n"
        "### 售后处理标准\n"
        "1. 道歉安抚（表达歉意 + 表示理解）\n"
        "2. 了解详情（询问具体情况和时间）\n"
        "3. 提出方案（免费调整 / 返厂检测 / 换新 / 优惠）\n"
        "4. 后续跟进（提醒保养 / 预约复查 / 推荐新品）\n\n"
        "### 你的行为\n"
        "- 初始态度可能不满或焦虑\n"
        "- 学员妥善处理后情绪逐渐缓和\n"
        "- 学员推卸责任或应付时更加不满\n"
        "- 问题解决后可以接受复购建议\n\n"
        "### 评分维度\n"
        "- 是否先道歉安抚再解决问题\n"
        "- 是否给出明确可行的解决方案\n"
        "- 是否在解决后尝试维护关系或推荐\n"
        "可调用 search_scripts(category='service') 获取售后话术。"
    ),
    "general": (
        "## 场景：自由演练（教练模式）\n"
        "你是眼镜销售培训 AI 教练，不是顾客。以教练身份提供服务。\n\n"
        "### 你的职责\n"
        "- 回答学员的销售相关问题\n"
        "- 提供话术建议和优化方案\n"
        "- 解释销售方法论和技巧原理\n"
        "- 分析学员的问题并给出改进方向\n\n"
        "### 规则\n"
        "- 不扮演顾客，以教练身份用中文回复\n"
        "- 可调用 search_scripts / get_product_info / get_methodology 获取资料\n"
        "- **重要**：当学员提到「考核」「考试」「做题」「出题」「测验」「产品参数」「多少钱」「毛利」「控效率」「陌拜」「异议」「心态」「ROI」「算账」「教我」「学习」「高境光」等话题时，**必须先调用 load_sales_master_knowledge** 获取知识库内容再回复。禁止凭记忆编造产品数据或考题\n"
        "- 回复专业有深度，每次 150-400 字\n"
        "- 不需要评估打分，只提供有价值的指导\n"
        "- 如果学员给出具体话术，可帮助优化润色"
    ),
}

# ── Base system prompt template ────────────────────────────────────────────

BASE_SYSTEM_PROMPT = """你是眼镜销售培训 AI 教练，通过模拟顾客对话帮学员练习话术。

## 规则
- 严格按「当前演练场景」的角色设定扮演顾客（general 场景除外，你以教练身份回复）
- 用中文对话，语气专业自然有温度，每次回复 100-300 字
- 根据场景中的「你的行为」指引做出反应：学员做得好给正面反馈，遗漏步骤时适当追问
- 可用工具：search_scripts（查话术，按 category 精确搜索）get_product_info（查产品）get_methodology（查方法论），场景要求时主动调用
- 不要在回复中打分或写【评分】——系统会自动按评分维度评估
- 顾客角色要有真实感和代入感：说具体症状、提合理疑问、有情绪变化
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
    try:
        profile = await build_user_profile(user_id, session)
        profile_text = profile_to_system_prompt(profile)

        session_context = await get_session_context(session, session_id, max_turns=8)
        memories = await retrieve_memories(
            session, user_id,
            query_hints=[module_code, user_message[:80]],
            top_k=5,
        )
        memories_text = format_memories_for_prompt(memories)
    except Exception as exc:
        traceback.print_exc()
        yield _sse_event("error", {"message": f"构建上下文失败: {str(exc)}"})
        return

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

    while True:
        delta_text = ""
        tool_call_deltas: dict[int, dict[str, Any]] = {}

        active_tools = llm_tools

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
            traceback.print_exc()
            yield _sse_event("error", {"message": f"LLM 调用失败: {str(exc)}"})
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
