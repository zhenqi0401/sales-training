# 销售培训系统

> 眼视光行业销售人员培训平台 — 前后端分离 Web 应用

## 项目结构

```
销售培训系统/
├── backend/          # FastAPI 后端 (Python 3.12)
├── admin-web/        # 管理端 (Vue 3 + Element Plus)
├── training-web/     # 培训端 (Vue 3 + Vant 移动优先)
├── docker-compose.yml
└── README.md
```

## 快速启动

### 1. 启动基础设施

```bash
docker-compose up -d mysql redis
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt --break-system-packages
alembic upgrade head
python seed_data/seed_all.py
uv run python -m uvicorn app.main:app --reload --port 8080
```

API 文档：http://localhost:8080/api/docs

### 3. 启动管理端

```bash
cd admin-web
npm install
npm run dev
```

管理端：http://localhost:5173

### 4. 启动培训端

```bash
cd training-web
npm install
npm run dev
```

培训端：http://localhost:5174

### 默认账号

| 角色 | 账号 | 密码 |
|------|------|------|
| 超级管理员 | admin | admin123 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 管理端 | Vue 3 + Element Plus + Pinia + Vite |
| 培训端 | Vue 3 + Vant 4 + Pinia + Vite (移动优先) |
| 后端 | FastAPI + SQLAlchemy Async + Celery |
| 数据库 | MySQL 8.0 + Redis 7 |
| 认证 | JWT + bcrypt |
| 异步任务 | Celery + Redis (AI出题、视频处理) |

## 产品分类编码

| 编码 | 名称 |
|------|------|
| qingkong | 青控 |
| xieruoshi | 斜弱视 |
| jiaosu | 角塑 |
| yanjiang | 眼镜 |
| zhoubian | 周边产品 |
| gongneng | 功能性眼镜 |
| qiwenhua | 企业文化 |

## 用户角色

| 角色 | 权限范围 |
|------|---------|
| super_admin | 全部功能，含门店管理 |
| training_admin | 课程管理、题库管理、数据查看 |
| instructor | 所负责课程的管理、查看学员进度 |
| student | 视频学习、考试认证、话术练习 |
