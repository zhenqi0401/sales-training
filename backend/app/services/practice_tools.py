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
    """Evaluate the quality of a user's sales response.

    This tool returns a structured evaluation with score, feedback,
    highlights, and improvement suggestions. The actual evaluation
    logic is simple rules-based here; in production this would be
    an LLM sub-call.
    """
    score = 3  # default neutral
    highlights: list[str] = []
    improvements: list[str] = []
    feedback_parts: list[str] = []

    # Basic heuristics (lightweight; LLM evaluation happens in agent loop)
    resp_len = len(user_response.strip())
    if resp_len < 10:
        score = 1
        feedback_parts.append("回复过于简短，建议展开说明")
        improvements.append("尝试用更完整的话术回应客户")
    elif resp_len < 30:
        score = 2
        feedback_parts.append("回复偏短，可以补充更多信息")
        improvements.append("增加产品卖点或关怀语句")
    elif resp_len > 200:
        score = 4
        feedback_parts.append("回复内容详实")
        highlights.append("内容充分")

    # Check for key sales phrases
    keywords_present = []
    for kw in ["您好", "欢迎", "请问", "谢谢", "感谢"]:
        if kw in user_response:
            keywords_present.append(kw)
    if keywords_present:
        highlights.append(f"使用了礼貌用语：{', '.join(keywords_present)}")
        score = min(5, score + 1)

    if "？" in user_response or "?" in user_response:
        highlights.append("使用了提问技巧，主动了解顾客需求")
        score = min(5, score + 1)

    # Scenario-specific checks
    if scenario == "objection" and any(w in user_response for w in ["理解", "确实", "不过", "但是"]):
        highlights.append("异议处理中使用了「理解+转折」技巧")

    if not highlights:
        improvements.append("可以增加礼貌用语和主动提问")
    if "价格" in scenario.lower() and "价格" not in user_response:
        improvements.append("涉及价格场景时，建议先强调价值再谈价格")

    # Compute final score
    if score >= 5:
        feedback = "非常出色的回复！" + " ".join(feedback_parts)
    elif score >= 4:
        feedback = "不错的回复。" + " ".join(feedback_parts)
    elif score >= 3:
        feedback = "回复尚可，有提升空间。" + " ".join(feedback_parts)
    else:
        feedback = "回复需要改进。" + " ".join(feedback_parts)

    return json.dumps({
        "score": score,
        "max_score": 5,
        "feedback": feedback,
        "highlights": highlights if highlights else [],
        "improvements": improvements if improvements else [],
    }, ensure_ascii=False)


EVALUATE_RESPONSE_TOOL = register_tool(ToolDef(
    name="evaluate_response",
    description="评估用户的销售话术回复质量。对用户的回复进行评分（1-5分），指出亮点和改进建议。在每一轮用户回复后应调用此工具。",
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
