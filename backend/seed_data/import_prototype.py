#!/usr/bin/env python
"""Import training content from the legacy HTML prototype.

Usage:
    cd backend
    python -m seed_data.import_prototype
    python -m seed_data.import_prototype --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import html
import io
import re
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select, func

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory, engine
from app.models.base import Base
from app.models.category import Category
from app.models.product import Product
from app.models.question import Question
from app.models.script import Script


ROOT = Path(__file__).resolve().parents[2]
PROTOTYPE = ROOT / "to_c_training_v11.html"

MODULE_CATEGORIES = {
    "大师理论": ("prototype_masters", "大师理论"),
    "产品知识": ("prototype_products", "产品知识"),
    "进店接待": ("prototype_reception", "进店接待"),
    "SPIN提问": ("prototype_spin", "SPIN提问"),
    "价值传递": ("prototype_value", "价值传递"),
    "异议处理": ("prototype_objection", "异议处理"),
    "成交推进": ("prototype_close", "成交推进"),
    "售后维护": ("prototype_after", "售后维护"),
    "实战应用": ("prototype_practice", "实战应用"),
    "合规意识": ("prototype_compliance", "合规意识"),
    "其他": ("prototype_other", "其他"),
}

PRODUCT_CATEGORIES = {
    "青控": ("qingkong", "青控"),
    "斜弱视": ("xieruoshi", "斜弱视"),
    "角塑": ("jiaosu", "角塑"),
    "眼镜": ("yanjing", "眼镜"),
    "周边产品": ("zhoubian", "周边产品"),
    "功能性眼镜": ("gongneng", "功能性眼镜"),
    "竞品对比": ("competitor_compare", "竞品对比"),
}


def clean_text(value: str) -> str:
    value = re.sub(r"<\s*br\s*/?\s*>", "\n", value, flags=re.I)
    value = re.sub(r"</p\s*>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    value = value.replace("🗣️ 话术：**", "")
    value = value.replace("🗣️ 话术：", "")
    value = value.replace("推荐话术：", "")
    value = value.replace("**", "")
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = re.sub(r"[ \t]+", " ", value)
    return value.strip()


def js_unescape(value: str) -> str:
    return (
        value.replace(r"\/", "/")
        .replace(r"\"", '"')
        .replace(r"\'", "'")
        .replace(r"\n", "\n")
        .replace(r"\t", "\t")
        .replace(r"\\", "\\")
    )


def extract_js_string(obj: str, key: str) -> str | None:
    match = re.search(rf"\b{re.escape(key)}\s*:\s*\"", obj)
    if not match:
        return None

    i = match.end()
    chars: list[str] = []
    escaped = False
    while i < len(obj):
        ch = obj[i]
        if escaped:
            chars.append("\\" + ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == '"':
            return js_unescape("".join(chars))
        else:
            chars.append(ch)
        i += 1
    return None


def extract_js_int(obj: str, key: str) -> int | None:
    match = re.search(rf"\b{re.escape(key)}\s*:\s*(\d+)", obj)
    return int(match.group(1)) if match else None


def extract_js_string_array(obj: str, key: str) -> list[str]:
    match = re.search(rf"\b{re.escape(key)}\s*:\s*\[", obj)
    if not match:
        return []

    i = match.end()
    depth = 1
    chars: list[str] = []
    in_string = False
    escaped = False
    while i < len(obj) and depth:
        ch = obj[i]
        chars.append(ch)
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
        i += 1

    body = "".join(chars[:-1])
    values: list[str] = []
    pos = 0
    while pos < len(body):
        while pos < len(body) and body[pos] not in '"':
            pos += 1
        if pos >= len(body):
            break
        pos += 1
        item: list[str] = []
        escaped = False
        while pos < len(body):
            ch = body[pos]
            if escaped:
                item.append("\\" + ch)
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                pos += 1
                break
            else:
                item.append(ch)
            pos += 1
        values.append(js_unescape("".join(item)))
    return values


def find_js_object_blocks(source: str) -> list[str]:
    blocks: list[str] = []
    i = 0
    while i < len(source):
        if source[i] != "{":
            i += 1
            continue

        start = i
        depth = 0
        in_string = False
        escaped = False
        while i < len(source):
            ch = source[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        block = source[start : i + 1]
                        if re.search(r"\bq\s*:", block) and re.search(r"\bo\s*:", block):
                            blocks.append(block)
                        break
            i += 1
        i += 1
    return blocks


def js_section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        return ""
    start += len(start_marker)
    end = text.find(end_marker, start)
    return text[start:end] if end >= 0 else text[start:]


def extract_questions(text: str) -> list[dict[str, Any]]:
    sections = [
        ("module", js_section(text, "const moduleQuizzes = {", "\n};")),
        ("L1", js_section(text, "const l1Q=[", "\n];\nconst l2Q")),
        ("L2", js_section(text, "const l2Q=[", "\n];\nconst l3Q")),
        ("L3", js_section(text, "const l3Q=[", "\n];\n\nlet quizQuestions")),
    ]

    seen: set[str] = set()
    questions: list[dict[str, Any]] = []
    for level, section in sections:
        for block in find_js_object_blocks(section):
            content = extract_js_string(block, "q")
            options = extract_js_string_array(block, "o")
            answer_idx = extract_js_int(block, "a")
            if not content or not options or answer_idx is None or answer_idx >= len(options):
                continue

            module = extract_js_string(block, "m") or module_name_from_section(section, block) or "其他"
            explanation = extract_js_string(block, "e") or ""
            master = extract_js_string(block, "master") or ""
            key = content.strip()
            if key in seen:
                continue
            seen.add(key)

            option_map = {}
            for idx, option in enumerate(options):
                letter = chr(65 + idx)
                option_map[letter] = re.sub(r"^[A-Z]\)\s*", "", option).strip()

            questions.append(
                {
                    "content": content.strip(),
                    "type": "single",
                    "options": option_map,
                    "answer": chr(65 + answer_idx),
                    "analysis": (f"{master}\n{explanation}".strip() if master else explanation),
                    "difficulty": {"module": 2, "L1": 1, "L2": 3, "L3": 5}.get(level, 2),
                    "module": module,
                    "source": "prototype",
                    "tags": [tag for tag in ["prototype", level, module, master] if tag],
                }
            )
    return questions


def module_name_from_section(section: str, block: str) -> str | None:
    prefix = section[: section.find(block)]
    matches = list(re.finditer(r"(?m)^([a-zA-Z]+)\s*:\s*\[", prefix))
    if not matches:
        return None
    module_id = matches[-1].group(1)
    return {
        "masters": "大师理论",
        "products": "产品知识",
        "reception": "进店接待",
        "spin": "SPIN提问",
        "value": "价值传递",
        "objection": "异议处理",
        "close": "成交推进",
        "after": "售后维护",
    }.get(module_id)


def extract_div_blocks(text: str, class_name: str) -> list[str]:
    blocks: list[str] = []
    pattern = re.compile(rf'<div\b[^>]*class="[^"]*\b{re.escape(class_name)}\b[^"]*"[^>]*>', re.I)
    tag_re = re.compile(r"<div\b[^>]*>|</div\s*>", re.I)

    for match in pattern.finditer(text):
        depth = 0
        for tag in tag_re.finditer(text, match.start()):
            if tag.group(0).lower().startswith("<div"):
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    blocks.append(text[match.start() : tag.end()])
                    break
    return blocks


def inner_first(block: str, class_name: str) -> str:
    match = re.search(
        rf'<div\b[^>]*class="[^"]*\b{re.escape(class_name)}\b[^"]*"[^>]*>(.*?)</div>',
        block,
        flags=re.I | re.S,
    )
    return clean_text(match.group(1)) if match else ""


def extract_html_scripts(text: str) -> list[dict[str, Any]]:
    scripts: list[dict[str, Any]] = []

    for idx, block in enumerate(extract_div_blocks(text, "objection-card"), start=1):
        title = inner_first(block, "q")
        content = inner_first(block, "a")
        if title and content:
            scripts.append(
                {
                    "title": title[:256],
                    "category": "prototype_card",
                    "theory": "",
                    "content": content,
                    "tags": ["prototype", "html_card"],
                    "sort_order": idx,
                }
            )

    for idx, block in enumerate(extract_div_blocks(text, "script-box"), start=1):
        title = inner_first(block, "label") or f"原型话术 {idx}"
        content = inner_first(block, "text")
        if content:
            scripts.append(
                {
                    "title": title[:256],
                    "category": "prototype_script",
                    "theory": "",
                    "content": content,
                    "tags": ["prototype", "script_box"],
                    "sort_order": idx,
                }
            )

    objections = js_section(text, "const objections = [", "\n];\n\n// 渲染异议库")
    for idx, block in enumerate(find_js_object_blocks(objections), start=1):
        obj_id = extract_js_string(block, "id") or f"OBJ-{idx:03d}"
        question = extract_js_string(block, "q") or obj_id
        concern = extract_js_string(block, "concern") or ""
        answer = clean_text(extract_js_string(block, "a") or "")
        master = extract_js_string(block, "master") or ""
        tags = extract_js_string_array(block, "tags")
        if answer:
            scripts.append(
                {
                    "title": f"{obj_id} {question}"[:256],
                    "category": "objection",
                    "theory": master,
                    "content": answer,
                    "tags": ["prototype", concern, *tags],
                    "sort_order": idx,
                }
            )

    return dedupe_dicts(scripts, ("title", "content"))


def extract_products(text: str) -> list[dict[str, Any]]:
    section = text[text.find('<div id="sec-learn-products"') : text.find('<div id="sec-exam"')]
    products: list[dict[str, Any]] = []
    for idx, block in enumerate(extract_div_blocks(section, "product-card"), start=1):
        title_match = re.search(r"<h4[^>]*>(.*?)</h4>", block, flags=re.I | re.S)
        title = clean_text(title_match.group(1)) if title_match else f"原型产品 {idx}"
        title = re.sub(r"^[^\w\u4e00-\u9fff]+", "", title).strip()
        content = clean_text(block)
        if title and content:
            products.append(
                {
                    "name": title[:256],
                    "intro": content[:12000],
                    "specs": {"source": "to_c_training_v11.html"},
                    "faq": None,
                    "compare_data": None,
                    "sort_order": idx,
                    "category_name": match_product_category(title),
                }
            )
    return dedupe_dicts(products, ("name",))


def match_product_category(title: str) -> str:
    for name in PRODUCT_CATEGORIES:
        if name in title:
            return name
    return "青控"


def dedupe_dicts(items: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        marker = tuple(item.get(key) for key in keys)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(item)
    return result


async def get_or_create_category(session, code: str, name: str) -> Category:
    existing = (await session.execute(select(Category).where(Category.code == code))).scalar_one_or_none()
    if existing:
        if existing.name != name:
            existing.name = name
        return existing

    category = Category(name=name, code=code, sort_order=0, is_active=True)
    session.add(category)
    await session.flush()
    return category


async def import_content(dry_run: bool = False) -> None:
    text = PROTOTYPE.read_text(encoding="utf-8")
    questions = extract_questions(text)
    scripts = extract_html_scripts(text)
    products = extract_products(text)

    print(f"Parsed from prototype: {len(questions)} questions, {len(scripts)} scripts, {len(products)} products")
    if dry_run:
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        category_by_module: dict[str, Category] = {}
        for module, (code, name) in MODULE_CATEGORIES.items():
            category_by_module[module] = await get_or_create_category(session, code, name)

        product_category_by_name: dict[str, Category] = {}
        for key, (code, name) in PRODUCT_CATEGORIES.items():
            product_category_by_name[key] = await get_or_create_category(session, code, name)

        inserted_products = 0
        for item in products:
            existing = (
                await session.execute(select(Product).where(Product.name == item["name"]))
            ).scalar_one_or_none()
            if existing:
                continue
            category = product_category_by_name.get(item.pop("category_name"), product_category_by_name["青控"])
            session.add(Product(**item, category_id=category.id, is_active=True))
            inserted_products += 1

        inserted_scripts = 0
        for item in scripts:
            existing = (
                await session.execute(
                    select(Script).where(Script.title == item["title"], Script.content == item["content"])
                )
            ).scalar_one_or_none()
            if existing:
                continue
            session.add(Script(**item, is_active=True))
            inserted_scripts += 1

        inserted_questions = 0
        for item in questions:
            existing = (
                await session.execute(select(Question).where(Question.content == item["content"]))
            ).scalar_one_or_none()
            if existing:
                continue
            module = item.pop("module")
            category = category_by_module.get(module, category_by_module["其他"])
            session.add(Question(**item, category_id=category.id, is_active=True))
            inserted_questions += 1

        await session.commit()

        totals = {
            "products": await session.scalar(select(func.count()).select_from(Product).where(Product.is_active == True)),
            "scripts": await session.scalar(select(func.count()).select_from(Script).where(Script.is_active == True)),
            "questions": await session.scalar(select(func.count()).select_from(Question).where(Question.is_active == True)),
        }

    print(
        "Inserted: "
        f"{inserted_questions} questions, {inserted_scripts} scripts, {inserted_products} products"
    )
    print(
        "Active totals: "
        f"{totals['questions']} questions, {totals['scripts']} scripts, {totals['products']} products"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Parse only; do not write to database")
    args = parser.parse_args()
    asyncio.run(import_content(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
