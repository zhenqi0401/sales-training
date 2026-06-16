"""MCP-aligned practice tools — search scripts, products, methodologies, evaluate responses.

These tools are designed to be callable by the agent LLM via function/tool calling.
Each tool has a JSON Schema definition, a typed input model, and an async execute function.

The MCP (Model Context Protocol) pattern used here is:
  1. Tools expose a `definition` (name + description + input_schema) for LLM function calling.
  2. Tools expose an `execute(**kwargs)` async function that performs the actual work.
  3. The agent loop maps LLM tool_calls → tool.execute() → tool results → back to LLM.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.sales_methodology import SalesMethodology
from app.models.script import Script


# ── Tool registry ──────────────────────────────────────────────────────────

@dataclass
class ToolDef:
    """MCP tool definition with JSON Schema and async executor."""
    name: str
    description: str
    input_schema: dict[str, Any]
    execute: Any = field(repr=False)  # async callable


_tool_registry: dict[str, ToolDef] = {}


def register_tool(tool: ToolDef) -> ToolDef:
    _tool_registry[tool.name] = tool
    return tool


def get_tool(name: str) -> ToolDef | None:
    return _tool_registry.get(name)


def get_all_tool_definitions() -> list[dict[str, Any]]:
    """Return all tool definitions in OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema,
            },
        }
        for t in _tool_registry.values()
    ]


# ── Tool implementations ───────────────────────────────────────────────────

async def _search_scripts_execute(
    session: AsyncSession,
    keyword: str = "",
    category: str = "",
    limit: int = 5,
) -> str:
    """Search sales scripts by keyword and/or category."""
    query = select(Script).where(Script.is_active == True)
    if keyword:
        query = query.where(
            or_(
                Script.title.like(f"%{keyword}%"),
                Script.content.like(f"%{keyword}%"),
            )
        )
    if category:
        query = query.where(Script.category == category)

    query = query.order_by(Script.sort_order, Script.id).limit(limit)
    result = await session.execute(query)
    scripts = result.scalars().all()

    if not scripts:
        return json.dumps({"found": 0, "message": f"未找到与 '{keyword}' 相关的话术", "scripts": []}, ensure_ascii=False)

    items = []
    for s in scripts:
        items.append({
            "id": s.id,
            "title": s.title,
            "category": s.category,
            "content": (s.content or "")[:500],
            "theory": (s.theory or "")[:200],
        })

    return json.dumps({
        "found": len(items),
        "scripts": items,
    }, ensure_ascii=False)


SEARCH_SCRIPTS_TOOL = register_tool(ToolDef(
    name="search_scripts",
    description="搜索销售话术库。根据关键词和分类查找匹配的销售话术、技巧和理论知识。可用于获取标准话术模板来指导用户。",
    input_schema={
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "搜索关键词，如产品名、场景、技巧名等",
            },
            "category": {
                "type": "string",
                "description": "话术分类，可选值: opening(开场白), product(产品介绍), objection(异议处理), closing(促单成交), service(售后服务), general(通用话术)",
            },
            "limit": {
                "type": "integer",
                "description": "返回数量上限，默认5",
                "default": 5,
            },
        },
        "required": ["keyword"],
    },
    execute=_search_scripts_execute,
))


async def _get_product_info_execute(
    session: AsyncSession,
    product_name: str = "",
    product_id: int = 0,
) -> str:
    """Get product specifications, FAQ, and intro."""
    if product_id:
        product = await session.get(Product, product_id)
    elif product_name:
        result = await session.execute(
            select(Product).where(
                Product.name.like(f"%{product_name}%")
            ).limit(1)
        )
        product = result.scalar_one_or_none()
    else:
        return json.dumps({"error": "请提供 product_name 或 product_id"}, ensure_ascii=False)

    if not product:
        return json.dumps({"found": False, "message": "未找到该产品"}, ensure_ascii=False)

    return json.dumps({
        "found": True,
        "product": {
            "id": product.id,
            "name": product.name,
            "intro": (product.intro or "")[:800],
            "specs": product.specs or {},
            "faq": [
                {"q": faq.get("question", ""), "a": faq.get("answer", "")}
                for faq in (product.faq or [])[:5]
            ] if product.faq else [],
        },
    }, ensure_ascii=False)


GET_PRODUCT_INFO_TOOL = register_tool(ToolDef(
    name="get_product_info",
    description="查询产品信息。根据产品名称或ID获取产品规格、卖点、FAQ等详细信息，帮助在话术演练中准确介绍产品。",
    input_schema={
        "type": "object",
        "properties": {
            "product_name": {
                "type": "string",
                "description": "产品名称（模糊匹配）",
            },
            "product_id": {
                "type": "integer",
                "description": "产品ID（精确匹配）",
            },
        },
    },
    execute=_get_product_info_execute,
))


async def _get_methodology_execute(
    session: AsyncSession,
    keyword: str = "",
    limit: int = 3,
) -> str:
    """Retrieve relevant sales methodologies."""
    query = select(SalesMethodology).where(SalesMethodology.status == "published")
    if keyword:
        query = query.where(
            or_(
                SalesMethodology.title.like(f"%{keyword}%"),
                SalesMethodology.content.like(f"%{keyword}%"),
            )
        )
    query = query.order_by(SalesMethodology.id.desc()).limit(limit)
    result = await session.execute(query)
    methods = result.scalars().all()

    if not methods:
        return json.dumps({"found": 0, "message": "未找到相关方法论", "methodologies": []}, ensure_ascii=False)

    items = []
    for m in methods:
        items.append({
            "id": m.id,
            "title": m.title,
            "content": (m.content or "")[:600],
            "source": m.source or "",
        })

    return json.dumps({"found": len(items), "methodologies": items}, ensure_ascii=False)


GET_METHODOLOGY_TOOL = register_tool(ToolDef(
    name="get_methodology",
    description="获取销售方法论。根据关键词查找相关的销售方法论和最佳实践，为话术演练提供理论指导。",
    input_schema={
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "搜索关键词，如场景、技巧名称等",
            },
            "limit": {
                "type": "integer",
                "description": "返回数量上限，默认3",
                "default": 3,
            },
        },
    },
    execute=_get_methodology_execute,
))


async def _evaluate_response_execute(
    user_response: str,
    scenario: str = "",
    reference_scripts: str = "",
) -> str:
    """Evaluate the quality of a user's sales response with scenario-specific rules."""
    score = 3  # default neutral
    highlights: list[str] = []
    improvements: list[str] = []
    score_reasons: list[str] = []

    resp = user_response.strip()
    resp_len = len(resp)

    # ── Universal checks ──────────────────────────────────────────────
    if resp_len < 10:
        score = 1
        score_reasons.append("回复过短(-2)")
        improvements.append("尝试用更完整的话术回应客户")
    elif resp_len < 30:
        score = 2
        score_reasons.append("回复偏短(-1)")
        improvements.append("增加产品卖点或关怀语句，让回复更充实")
    elif resp_len > 200:
        score = min(5, score + 1)
        highlights.append("回复内容详实，信息量充足")

    # Polite keywords
    polite_kw = ["您好", "欢迎", "请问", "谢谢", "感谢", "请坐", "您请"]
    found_polite = [kw for kw in polite_kw if kw in resp]
    if found_polite:
        highlights.append(f"礼貌用语：{', '.join(found_polite)}")
        score_reasons.append(f"礼貌用语(+{len(found_polite)})")
        score = min(5, score + min(len(found_polite), 2))

    # Question technique
    if "？" in resp or "?" in resp:
        highlights.append("使用了提问技巧，主动了解顾客需求")
        score_reasons.append("提问技巧(+1)")
        score = min(5, score + 1)

    # ── Scenario-specific checks ──────────────────────────────────────

    if scenario == "reception":
        # Check 七步法 elements
        reception_checks = {
            "迎宾/问候": any(kw in resp for kw in ["欢迎光临", "您好", "你好"]),
            "引导/入座": any(kw in resp for kw in ["请坐", "这边坐", "这边请", "倒水"]),
            "了解来意": any(kw in resp for kw in ["请问您", "有什么需要", "想配", "想看"]),
            "需求挖掘": any(kw in resp for kw in ["用眼习惯", "平时", "预算", "之前戴", "场合"]),
        }
        done = [k for k, v in reception_checks.items() if v]
        missing = [k for k, v in reception_checks.items() if not v]
        if done:
            highlights.append(f"接待流程覆盖：{'、'.join(done)}")
            score_reasons.append(f"流程覆盖+{len(done)}")
            score = min(5, score + len(done))
        if missing:
            improvements.append(f"建议补充接待环节：{'、'.join(missing)}")

    elif scenario == "question":
        dims = ["用眼", "佩戴", "习惯", "预算", "场景", "不适", "时长", "度数", "需求"]
        covered = [d for d in dims if d in resp]
        if len(covered) >= 3:
            highlights.append(f"问诊覆盖多维度（{len(covered)}个）")
            score_reasons.append(f"多维问诊(+{min(len(covered), 3)})")
            score = min(5, score + min(len(covered), 3))
        elif len(covered) >= 1:
            improvements.append("建议从更多维度提问（用眼习惯、佩戴史、预算、使用场景等）")
        else:
            improvements.append("几乎没有问诊内容，建议主动了解顾客的用眼情况和需求")

    elif scenario == "product":
        # FAB check
        has_feature = any(kw in resp for kw in ["材质", "技术", "设计", "功能", "折射率", "膜层", "阿贝数"])
        has_advantage = any(kw in resp for kw in ["更轻", "更薄", "更清晰", "更好", "优于", "相比"])
        has_benefit = any(kw in resp for kw in ["对您来说", "您可以", "您就能", "帮您", "让您", "适合您"])
        fab_count = sum([has_feature, has_advantage, has_benefit])
        if fab_count >= 3:
            highlights.append("完整使用了 FAB 介绍法（特性→优势→利益）")
            score_reasons.append("FAB完整(+3)")
            score = min(5, score + 3)
        elif fab_count >= 2:
            highlights.append(f"部分使用了 FAB 法（{fab_count}/3 要素）")
            score = min(5, score + 2)
        elif fab_count == 1:
            improvements.append("建议用 FAB 法完整介绍：先说特性（是什么），再说优势（好在哪），最后讲利益（对您有什么用）")
        else:
            improvements.append("产品介绍缺少结构和卖点，建议用 FAB 法组织内容")

    elif scenario == "objection":
        has_understand = any(kw in resp for kw in ["理解", "确实", "明白您的", "我懂", "很多顾客", "您说得对"])
        has_turn = any(kw in resp for kw in ["不过", "但是", "其实", "让我给您", "您知道吗"])
        has_solve = any(kw in resp for kw in ["建议", "可以", "我们提供", "帮您", "方案", "保障"])
        ltz_count = sum([has_understand, has_turn, has_solve])
        if ltz_count >= 3:
            highlights.append("完美运用「理解+转折+解决」三步法处理异议")
            score_reasons.append("三步法完整(+3)")
            score = min(5, score + 3)
        elif ltz_count >= 2:
            highlights.append(f"部分运用了异议处理步骤（{ltz_count}/3）")
            score = min(5, score + 2)
        elif has_understand:
            improvements.append("先理解后别忘了转折引导和提供解决方案")
        else:
            improvements.append("异议处理建议使用三步法：先认可理解→再转折引导→最后提供解决方案")

        # Check specific objection types
        if "贵" in resp or "价格" in resp:
            if "价值" in resp or "品质" in resp or "售后" in resp or "保障" in resp:
                highlights.append("面对价格异议，用价值而非降价回应")
                score = min(5, score + 1)

    elif scenario == "closing":
        closing_techniques = {
            "假设成交": any(kw in resp for kw in ["帮您下单", "帮您订", "那就这", "我帮您"]),
            "二选一": any(kw in resp for kw in ["还是", "选哪个", "金色还", "A还是"]),
            "价值总结": any(kw in resp for kw in ["综合来看", "总结", "总的来说", "能满足"]),
            "限时/从众": any(kw in resp for kw in ["活动", "优惠", "最后", "很多顾客", "大家"]),
        }
        used = [k for k, v in closing_techniques.items() if v]
        if len(used) >= 2:
            highlights.append(f"灵活运用了多种促单技巧：{'、'.join(used)}")
            score_reasons.append(f"促单技巧+{len(used)}")
            score = min(5, score + len(used))
        elif len(used) == 1:
            improvements.append(f"尝试了{used[0]}，可以再结合其他促单技巧增强效果")
        else:
            improvements.append("面对犹豫顾客建议使用促单技巧：假设成交、二选一、限时优惠或价值总结")

    elif scenario == "fitting":
        fitting_steps = ["旧镜", "验光", "试戴", "挑选", "镜片", "取镜", "注意事项"]
        covered_steps = [s for s in fitting_steps if s in resp]
        if len(covered_steps) >= 3:
            highlights.append(f"验光配镜流程覆盖充分（{len(covered_steps)}个环节）")
            score_reasons.append(f"流程覆盖+{min(len(covered_steps), 4)}")
            score = min(5, score + min(len(covered_steps), 4))
        if not any(kw in resp for kw in ["试戴", "舒适", "感觉"]):
            improvements.append("验光后建议安排试戴并询问顾客感受")

    elif scenario == "aftercare":
        has_apology = any(kw in resp for kw in ["抱歉", "对不起", "不好意思", "理解您", "给您带来"])
        has_solution = any(kw in resp for kw in ["调整", "更换", "返厂", "维修", "免费", "帮您检"])
        has_followup = any(kw in resp for kw in ["保养", "复查", "有问题随时", "再联系", "新品", "活动"])

        if has_apology:
            highlights.append("售后开场先致歉安抚顾客情绪")
            score = min(5, score + 1)
        else:
            improvements.append("售后第一步应先道歉并安抚顾客情绪")

        if has_solution:
            highlights.append("给出了明确的解决方案")
            score = min(5, score + 1)
        else:
            improvements.append("需要给出具体可行的解决方案（调整/更换/返厂检测等）")

        if has_followup:
            highlights.append("售后服务中尝试了关系维护和后续跟进")
            score = min(5, score + 1)

    # ── Final score computation ────────────────────────────────────────
    if not highlights and not improvements:
        improvements.append("可以增加礼貌用语和主动提问，使回复更加专业")

    # Clamp score
    score = max(1, min(5, score))

    if score >= 5:
        feedback = "非常出色的回复！" + "；".join(score_reasons) if score_reasons else ""
        feedback += " 各项技能表现优秀，继续保持！"
    elif score >= 4:
        feedback = "不错的回复。" + "；".join(score_reasons) if score_reasons else ""
        feedback += " 还有小幅提升空间。"
    elif score >= 3:
        feedback = "回复尚可，有提升空间。" + "；".join(score_reasons) if score_reasons else ""
    else:
        feedback = "回复需要改进。" + "；".join(score_reasons) if score_reasons else ""
        feedback += " 请参考改进建议调整话术。"

    return json.dumps({
        "score": score,
        "max_score": 5,
        "feedback": feedback,
        "highlights": highlights if highlights else [],
        "improvements": improvements if improvements else [],
        "score_reasons": score_reasons,
    }, ensure_ascii=False)


EVALUATE_RESPONSE_TOOL = register_tool(ToolDef(
    name="evaluate_response",
    description="评估用户的销售话术回复质量。针对不同场景（接待/问诊/产品/异议/成交/验光/售后）有专项评分规则。对用户回复评分（1-5分），指出亮点、改进建议和加减分原因。在每一轮用户回复后应调用此工具。",
    input_schema={
        "type": "object",
        "properties": {
            "user_response": {
                "type": "string",
                "description": "用户的回复内容",
            },
            "scenario": {
                "type": "string",
                "description": "当前演练场景编码: reception/question/product/objection/closing/fitting/aftercare/general",
            },
            "reference_scripts": {
                "type": "string",
                "description": "可选，参考话术内容（从 search_scripts 获取）",
            },
        },
        "required": ["user_response", "scenario"],
    },
    execute=_evaluate_response_execute,
))


# ── Sales Master Knowledge Tool ────────────────────────────────────────────
# Progressive-disclosure knowledge base for 高境光镜片 sales training.
# References loaded on first access and cached.

from pathlib import Path as _Path

_knowledge_cache: dict[str, str] = {}
"""Module-level cache: topic → content snippet (lazy loaded)."""

# Resolve knowledge base path with fallback for edge cases
_KNOWLEDGE_BASE_PATH = _Path(__file__).resolve().parent.parent / "data" / "sales_master"
if not _KNOWLEDGE_BASE_PATH.exists():
    # Fallback: try relative to current working directory
    _cwd_path = _Path.cwd() / "backend" / "app" / "data" / "sales_master"
    if _cwd_path.exists():
        _KNOWLEDGE_BASE_PATH = _cwd_path
_QUESTION_BANK_PATH = _KNOWLEDGE_BASE_PATH / "references" / "question_bank.md"

# Topic → (file, heading_pattern) mapping for progressive disclosure
_TOPIC_MAP: dict[str, tuple[str, str]] = {
    "product": ("knowledge_base.md", "## 模块二：产品知识"),
    "mindset": ("knowledge_base.md", "## 模块一：销售心态建设"),
    "roi": ("knowledge_base.md", "## 模块三：ROI"),
    "visit": ("knowledge_base.md", "## 模块四：陌拜SOP"),
    "objection": ("knowledge_base.md", "## 模块五：异议处理"),
    "hard_numbers": ("knowledge_base.md", "## 硬数字速记"),
    "exam": ("question_bank.md", ""),  # special: random sample
    "all": ("knowledge_base.md", ""),  # entire knowledge base
}


def _load_file(file_name: str) -> str:
    """Load a reference file with caching."""
    key = f"file:{file_name}"
    if key not in _knowledge_cache:
        file_path = _KNOWLEDGE_BASE_PATH / "references" / file_name
        if not file_path.exists():
            file_path = _KNOWLEDGE_BASE_PATH / file_name
        if file_path.exists():
            _knowledge_cache[key] = file_path.read_text(encoding="utf-8")
        else:
            _knowledge_cache[key] = ""
    return _knowledge_cache[key]


def _extract_section(content: str, heading: str, max_chars: int = 2000) -> str:
    """Extract a section from markdown content by heading."""
    if not heading:
        return content[:max_chars]
    # Find the heading
    idx = content.find(heading)
    if idx == -1:
        # Try with ## prefix
        idx = content.find(f"## {heading}") if not heading.startswith("#") else -1
    if idx == -1:
        return content[:max_chars]  # fallback: return beginning
    # Find next ## heading (same or higher level)
    rest = content[idx:]
    next_h2 = rest.find("\n## ", len(heading) + 2)
    if next_h2 > 0:
        return rest[:next_h2].strip()[:max_chars]
    return rest.strip()[:max_chars]


def _pick_random_questions(content: str, count: int = 3) -> str:
    """Pick random questions from the question bank."""
    import re as _re
    # Split by question numbers (**1.**, **2.**, etc.)
    blocks = _re.split(r"\n(?=\*\*\d+\.)", content)
    questions = [b.strip() for b in blocks if b.strip() and _re.match(r"\*\*\d+\.", b.strip())]
    if len(questions) <= count:
        return "\n\n".join(questions)
    import random as _random
    chosen = _random.sample(questions, count)
    return "\n\n".join(chosen)


async def _load_sales_master_knowledge_execute(
    topic: str = "product",
    keyword: str = "",
) -> str:
    """Progressive-disclosure knowledge loader for sales master skill.

    Loads only the relevant section based on the requested topic.
    """
    import json as _json

    try:

        # Normalize topic: support Chinese and English
        topic_aliases: dict[str, str] = {
            "产品": "product", "产品知识": "product", "product": "product",
            "心态": "mindset", "心态建设": "mindset", "mindset": "mindset",
            "roi": "roi", "算账": "roi", "利润": "roi",
            "陌拜": "visit", "陌拜sop": "visit", "拜访": "visit", "visit": "visit",
            "异议": "objection", "异议处理": "objection", "objection": "objection",
            "硬数字": "hard_numbers", "数字": "hard_numbers", "参数": "hard_numbers",
            "hard_numbers": "hard_numbers",
            "考题": "exam", "考试": "exam", "题目": "exam", "exam": "exam",
            "全部": "all", "all": "all",
        }
        resolved = topic_aliases.get(topic.lower().strip(), "product")

        # ── Exam mode: random questions from question bank ───────────────
        if resolved == "exam":
            qb = _load_file("question_bank.md")
            if not qb:
                return _json.dumps({"found": False, "message": "题库文件未找到"}, ensure_ascii=False)
            # Filter by keyword if provided
            if keyword:
                lines = qb.split("\n")
                filtered: list[str] = []
                capture = False
                current_block = ""
                for line in lines:
                    if line.startswith("**") and "题）" not in line and line.strip().startswith("**"):
                        if capture and current_block.strip():
                            filtered.append(current_block.strip())
                        capture = keyword.lower() in line.lower()
                        current_block = line
                    elif capture:
                        current_block += "\n" + line
                if capture and current_block.strip():
                    filtered.append(current_block.strip())
                if filtered:
                    import random as _random2
                    chosen = _random2.sample(filtered, min(3, len(filtered)))
                    return _json.dumps({
                        "found": True, "topic": "exam", "count": len(chosen),
                        "questions": "\n\n".join(chosen),
                    }, ensure_ascii=False)

            questions_text = _pick_random_questions(qb, count=3)
            return _json.dumps({
                "found": True, "topic": "exam", "count": 3,
                "questions": questions_text,
            }, ensure_ascii=False)

        # ── Knowledge base mode ──────────────────────────────────────────
        mapping = _TOPIC_MAP.get(resolved)
        if not mapping:
            return _json.dumps({
                "found": False,
                "message": f"未知话题 '{topic}'。可选：产品/心态/ROI/陌拜/异议/硬数字/考题/全部",
            }, ensure_ascii=False)

        file_name, heading = mapping
        if resolved == "all":
            content = _load_file("knowledge_base.md")
            section = content[:4000]
        else:
            content = _load_file(file_name)
            section = _extract_section(content, heading, max_chars=2500)

        if not section:
            return _json.dumps({"found": False, "message": f"未找到 '{topic}' 相关内容"}, ensure_ascii=False)

        # Filter further by keyword if provided
        if keyword and resolved != "hard_numbers":
            lower_section = section.lower()
            kw_lower = keyword.lower()
            if kw_lower not in lower_section:
                # Try to find in full content
                full = _load_file(file_name)
                idx = full.lower().find(kw_lower)
                if idx > 0:
                    start = max(0, idx - 200)
                    end = min(len(full), idx + 1500)
                    section = full[start:end]

        return _json.dumps({
            "found": True,
            "topic": resolved,
            "topic_label": topic,
            "content": section,
        }, ensure_ascii=False)

    except Exception as _exc:
        return _json.dumps({
            "found": False,
            "error": f"工具内部错误: {str(_exc)}",
        }, ensure_ascii=False)


LOAD_SALES_MASTER_TOOL = register_tool(ToolDef(
    name="load_sales_master_knowledge",
    description="渐进式加载高境光镜片销售知识库。按话题返回对应的产品知识、销售方法论、心态建设、陌拜SOP、异议处理话术、ROI算账、硬数字速记或随机考题。当学员问到高境光镜片相关问题时主动调用。",
    input_schema={
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "查询话题：product(产品知识)/mindset(心态建设)/roi(ROI算账)/visit(陌拜SOP)/objection(异议处理)/hard_numbers(硬数字)/exam(随机考题)/all(全部)",
            },
            "keyword": {
                "type": "string",
                "description": "可选，在话题内进一步过滤的关键词",
            },
        },
        "required": ["topic"],
    },
    execute=_load_sales_master_knowledge_execute,
))
