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


@router.post("/methodologies", response_model=ApiResponse, status_code=201, summary="新建方法论",
             dependencies=[Depends(require_admin())])
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
