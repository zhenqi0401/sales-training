"""API v1 router — aggregates all endpoint modules."""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    users,
    stores,
    categories,
    videos,
    questions,
    exam_papers,
    exams,
    learning,
    scripts,
    products,
    favorites,
    dashboard,
    sales,
    practice,
)

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router, prefix="/auth", tags=["认证"])
router.include_router(users.router, prefix="/users", tags=["用户管理"])
router.include_router(stores.router, prefix="/stores", tags=["门店管理"])
router.include_router(categories.router, prefix="/categories", tags=["分类管理"])
router.include_router(videos.router, prefix="/videos", tags=["视频管理"])
router.include_router(questions.router, prefix="/questions", tags=["题库管理"])
router.include_router(exam_papers.router, prefix="/exam-papers", tags=["试卷管理"])
router.include_router(exams.router, prefix="/exams", tags=["考试管理"])
router.include_router(learning.router, prefix="/learning", tags=["学习进度"])
router.include_router(scripts.router, prefix="/scripts", tags=["话术管理"])
router.include_router(products.router, prefix="/products", tags=["产品管理"])
router.include_router(favorites.router, prefix="/favorites", tags=["收藏管理"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["数据统计"])
router.include_router(sales.router, prefix="/sales", tags=["销售功能"])
router.include_router(practice.router, prefix="/practice", tags=["话术演练"])
