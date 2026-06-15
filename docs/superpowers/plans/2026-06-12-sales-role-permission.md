# Sales Role & Permission Adjustment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一系统角色为 `admin` / `sales` / `student` 三种，在后端强化接口权限隔离，在管理端和培训端对应调整前端角色校验、菜单、用户管理 UI，并新增销售看板、销售方法论、销售语音文件、Agent 话术演练入口。

**Architecture:** 后端新增 `require_admin` / `require_training_user` / `require_sales` / `require_sales_or_admin` 依赖函数，并把各路由上已有的 `require_role("super_admin","training_admin")` 统一换成 `require_admin`；新增三张数据库表（sales_dashboard、sales_methodologies、sales_audio_files）及对应路由模块；前端管理端在路由守卫中检查 `role === 'admin'`；培训端在路由守卫中检查 `role in ['sales','student']`，TabBar / 菜单根据角色动态展示，实战演练页顶部增加 Agent 话术演练入口卡片。

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy 2.0 (async) / Alembic / Vue 3 / Vant / Element Plus / TypeScript

---

## 文件变更总览

### 后端

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/core/dependencies.py` | 修改 | 新增 `require_admin`、`require_training_user`、`require_sales`、`require_sales_or_admin` |
| `backend/app/models/user.py` | 修改 | 更新 role 注释 |
| `backend/app/models/sales_audio_file.py` | 新建 | 销售语音文件表 |
| `backend/app/models/sales_methodology.py` | 新建 | 销售方法论表 |
| `backend/app/models/__init__.py` | 修改 | 导出新模型 |
| `backend/app/api/v1/users.py` | 修改 | `require_admin` 替换旧权限 |
| `backend/app/api/v1/stores.py` | 修改 | `require_admin` 替换旧权限 |
| `backend/app/api/v1/categories.py` | 修改 | 写操作加 `require_admin` |
| `backend/app/api/v1/videos.py` | 修改 | 写操作加 `require_admin` |
| `backend/app/api/v1/scripts.py` | 修改 | 写操作加 `require_admin` |
| `backend/app/api/v1/products.py` | 修改 | 写操作加 `require_admin` |
| `backend/app/api/v1/questions.py` | 修改 | 全部操作加 `require_admin` |
| `backend/app/api/v1/exam_papers.py` | 修改 | 全部操作加 `require_admin` |
| `backend/app/api/v1/dashboard.py` | 修改 | `admin-overview` 加 `require_admin` |
| `backend/app/api/v1/sales.py` | 新建 | 销售看板、方法论、语音文件接口 |
| `backend/app/api/v1/router.py` | 修改 | 注册 sales 路由 |
| `backend/app/schemas/user.py` | 修改 | UserCreate/UserUpdate role 校验；TrainingUserResponse 新增 role 字段 |
| `backend/app/api/v1/auth.py` | 修改 | send-code / phone-login 允许 sales+student；login 接口管理端 role 校验移至前端 |
| `backend/alembic/versions/c01_role_unify_sales_tables.py` | 新建 | 迁移旧角色值 + 新建三张销售表 |
| `backend/seed_data/seed_all.py` | 修改 | 更新测试账户角色为新枚举 |

### 管理端 (admin-web)

| 文件 | 操作 | 说明 |
|------|------|------|
| `admin-web/src/types/index.ts` | 修改 | UserInfo.role 类型改为 `'admin'` |
| `admin-web/src/router/index.ts` | 修改 | 路由守卫：非 admin 跳转无权限页 |
| `admin-web/src/stores/app.ts` | 修改 | 用户管理菜单改为管理员/销售/学员 |
| `admin-web/src/views/users/index.vue` | 修改 | 角色筛选选项、创建/编辑角色选项 |
| `admin-web/src/views/users/detail.vue` | 修改 | 角色 Tag 显示 |

### 培训端 (training-web)

| 文件 | 操作 | 说明 |
|------|------|------|
| `training-web/src/types/index.ts` | 修改 | UserInfo 新增 `role` 字段 |
| `training-web/src/stores/auth-user.ts` | 修改 | normalizeTrainingUser 保留 role 字段 |
| `training-web/src/stores/auth.ts` | 修改 | 暴露 `userRole` computed |
| `training-web/src/router/index.ts` | 修改 | 路由守卫：非 sales/student 跳转；sales 专属路由加 requireSales meta |
| `training-web/src/components/layout/TabBar.vue` | 修改 | 根据角色动态添加销售看板/销售方法论 tab |
| `training-web/src/views/practice/index.vue` | 修改 | 顶部增加 Agent 话术演练入口卡片 |
| `training-web/src/views/sales/dashboard.vue` | 新建 | 销售看板页面 |
| `training-web/src/views/sales/methodology.vue` | 新建 | 销售方法论页面 |
| `training-web/src/api/sales.ts` | 新建 | 销售相关 API 调用 |

---

## Task 1: 后端 — 统一角色权限依赖函数

**Files:**
- Modify: `backend/app/core/dependencies.py`

- [ ] **Step 1: 在 dependencies.py 末尾新增四个权限依赖**

```python
# 在文件末尾 require_role 之后追加：

def require_admin():
    """Only allow admin role."""
    return require_role("admin")


def require_training_user():
    """Allow sales and student roles (training-web users)."""
    return require_role("sales", "student")


def require_sales():
    """Only allow sales role."""
    return require_role("sales")


def require_sales_or_admin():
    """Allow sales (read) and admin (manage)."""
    return require_role("sales", "admin")
```

- [ ] **Step 2: 验证无语法错误**

```bash
cd backend && python -c "from app.core.dependencies import require_admin, require_training_user, require_sales, require_sales_or_admin; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/dependencies.py
git commit -m "feat(backend): add require_admin/training_user/sales/sales_or_admin dependencies"
```

---

## Task 2: 后端 — 修改管理接口使用 require_admin

**Files:**
- Modify: `backend/app/api/v1/users.py:17`
- Modify: `backend/app/api/v1/stores.py:52`

- [ ] **Step 1: 修改 users.py — 替换路由级权限**

将 `users.py` 第 17 行：
```python
router = APIRouter(dependencies=[Depends(require_role("super_admin", "training_admin"))])
```
改为：
```python
router = APIRouter(dependencies=[Depends(require_admin())])
```

同时在文件顶部导入 `require_admin`（替换原 `require_role` 导入，若 `require_role` 还有其他用处则保留并追加）：
```python
from app.core.dependencies import CurrentUserDep, SessionDep, require_admin
```

- [ ] **Step 2: 修改 stores.py — 替换路由级权限**

将 `stores.py` 第 10 行导入改为：
```python
from app.core.dependencies import CurrentUserDep, SessionDep, require_admin
```

将 `stores.py` 第 52 行：
```python
router = APIRouter(dependencies=[Depends(require_role("super_admin", "training_admin"))])
```
改为：
```python
router = APIRouter(dependencies=[Depends(require_admin())])
```

- [ ] **Step 3: 验证导入无错误**

```bash
cd backend && python -c "from app.api.v1 import users, stores; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/users.py backend/app/api/v1/stores.py
git commit -m "feat(backend): restrict /users and /stores to admin only"
```

---

## Task 3: 后端 — 修改 categories / videos / scripts / products / questions / exam_papers / dashboard 接口权限

**Files:**
- Modify: `backend/app/api/v1/categories.py`
- Modify: `backend/app/api/v1/videos.py`
- Modify: `backend/app/api/v1/scripts.py`
- Modify: `backend/app/api/v1/products.py`
- Modify: `backend/app/api/v1/questions.py`
- Modify: `backend/app/api/v1/exam_papers.py`
- Modify: `backend/app/api/v1/dashboard.py`

**设计思路：**
- `categories`, `videos`, `products`：GET（读取）对 training_user 开放，写操作（POST/PUT/DELETE）限 admin。
- `scripts`：GET 对 training_user 开放，写操作限 admin。
- `questions`, `exam_papers`：全部限 admin（培训端通过 `/exams` 路由答题，不直接访问这两个模块）。
- `dashboard`：`/admin-overview` 和 `/student-progress-export` 限 admin；`/stats` 和 `/student-progress-export` 需登录即可（training_user 可读）。

- [ ] **Step 1: 修改 categories.py — 写操作加 admin 权限**

在 `categories.py` 顶部导入处追加：
```python
from fastapi import Depends
from app.core.dependencies import require_admin
```

将 `create_category`、`update_category`、`delete_category` 三个函数的路由装饰器改为添加 `dependencies`，例如：
```python
@router.post("/", response_model=CategoryResponse, status_code=201, summary="创建分类",
             dependencies=[Depends(require_admin())])
async def create_category(...):
    ...

@router.put("/{category_id}", response_model=CategoryResponse, summary="更新分类",
            dependencies=[Depends(require_admin())])
async def update_category(...):
    ...

@router.delete("/{category_id}", response_model=MessageResponse, summary="删除分类",
               dependencies=[Depends(require_admin())])
async def delete_category(...):
    ...
```

- [ ] **Step 2: 修改 videos.py — 写操作加 admin 权限**

在 `videos.py` 顶部导入处追加（`Depends` 已存在，追加 `require_admin`）：
```python
from app.core.dependencies import CurrentUserDep, SessionDep, require_admin
```

将以下路由装饰器追加 `dependencies=[Depends(require_admin())]`：
- `create_video` (POST /)
- `update_video` (PUT /{video_id})
- `update_video_status` (PUT /{video_id}/status)
- `batch_update_video_status` (POST /batch/status)
- `delete_video` (DELETE /{video_id})

- [ ] **Step 3: 修改 scripts.py — 写操作加 admin 权限**

在 `scripts.py` 顶部导入处追加：
```python
from fastapi import Depends
from app.core.dependencies import require_admin
```

将 `create_script`、`update_script`、`delete_script` 添加 `dependencies=[Depends(require_admin())]`。

- [ ] **Step 4: 修改 products.py — 写操作加 admin 权限**

在 `products.py` 顶部导入处追加：
```python
from fastapi import Depends
from app.core.dependencies import require_admin
```

将 `create_product`、`update_product`、`delete_product` 添加 `dependencies=[Depends(require_admin())]`。

- [ ] **Step 5: 修改 questions.py — 全部操作限 admin**

在 `questions.py` 顶部将路由创建改为：
```python
from app.core.dependencies import CurrentUserDep, SessionDep, require_admin
router = APIRouter(dependencies=[Depends(require_admin())])
```
并在文件顶部已有 `from fastapi import APIRouter, HTTPException` 后追加 `Depends`。

- [ ] **Step 6: 修改 exam_papers.py — 全部操作限 admin**

在 `exam_papers.py` 顶部：
```python
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import CurrentUserDep, SessionDep, require_admin
router = APIRouter(dependencies=[Depends(require_admin())])
```

- [ ] **Step 7: 修改 dashboard.py — admin-overview 和 export 限 admin**

在 `dashboard.py` 顶部导入处追加：
```python
from fastapi import Depends
from app.core.dependencies import require_admin
```

将 `get_admin_overview` 和 `export_student_progress` 两个路由装饰器追加 `dependencies=[Depends(require_admin())]`：
```python
@router.get("/admin-overview", summary="管理员数据概览",
            dependencies=[Depends(require_admin())])
async def get_admin_overview(session: SessionDep, user: CurrentUserDep):
    ...

@router.get("/student-progress-export", summary="导出学员学习进度",
            dependencies=[Depends(require_admin())])
async def export_student_progress(session: SessionDep, user: CurrentUserDep):
    ...
```

- [ ] **Step 8: 验证所有修改后导入正常**

```bash
cd backend && python -c "from app.api.v1 import categories, videos, scripts, products, questions, exam_papers, dashboard; print('OK')"
```

Expected: `OK`

- [ ] **Step 9: Commit**

```bash
git add backend/app/api/v1/categories.py backend/app/api/v1/videos.py backend/app/api/v1/scripts.py backend/app/api/v1/products.py backend/app/api/v1/questions.py backend/app/api/v1/exam_papers.py backend/app/api/v1/dashboard.py
git commit -m "feat(backend): restrict admin-only write endpoints and dashboard overview"
```

---

## Task 4: 后端 — 修复 auth.py 中硬编码的 role == "student" 检查

**Files:**
- Modify: `backend/app/api/v1/auth.py:172-173` (send-code)
- Modify: `backend/app/api/v1/auth.py:211-212` (phone-login)

培训端支持 `sales` 和 `student` 都能用手机号登录。

- [ ] **Step 1: 修改 send-code 接口的角色判断**

将 `auth.py` 中 `send_code` 函数内：
```python
    if user is None or user.role != "student":
        raise HTTPException(status_code=404, detail="学员账号不存在")
```
改为：
```python
    if user is None or user.role not in ("sales", "student"):
        raise HTTPException(status_code=404, detail="培训账号不存在")
```

- [ ] **Step 2: 修改 phone-login 接口的角色判断**

将 `auth.py` 中 `phone_login` 函数内：
```python
    if user is None or user.role != "student":
        raise HTTPException(status_code=404, detail="学员账号不存在")
```
改为：
```python
    if user is None or user.role not in ("sales", "student"):
        raise HTTPException(status_code=404, detail="培训账号不存在")
```

- [ ] **Step 3: 在 TrainingUserResponse 中新增 role 字段**

在 `backend/app/schemas/user.py` 的 `TrainingUserResponse` 类中新增 `role` 字段：
```python
class TrainingUserResponse(BaseModel):
    id: int
    name: str
    phone: str
    avatar: str = ""
    storeName: str = ""
    joinDate: str = ""
    level: int = 1
    point: int = 0
    mustChangePassword: bool = False
    role: str = "student"   # 新增
```

- [ ] **Step 4: 在 auth.py 的 `_to_training_user` 函数中填充 role**

将 `_to_training_user` 函数改为：
```python
def _to_training_user(user: User) -> TrainingUserResponse:
    join_date = user.created_at.date().isoformat() if user.created_at else ""
    return TrainingUserResponse(
        id=user.id,
        name=user.real_name or user.username,
        phone=user.phone,
        avatar=user.avatar or "",
        storeName="",
        joinDate=join_date,
        level=1,
        point=0,
        mustChangePassword=_get_user_must_change_password(user),
        role=user.role,
    )
```

- [ ] **Step 5: 验证**

```bash
cd backend && python -c "from app.api.v1.auth import _to_training_user; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/auth.py backend/app/schemas/user.py
git commit -m "feat(backend): allow sales role in phone login; add role to TrainingUserResponse"
```

---

## Task 5: 后端 — 新建销售模型（SalesMethodology、SalesAudioFile）

**Files:**
- Create: `backend/app/models/sales_methodology.py`
- Create: `backend/app/models/sales_audio_file.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建 sales_methodology.py**

```python
"""Sales methodology model."""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SalesMethodology(Base, TimestampMixin):
    __tablename__ = "sales_methodologies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(64), default="manual")
    source_audio_file_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="published")
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
```

- [ ] **Step 2: 创建 sales_audio_file.py**

```python
"""Sales audio file model."""
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SalesAudioFile(Base, TimestampMixin):
    __tablename__ = "sales_audio_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[Optional[str]] = mapped_column(String(256), default="")
    duration: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    transcript: Mapped[Optional[str]] = mapped_column(Text, default="")
    summary: Mapped[Optional[str]] = mapped_column(Text, default="")
    methodology_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="uploaded")
```

- [ ] **Step 3: 修改 models/__init__.py**

查看当前 `__init__.py` 内容，追加两行导入：
```python
from app.models.sales_methodology import SalesMethodology
from app.models.sales_audio_file import SalesAudioFile
```

- [ ] **Step 4: 验证**

```bash
cd backend && python -c "from app.models.sales_methodology import SalesMethodology; from app.models.sales_audio_file import SalesAudioFile; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/sales_methodology.py backend/app/models/sales_audio_file.py backend/app/models/__init__.py
git commit -m "feat(backend): add SalesMethodology and SalesAudioFile models"
```

---

## Task 6: 后端 — 新建 Alembic 迁移（角色统一 + 新表）

**Files:**
- Create: `backend/alembic/versions/c01_role_unify_sales_tables.py`

- [ ] **Step 1: 创建迁移文件**

```python
"""Unify user roles and add sales tables."""

from alembic import op
import sqlalchemy as sa

revision = "c01_role_unify_sales_tables"
down_revision = "b01_user_must_change_password"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # --- 1. Migrate legacy role values ---
    op.execute(
        "UPDATE users SET role = 'admin' WHERE role IN ('super_admin', 'training_admin', 'instructor')"
    )

    # --- 2. Create sales_methodologies table ---
    if "sales_methodologies" not in tables:
        op.create_table(
            "sales_methodologies",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("title", sa.String(256), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("source", sa.String(64), default="manual"),
            sa.Column("source_audio_file_id", sa.Integer(), nullable=True),
            sa.Column("tags", sa.Text(), default=""),
            sa.Column("status", sa.String(32), default="published"),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )

    # --- 3. Create sales_audio_files table ---
    if "sales_audio_files" not in tables:
        op.create_table(
            "sales_audio_files",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("file_url", sa.String(512), nullable=False),
            sa.Column("filename", sa.String(256), default=""),
            sa.Column("duration", sa.Integer(), default=0),
            sa.Column("file_size", sa.Integer(), default=0),
            sa.Column("transcript", sa.Text(), default=""),
            sa.Column("summary", sa.Text(), default=""),
            sa.Column("methodology_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(32), default="uploaded"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("sales_audio_files")
    op.drop_table("sales_methodologies")
```

- [ ] **Step 2: 验证文件语法**

```bash
cd backend && python -c "import alembic; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/c01_role_unify_sales_tables.py
git commit -m "feat(backend): migration — unify roles + add sales_methodologies and sales_audio_files"
```

---

## Task 7: 后端 — 新建 sales.py API 路由

**Files:**
- Create: `backend/app/api/v1/sales.py`
- Modify: `backend/app/api/v1/router.py`

- [ ] **Step 1: 创建 sales.py**

```python
"""Sales-specific endpoints: dashboard, methodologies, audio files."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, func

from app.core.config import settings
from app.core.dependencies import CurrentUserDep, SessionDep, require_admin, require_sales, require_sales_or_admin
from app.models.sales_methodology import SalesMethodology
from app.models.sales_audio_file import SalesAudioFile
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
```

- [ ] **Step 2: 在 router.py 注册 sales 路由**

在 `router.py` 的 import 处追加：
```python
from app.api.v1 import sales
```
在 `router.include_router(dashboard.router, ...)` 后追加：
```python
router.include_router(sales.router, prefix="/sales", tags=["销售功能"])
```

- [ ] **Step 3: 验证**

```bash
cd backend && python -c "from app.api.v1.router import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/sales.py backend/app/api/v1/router.py
git commit -m "feat(backend): add sales dashboard, methodologies, and audio files API"
```

---

## Task 8: 后端 — 更新种子数据账号角色

**Files:**
- Modify: `backend/seed_data/seed_all.py`

- [ ] **Step 1: 修改 ADMINS 列表中的旧角色**

将 `seed_all.py` 第 35-42 行的 ADMINS 列表改为：
```python
ADMINS = [
    {"username": "admin", "phone": "13800000000", "password": "admin123",
     "real_name": "超级管理员", "role": "admin"},
    {"username": "admin2", "phone": "13800000001", "password": "admin123",
     "real_name": "培训管理员", "role": "admin"},
    {"username": "sales1", "phone": "13800000002", "password": "sales123",
     "real_name": "张销售", "role": "sales"},
    {"username": "student", "phone": "13800000003", "password": "student123",
     "real_name": "李学员", "role": "student"},
]
```

- [ ] **Step 2: Commit**

```bash
git add backend/seed_data/seed_all.py
git commit -m "feat(backend): update seed accounts to use unified role values"
```

---

## Task 9: 管理端 — 类型定义 & 路由守卫角色校验

**Files:**
- Modify: `admin-web/src/types/index.ts:9`
- Modify: `admin-web/src/router/index.ts`
- Modify: `admin-web/src/stores/auth.ts`

- [ ] **Step 1: 修改 types/index.ts — UserInfo.role 类型**

将第 9 行：
```typescript
  role: 'admin' | 'trainer' | 'student'
```
改为：
```typescript
  role: 'admin' | 'sales' | 'student'
```

- [ ] **Step 2: 修改 stores/auth.ts — 登录后暴露 role 辅助 getter**

在 `isLoggedIn` computed 后追加：
```typescript
  const isAdmin = computed(() => userInfo.value?.role === 'admin')
```
并在 return 对象中包含 `isAdmin`。

- [ ] **Step 3: 修改 router/index.ts — 登录后检查是否为 admin**

将 `getToken` 函数改为同时读取 role：
```typescript
function getAuthInfo(): { token: string | null; role: string | null } {
  try {
    const raw = localStorage.getItem('auth-store')
    if (!raw) return { token: null, role: null }
    const parsed = JSON.parse(raw)
    return { token: parsed.token || null, role: parsed.role || null }
  } catch {
    return { token: null, role: null }
  }
}
```

在路由守卫 `router.beforeEach` 中，认证通过后增加 role 校验：
```typescript
router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || ''} - 销售培训系统`

  if (to.meta.noAuth) {
    next()
    return
  }

  const { token, role } = getAuthInfo()
  if (!token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  // 管理端只允许 admin
  if (role && role !== 'admin') {
    next({ path: '/login', query: { error: 'no_permission' } })
    return
  }

  next()
})
```

- [ ] **Step 4: 修改 stores/auth.ts — login 时保存 role 到 localStorage**

将 `localStorage.setItem('auth-store', ...)` 改为包含 role：
```typescript
localStorage.setItem('auth-store', JSON.stringify({ token: t, role: user.role }))
```

- [ ] **Step 5: Commit**

```bash
git add admin-web/src/types/index.ts admin-web/src/router/index.ts admin-web/src/stores/auth.ts
git commit -m "feat(admin-web): restrict management portal to admin role only"
```

---

## Task 10: 管理端 — 用户管理 UI 调整（角色选项改为管理员/销售/学员）

**Files:**
- Modify: `admin-web/src/stores/app.ts`
- Modify: `admin-web/src/views/users/index.vue`
- Modify: `admin-web/src/views/users/detail.vue`

- [ ] **Step 1: 修改 app.ts — 用户管理菜单**

将 `menuItems` 中用户管理子菜单改为：
```typescript
{
  title: '用户管理',
  icon: 'User',
  path: '',
  children: [
    { title: '管理员', icon: 'UserFilled', path: '/users?role=admin' },
    { title: '销售管理', icon: 'TrendCharts', path: '/users?role=sales' },
    { title: '学员管理', icon: 'User', path: '/users?role=student' },
  ],
},
```

- [ ] **Step 2: 修改 users/index.vue — 筛选下拉和创建表单角色选项**

将搜索区的角色 el-option 改为：
```html
<el-option label="管理员" value="admin" />
<el-option label="销售" value="sales" />
<el-option label="学员" value="student" />
```

将创建/编辑弹窗中的角色 el-option 改为（移除培训师）：
```html
<el-option label="管理员" value="admin" />
<el-option label="销售" value="sales" />
<el-option label="学员" value="student" />
```

将列表中角色 Tag 显示改为：
```html
<el-tag v-if="row.role === 'admin'" type="danger" size="small">管理员</el-tag>
<el-tag v-else-if="row.role === 'sales'" type="warning" size="small">销售</el-tag>
<el-tag v-else type="info" size="small">学员</el-tag>
```

将 `userForm` 初始值 `role` 保持 `'student'` 不变（或改为默认 `'sales'` 视业务需要，保持 `'student'`）。

- [ ] **Step 3: 修改 users/detail.vue — 角色 Tag 显示**

将第 25-26 行改为：
```html
<el-tag v-if="userInfo.role === 'admin'" type="danger" size="small">管理员</el-tag>
<el-tag v-else-if="userInfo.role === 'sales'" type="warning" size="small">销售</el-tag>
<el-tag v-else type="info" size="small">学员</el-tag>
```

- [ ] **Step 4: Commit**

```bash
git add admin-web/src/stores/app.ts admin-web/src/views/users/index.vue admin-web/src/views/users/detail.vue
git commit -m "feat(admin-web): update user role options to admin/sales/student"
```

---

## Task 11: 培训端 — 类型定义和 auth store 新增 role 支持

**Files:**
- Modify: `training-web/src/types/index.ts`
- Modify: `training-web/src/stores/auth-user.ts`
- Modify: `training-web/src/stores/auth.ts`

- [ ] **Step 1: 修改 types/index.ts — UserInfo 增加 role**

在 `UserInfo` 接口中追加 `role` 字段：
```typescript
export interface UserInfo {
  id: number
  name: string
  phone: string
  avatar: string
  storeName: string
  joinDate: string
  level: number
  point: number
  mustChangePassword?: boolean
  role?: string   // 新增：'sales' | 'student'
}
```

- [ ] **Step 2: 修改 auth-user.ts — normalizeTrainingUser 保留 role**

在 `RawTrainingUser` 类型中追加 `role`：
```typescript
type RawTrainingUser = {
  // ... 现有字段 ...
  role?: string | null
}
```

在 `normalizeTrainingUser` return 对象中追加：
```typescript
  role: typeof raw.role === 'string' ? raw.role : 'student',
```

- [ ] **Step 3: 修改 auth.ts — 暴露 userRole computed**

在 `isLoggedIn` 后追加：
```typescript
  const userRole = computed(() => user.value?.role ?? 'student')
  const isSales = computed(() => userRole.value === 'sales')
```

并在 return 对象中包含 `userRole` 和 `isSales`。

- [ ] **Step 4: Commit**

```bash
git add training-web/src/types/index.ts training-web/src/stores/auth-user.ts training-web/src/stores/auth.ts
git commit -m "feat(training-web): add role field to UserInfo and expose userRole/isSales"
```

---

## Task 12: 培训端 — 路由守卫角色校验 & 销售专属路由

**Files:**
- Modify: `training-web/src/router/index.ts`

- [ ] **Step 1: 在路由守卫中增加培训端角色校验**

在现有 `router.beforeEach` 中，在判断 `!authStore.isLoggedIn` 之后追加：
```typescript
  // 培训端只允许 sales 和 student
  } else if (
    to.meta.requiresAuth !== false &&
    authStore.isLoggedIn &&
    authStore.userRole &&
    !['sales', 'student'].includes(authStore.userRole)
  ) {
    authStore.logout()
    next({ path: '/login' })
  ```
  （注意：需要嵌入到现有 else-if 链中，替换 `else { next() }` 前的条件块）

完整更新后的 `beforeEach`：
```typescript
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth !== false && authStore.needsUserInfoRefresh()) {
    await authStore.fetchUserInfo()
  }

  if (to.meta.requiresAuth !== false && !authStore.isLoggedIn) {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (authStore.mustChangePassword && !to.meta.allowChangePassword) {
    next({ path: '/init-password' })
  } else if (to.path === '/init-password' && authStore.isLoggedIn && !authStore.mustChangePassword) {
    next({ path: '/home' })
  } else if (to.path === '/login' && authStore.isLoggedIn) {
    next({ path: '/home' })
  } else if (
    to.meta.requiresAuth !== false &&
    authStore.isLoggedIn &&
    authStore.userRole !== '' &&
    !['sales', 'student'].includes(authStore.userRole)
  ) {
    authStore.logout()
    next({ path: '/login' })
  } else if (to.meta.requiresSales && authStore.userRole !== 'sales') {
    next({ path: '/home' })
  } else {
    next()
  }
})
```

- [ ] **Step 2: 新增销售专属路由**

在 `routes` 数组末尾（`/profile/records` 路由后）追加：
```typescript
  {
    path: '/sales/dashboard',
    name: 'SalesDashboard',
    component: () => import('@/views/sales/dashboard.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: true, requiresSales: true }
  },
  {
    path: '/sales/methodology',
    name: 'SalesMethodology',
    component: () => import('@/views/sales/methodology.vue'),
    meta: { requiresAuth: true, keepAlive: false, showTabBar: true, requiresSales: true }
  },
```

- [ ] **Step 3: Commit**

```bash
git add training-web/src/router/index.ts
git commit -m "feat(training-web): role guard — only sales/student; add sales routes"
```

---

## Task 13: 培训端 — TabBar 根据角色动态显示销售菜单

**Files:**
- Modify: `training-web/src/components/layout/TabBar.vue`

- [ ] **Step 1: 更新 TabBar.vue — 根据 isSales 动态显示 tabs**

将 `<script setup>` 部分替换为：
```typescript
<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { computed, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const pendingActive = ref<number | null>(null)

const baseTabs = [
  { name: 'Home', label: '首页', icon: 'home-o', path: '/home' },
  { name: 'Courses', label: '课程', icon: 'shopping-cart-o', path: '/courses' },
  { name: 'Practice', label: '演练', icon: 'fire-o', path: '/practice' },
  { name: 'Exam', label: '考试', icon: 'records-o', path: '/exam' },
  { name: 'Profile', label: '我的', icon: 'contact-o', path: '/profile' },
]

const salesTabs = [
  { name: 'SalesDashboard', label: '看板', icon: 'chart-trending-o', path: '/sales/dashboard' },
  { name: 'SalesMethodology', label: '方法论', icon: 'medal-o', path: '/sales/methodology' },
]

const tabs = computed(() =>
  authStore.isSales ? [...baseTabs, ...salesTabs] : baseTabs
)

const routeActive = computed(() => {
  const idx = tabs.value.findIndex((t) => route.path.startsWith(t.path))
  return idx !== -1 ? idx : 0
})

const active = computed({
  get: () => pendingActive.value ?? routeActive.value,
  set: (value) => {
    pendingActive.value = Number(value)
  }
})

watch(
  () => route.fullPath,
  () => {
    pendingActive.value = null
  }
)

async function onTabChange(index: number | string) {
  const nextIndex = Number(index)
  const tab = tabs.value[nextIndex]
  if (!tab) {
    pendingActive.value = null
    return
  }

  pendingActive.value = nextIndex

  if (!authStore.isLoggedIn) {
    await router.push('/login')
    return
  }

  if (route.path === tab.path) {
    pendingActive.value = null
    return
  }

  try {
    await router.push(tab.path)
  } catch {
    pendingActive.value = null
  }
}
</script>
```

在 `<template>` 中将 `tabs` 改为 `tabs`（已是 computed，无需额外改动）：
```html
<van-tabbar-item
  v-for="(tab, index) in tabs"
  :key="index"
  :icon="tab.icon"
>
  {{ tab.label }}
</van-tabbar-item>
```

- [ ] **Step 2: Commit**

```bash
git add training-web/src/components/layout/TabBar.vue
git commit -m "feat(training-web): show sales dashboard and methodology tabs for sales role"
```

---

## Task 14: 培训端 — 新建销售 API 文件

**Files:**
- Create: `training-web/src/api/sales.ts`

- [ ] **Step 1: 创建 sales.ts**

```typescript
import { get, post } from './index'
import type { ApiResponse } from '@/types'

export const salesApi = {
  getDashboard(): Promise<ApiResponse<{
    totalSales: number
    totalAudioFiles: number
    totalMethodologies: number
  }>> {
    return get('/sales/dashboard')
  },

  getMethodologies(page = 1, pageSize = 20): Promise<ApiResponse<{
    total: number
    page: number
    pageSize: number
    items: Array<{
      id: number
      title: string
      content: string
      source: string
      tags: string
      status: string
      created_at: string
    }>
  }>> {
    return get('/sales/methodologies', { params: { page, page_size: pageSize } })
  },

  getMethodology(id: number): Promise<ApiResponse<{
    id: number
    title: string
    content: string
    source: string
    tags: string
    status: string
    created_at: string
  }>> {
    return get(`/sales/methodologies/${id}`)
  },

  uploadAudioFile(file: File): Promise<ApiResponse<{
    id: number
    file_url: string
    filename: string
    file_size: number
    status: string
  }>> {
    const form = new FormData()
    form.append('file', file)
    return post('/sales/audio-files', form)
  },

  getMyAudioFiles(page = 1, pageSize = 20): Promise<ApiResponse<{
    total: number
    items: Array<{
      id: number
      file_url: string
      filename: string
      duration: number
      file_size: number
      status: string
      created_at: string
    }>
  }>> {
    return get('/sales/audio-files/my', { params: { page, page_size: pageSize } })
  },
}
```

- [ ] **Step 2: Commit**

```bash
git add training-web/src/api/sales.ts
git commit -m "feat(training-web): add sales API module"
```

---

## Task 15: 培训端 — 新建销售看板页面

**Files:**
- Create: `training-web/src/views/sales/dashboard.vue`

- [ ] **Step 1: 创建 sales 视图文件夹和 dashboard.vue**

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { showToast } from 'vant'
import { salesApi } from '@/api/sales'

const loading = ref(true)
const stats = ref({ totalSales: 0, totalAudioFiles: 0, totalMethodologies: 0 })

async function loadDashboard() {
  loading.value = true
  try {
    const res = await salesApi.getDashboard()
    stats.value = res.data || stats.value
  } catch {
    showToast('看板数据加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">销售看板</h2>
      <p class="page-subtitle">销售团队整体数据概览</p>
    </div>

    <van-loading v-if="loading" size="24" class="page-loading">加载中...</van-loading>

    <template v-else>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-num">{{ stats.totalSales }}</div>
          <div class="stat-label">销售人员</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ stats.totalAudioFiles }}</div>
          <div class="stat-label">语音文件</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ stats.totalMethodologies }}</div>
          <div class="stat-label">方法论</div>
        </div>
      </div>

      <div class="section-card">
        <div class="section-title">快速入口</div>
        <div class="action-list">
          <van-cell title="销售方法论" icon="medal-o" is-link to="/sales/methodology" />
          <van-cell title="上传语音文件" icon="music-o" is-link to="/sales/audio" />
        </div>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.page-header {
  padding: 16px 16px 8px;
  background: $card;
  margin-bottom: 4px;
}
.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
}
.page-subtitle {
  font-size: 13px;
  color: var(--text-muted);
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 16px;
}
.stat-card {
  background: $card;
  border-radius: $radius;
  padding: 16px 8px;
  text-align: center;
  box-shadow: var(--shadow-sm);
}
.stat-num {
  font-size: 28px;
  font-weight: 700;
  color: var(--primary);
}
.stat-label {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted);
}
.section-card {
  margin: 0 16px 16px;
  background: $card;
  border-radius: $radius;
  padding: 16px;
  box-shadow: var(--shadow-sm);
}
.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 12px;
}
.action-list {
  border-radius: $radius;
  overflow: hidden;
}
.page-loading {
  padding: 36px 0;
  display: block;
  text-align: center;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add training-web/src/views/sales/dashboard.vue
git commit -m "feat(training-web): add sales dashboard view"
```

---

## Task 16: 培训端 — 新建销售方法论页面

**Files:**
- Create: `training-web/src/views/sales/methodology.vue`

- [ ] **Step 1: 创建 methodology.vue**

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { showToast } from 'vant'
import { salesApi } from '@/api/sales'

interface Methodology {
  id: number
  title: string
  content: string
  source: string
  tags: string
  status: string
  created_at: string
}

const loading = ref(true)
const methodologies = ref<Methodology[]>([])
const total = ref(0)
const page = ref(1)
const selectedItem = ref<Methodology | null>(null)
const showDetail = ref(false)

async function loadMethodologies() {
  loading.value = true
  try {
    const res = await salesApi.getMethodologies(page.value)
    const data = res.data
    methodologies.value = data.items || []
    total.value = data.total || 0
  } catch {
    showToast('方法论加载失败')
  } finally {
    loading.value = false
  }
}

function openDetail(item: Methodology) {
  selectedItem.value = item
  showDetail.value = true
}

onMounted(loadMethodologies)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">销售方法论</h2>
      <p class="page-subtitle">沉淀销售经验，共享优秀话术</p>
    </div>

    <van-loading v-if="loading" size="24" class="page-loading">加载中...</van-loading>

    <template v-else>
      <div v-if="methodologies.length" class="method-list">
        <div
          v-for="item in methodologies"
          :key="item.id"
          class="method-card"
          @click="openDetail(item)"
        >
          <div class="method-title">{{ item.title }}</div>
          <div class="method-preview">{{ item.content.slice(0, 80) }}{{ item.content.length > 80 ? '...' : '' }}</div>
          <div class="method-meta">
            <van-tag round plain type="primary" size="small">{{ item.source || '手动创建' }}</van-tag>
            <span class="method-date">{{ item.created_at?.slice(0, 10) }}</span>
          </div>
        </div>
      </div>
      <van-empty v-else description="暂无销售方法论" />
    </template>

    <van-popup v-model:show="showDetail" position="bottom" round :style="{ height: '75%' }">
      <div v-if="selectedItem" class="detail-panel">
        <div class="detail-header">
          <span class="detail-title">{{ selectedItem.title }}</span>
          <van-icon name="cross" size="20" @click="showDetail = false" />
        </div>
        <div class="detail-content">{{ selectedItem.content }}</div>
      </div>
    </van-popup>
  </div>
</template>

<style lang="scss" scoped>
.page-header {
  padding: 16px 16px 8px;
  background: $card;
  margin-bottom: 4px;
}
.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
}
.page-subtitle {
  font-size: 13px;
  color: var(--text-muted);
}
.method-list {
  padding: 12px 16px;
}
.method-card {
  background: $card;
  border-radius: $radius;
  padding: 14px;
  margin-bottom: 10px;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
}
.method-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 6px;
}
.method-preview {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
  margin-bottom: 8px;
}
.method-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.method-date {
  font-size: 11px;
  color: var(--text-muted);
}
.page-loading {
  padding: 36px 0;
  display: block;
  text-align: center;
}
.detail-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px;
}
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.detail-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
}
.detail-content {
  flex: 1;
  overflow-y: auto;
  font-size: 14px;
  color: var(--text);
  line-height: 1.8;
  white-space: pre-wrap;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add training-web/src/views/sales/methodology.vue
git commit -m "feat(training-web): add sales methodology view"
```

---

## Task 17: 培训端 — 实战演练页顶部增加 Agent 话术演练入口

**Files:**
- Modify: `training-web/src/views/practice/index.vue`

- [ ] **Step 1: 在 practice/index.vue 模板顶部添加 Agent 入口卡片**

在 `<template>` 中 `.module-list` div 之前插入：
```html
    <!-- Agent 话术演练入口 -->
    <div class="agent-banner" @click="goAgentPractice">
      <div class="agent-icon">
        <van-icon name="chat-o" size="28" color="#fff" />
      </div>
      <div class="agent-info">
        <div class="agent-title">AI 话术演练</div>
        <div class="agent-desc">与 AI 对话，模拟真实销售场景</div>
      </div>
      <van-icon name="arrow" size="16" color="rgba(255,255,255,0.8)" />
    </div>
```

在 `<script setup>` 中追加 `goAgentPractice` 方法：
```typescript
function goAgentPractice() {
  // Agent 话术演练入口占位，后续接入实际 Agent 页面
  showToast('AI 话术演练即将上线')
}
```

并在 script 顶部追加 `import { showToast } from 'vant'`。

在 `<style>` 中追加 `.agent-banner` 样式：
```scss
.agent-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 16px 4px;
  padding: 16px;
  border-radius: $radius;
  background: linear-gradient(135deg, #0e7490 0%, #0f766e 100%);
  color: #fff;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(14, 116, 144, 0.35);

  &:active {
    opacity: 0.9;
  }
}
.agent-icon {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.agent-title {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 3px;
}
.agent-desc {
  font-size: 12px;
  opacity: 0.85;
}
.agent-info {
  flex: 1;
}
```

- [ ] **Step 2: Commit**

```bash
git add training-web/src/views/practice/index.vue
git commit -m "feat(training-web): add Agent chat practice entry at top of practice page"
```

---

## Task 18: 最终验证

- [ ] **Step 1: 后端导入全量检查**

```bash
cd backend && python -c "from app.main import app; print('Backend import OK')"
```

Expected: `Backend import OK`

- [ ] **Step 2: 管理端构建**

```bash
cd admin-web && npm run build 2>&1 | tail -20
```

Expected: 无 ERROR，有 `dist/` 目录生成提示。

- [ ] **Step 3: 培训端构建**

```bash
cd training-web && npm run build 2>&1 | tail -20
```

Expected: 无 ERROR，有 `dist/` 目录生成提示。

- [ ] **Step 4: 功能验证清单（手动测试）**

- [ ] `admin` 账号可登录管理端
- [ ] `sales` 账号登录管理端时被拒绝并跳回登录页
- [ ] `student` 账号登录管理端时被拒绝并跳回登录页
- [ ] `sales` 账号登录培训端后 TabBar 显示「看板」「方法论」两个额外 tab
- [ ] `student` 账号登录培训端后 TabBar 不显示销售相关 tab
- [ ] 实战演练页面顶部显示 AI 话术演练入口卡片
- [ ] `GET /api/v1/sales/dashboard` 以 sales token 调用返回 200
- [ ] `GET /api/v1/sales/dashboard` 以 student token 调用返回 403
- [ ] `GET /api/v1/dashboard/admin-overview` 以 sales token 调用返回 403
- [ ] `POST /api/v1/questions/` 以 sales token 调用返回 403
