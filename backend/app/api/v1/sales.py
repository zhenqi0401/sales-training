"""Sales-specific endpoints: dashboard, methodologies, audio files."""

from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.config import settings
from app.core.dependencies import CurrentUserDep, SessionDep, require_admin, require_sales, require_sales_or_admin
from app.models.sales_audio_file import SalesAudioFile
from app.models.sales_methodology import SalesMethodology
from app.models.user import User
from app.schemas.user import ApiResponse

router = APIRouter()

UPLOAD_DIR = Path(settings.upload_dir)
AUDIO_DIR = UPLOAD_DIR / "sales-audio"
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
MAX_AUDIO_SIZE = 200 * 1024 * 1024  # 200MB


def audio_envelope(data=None, message: str = "success") -> ApiResponse:
    return ApiResponse(message=message, data=data)


# ── Sales Dashboard ────────────────────────────────────────────────────────


@router.get("/dashboard", response_model=ApiResponse, summary="销售看板",
            dependencies=[Depends(require_sales_or_admin())])
async def get_sales_dashboard(session: SessionDep, user: CurrentUserDep):
    total_sales = (
        await session.execute(
            select(func.count()).select_from(User).where(User.role == "sales", User.is_active == True)
        )
    ).scalar() or 0

    total_audio = (
        await session.execute(select(func.count()).select_from(SalesAudioFile))
    ).scalar() or 0

    total_methodology = (
        await session.execute(
            select(func.count()).select_from(SalesMethodology).where(SalesMethodology.status == "published")
        )
    ).scalar() or 0

    return audio_envelope({
        "totalSales": total_sales,
        "totalAudioFiles": total_audio,
        "totalMethodologies": total_methodology,
    })


# ── Admin Sales List (with per-user methodologies) ──────────────────────────


class SalesUserItem(BaseModel):
    id: int
    username: str
    real_name: Optional[str] = ""
    avatar: Optional[str] = ""
    phone: Optional[str] = ""
    sales_count: int = 0
    deal_count: int = 0
    methodology_count: int = 0
    methodologies: list = []

    model_config = {"from_attributes": True}


@router.get("/admin/sales-list", response_model=ApiResponse, summary="管理员销售列表",
            dependencies=[Depends(require_sales_or_admin())])
async def admin_sales_list(session: SessionDep, user: CurrentUserDep):
    sales_users = (
        await session.execute(
            select(User).where(User.role == "sales", User.is_active == True).order_by(User.id)
        )
    ).scalars().all()

    result = []
    for su in sales_users:
        methodologies = (
            await session.execute(
                select(SalesMethodology)
                .where(
                    SalesMethodology.created_by == su.id,
                    SalesMethodology.status == "published",
                )
                .order_by(SalesMethodology.id.desc())
            )
        ).scalars().all()

        method_items = [
            {
                "id": m.id,
                "title": m.title,
                "content": m.content,
                "source": m.source or "",
                "created_at": m.created_at.isoformat() if m.created_at else "",
            }
            for m in methodologies
        ]

        result.append({
            "id": su.id,
            "username": su.username,
            "real_name": su.real_name or "",
            "avatar": su.avatar or "",
            "phone": su.phone or "",
            "sales_count": 0,
            "deal_count": 0,
            "methodology_count": len(methodologies),
            "methodologies": method_items,
        })

    return audio_envelope(result)


# ── Sales Methodologies ────────────────────────────────────────────────────


class MethodologyCreate(BaseModel):
    title: str
    content: str
    source: Optional[str] = "manual"
    tags: Optional[str] = ""
    status: Optional[str] = "published"


class MethodologyUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[str] = None
    status: Optional[str] = None


class MethodologyGenerateRequest(BaseModel):
    audio_file_id: int


class MethodologyGenerateResponse(BaseModel):
    title: str
    content: str
    source_audio_file_id: int


class MethodologyResponse(BaseModel):
    id: int
    title: str
    content: str
    source: Optional[str] = ""
    tags: Optional[str] = ""
    status: str
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.get("/methodologies", response_model=ApiResponse, summary="销售方法论列表",
            dependencies=[Depends(require_sales_or_admin())])
async def list_methodologies(session: SessionDep, user: CurrentUserDep, page: int = 1, page_size: int = 20):
    query = select(SalesMethodology).where(SalesMethodology.status == "published")
    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    items = (
        await session.execute(
            query.order_by(SalesMethodology.id.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()
    return audio_envelope({
        "total": total,
        "page": page,
        "pageSize": page_size,
        "items": [MethodologyResponse.model_validate(m).model_dump() for m in items],
    })


@router.get("/methodologies/{methodology_id}", response_model=ApiResponse, summary="销售方法论详情",
            dependencies=[Depends(require_sales_or_admin())])
async def get_methodology(methodology_id: int, session: SessionDep, user: CurrentUserDep):
    item = await session.get(SalesMethodology, methodology_id)
    if not item:
        raise HTTPException(status_code=404, detail="方法论不存在")
    return audio_envelope(MethodologyResponse.model_validate(item).model_dump())


@router.post("/methodologies/generate", response_model=ApiResponse, summary="AI生成方法论草稿",
             dependencies=[Depends(require_sales_or_admin())])
async def generate_methodology(body: MethodologyGenerateRequest, session: SessionDep, user: CurrentUserDep):
    audio_file = await session.get(SalesAudioFile, body.audio_file_id)
    if not audio_file:
        raise HTTPException(status_code=404, detail="语音文件不存在")
    if audio_file.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权访问此文件")

    if not settings.ai_api_key:
        # Placeholder when AI is not configured
        draft = MethodologyGenerateResponse(
            title=f"销售心得 - {audio_file.filename or '录音'}",
            content=f"（AI 未配置，此为占位方法论）\n\n基于录音文件 {audio_file.filename} 的分析，此处将展示大模型生成的方法论总结。内容包括：\n1. 销售话术亮点\n2. 客户沟通技巧\n3. 改进建议\n\n请配置 SALES_TRAINING_AI_API_KEY 后重试。",
            source_audio_file_id=body.audio_file_id,
        )
        return audio_envelope(draft.model_dump())

    try:
        from app.services.ai_service import call_methodology_llm, resolve_upload_path

        audio_path = resolve_upload_path(audio_file.file_url)
        if audio_path is None:
            raise HTTPException(status_code=400, detail="无法解析音频文件路径")

        result = await call_methodology_llm(audio_path)
        title = result["title"]
        content = result["content"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 生成失败: {str(e)}")

    draft = MethodologyGenerateResponse(
        title=title,
        content=content,
        source_audio_file_id=body.audio_file_id,
    )
    return audio_envelope(draft.model_dump())


@router.post("/methodologies", response_model=ApiResponse, status_code=201, summary="新建方法论",
             dependencies=[Depends(require_sales_or_admin())])
async def create_methodology(body: MethodologyCreate, session: SessionDep, user: CurrentUserDep):
    item = SalesMethodology(**body.model_dump(), created_by=user.id)
    session.add(item)
    await session.flush()
    return audio_envelope(MethodologyResponse.model_validate(item).model_dump())


@router.put("/methodologies/{methodology_id}", response_model=ApiResponse, summary="更新方法论",
            dependencies=[Depends(require_admin())])
async def update_methodology(methodology_id: int, body: MethodologyUpdate, session: SessionDep, user: CurrentUserDep):
    item = await session.get(SalesMethodology, methodology_id)
    if not item:
        raise HTTPException(status_code=404, detail="方法论不存在")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await session.flush()
    return audio_envelope(MethodologyResponse.model_validate(item).model_dump())


@router.delete("/methodologies/{methodology_id}", response_model=ApiResponse, summary="删除方法论",
               dependencies=[Depends(require_admin())])
async def delete_methodology(methodology_id: int, session: SessionDep, user: CurrentUserDep):
    item = await session.get(SalesMethodology, methodology_id)
    if not item:
        raise HTTPException(status_code=404, detail="方法论不存在")
    item.status = "archived"
    await session.flush()
    return audio_envelope(message="已删除")


# ── Sales Audio Files ──────────────────────────────────────────────────────


class AudioFileResponse(BaseModel):
    id: int
    user_id: int
    file_url: str
    filename: Optional[str] = ""
    duration: Optional[int] = 0
    file_size: Optional[int] = 0
    transcript: Optional[str] = ""
    summary: Optional[str] = ""
    methodology_id: Optional[int] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.post("/audio-files", response_model=ApiResponse, status_code=201, summary="上传销售语音文件",
             dependencies=[Depends(require_sales())])
async def upload_audio_file(
    session: SessionDep,
    user: CurrentUserDep,
    file: UploadFile = File(...),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="仅支持 mp3/wav/m4a/aac/ogg 格式")

    content = await file.read()
    if len(content) > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过 200MB 限制")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    out_path = AUDIO_DIR / f"{uuid.uuid4().hex}{ext}"
    out_path.write_bytes(content)

    record = SalesAudioFile(
        user_id=user.id,
        file_url=f"/uploads/sales-audio/{out_path.name}",
        filename=file.filename or out_path.name,
        file_size=len(content),
        status="uploaded",
    )
    session.add(record)
    await session.flush()
    return audio_envelope(AudioFileResponse.model_validate(record).model_dump())


@router.get("/audio-files/my", response_model=ApiResponse, summary="我的语音文件",
            dependencies=[Depends(require_sales())])
async def list_my_audio_files(session: SessionDep, user: CurrentUserDep, page: int = 1, page_size: int = 20):
    query = select(SalesAudioFile).where(SalesAudioFile.user_id == user.id)
    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    items = (
        await session.execute(
            query.order_by(SalesAudioFile.id.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()
    return audio_envelope({
        "total": total,
        "page": page,
        "pageSize": page_size,
        "items": [AudioFileResponse.model_validate(f).model_dump() for f in items],
    })


@router.get("/admin/audio-files", response_model=ApiResponse, summary="管理员查看全部语音文件",
            dependencies=[Depends(require_admin())])
async def list_all_audio_files(
    session: SessionDep,
    user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
    user_id: Optional[int] = None,
):
    query = select(SalesAudioFile)
    if user_id is not None:
        query = query.where(SalesAudioFile.user_id == user_id)
    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    items = (
        await session.execute(
            query.order_by(SalesAudioFile.id.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()
    return audio_envelope({
        "total": total,
        "page": page,
        "pageSize": page_size,
        "items": [AudioFileResponse.model_validate(f).model_dump() for f in items],
    })
