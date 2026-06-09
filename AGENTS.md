# AGENTS.md

本文件用于记录在本项目中需要长期遵守的项目约定。后续在本仓库内开展开发、修复、重构、排查问题或生成文档时，应优先阅读并遵守本文件。

## 项目概览

- 项目名称：销售培训系统。
- 后端：`backend/`，FastAPI + SQLAlchemy Async + Alembic + Celery + Redis。
- 管理端：`admin-web/`，Vue 3 + TypeScript + Vite + Element Plus + Pinia。
- 培训端：`training-web/`，Vue 3 + TypeScript + Vite + Vant + Pinia，移动端优先。
- 基础设施：`docker-compose.yml` 提供 MySQL、Redis 等本地依赖。

## 重要维护规则

- 如果是项目开发，项目里必须维护 `update.md`。
- 每次进行重要更改时，都必须在 `update.md` 末尾追加新的补充说明。
- `update.md` 记录应包含日期、变更主题和要点，说明本次变更影响了哪些端、接口、页面或流程。
- 处理用户未要求的无关改动时，不要顺手重构或回滚。当前工作区可能存在用户或其他工具留下的未提交变更，应只改动完成任务所必需的文件。
- 涉及环境改变、增加安装包等需要找到对应的md文档或requirements进行修改。

## 常用命令

### 后端

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uv run python -m uvicorn app.main:app --reload --port 8080
```

后端接口文档通常位于 `http://localhost:8080/api/docs`。

### 管理端

```bash
cd admin-web
npm install
npm run dev
npm run build
```

管理端开发服务通常使用 `http://localhost:5173`。

### 培训端

```bash
cd training-web
npm install
npm run dev
npm run build
```

培训端开发服务通常使用 `http://localhost:5174`。

### 基础服务

```bash
docker-compose up -d mysql redis
```

### 视频转码（环境依赖）

服务器需安装 **ffmpeg**（含 ffprobe），用于上传后自动将视频统一转为 H.264 MP4（720p）。

```bash
# macOS
brew install ffmpeg

# Debian / Ubuntu
sudo apt install ffmpeg

# Windows
winget install ffmpeg
# 或从 https://ffmpeg.org/download.html 下载后加入 PATH
```

验证安装：`ffmpeg -version`

## 开发约定

- 后端接口应保持统一响应结构，已有培训端接口通常使用 `{ code, message, data }`。
- 后端新增数据结构时，应同步补充 SQLAlchemy model、Pydantic schema、API/service 逻辑，并在需要时新增 Alembic 迁移。
- 前端改动优先复用现有 API 封装、Pinia store、路由和组件风格。
- 管理端界面遵循 Element Plus 现有用法；培训端界面遵循 Vant 移动端优先风格。
- 修改登录、鉴权、考试、学习进度、收藏、视频上传等跨端流程时，需要同时检查后端、管理端和培训端调用是否一致。
- 不要提交上传的视频、封面等大体积运行时文件，除非用户明确要求保留为测试资产。

## 验证建议

- 后端逻辑改动后，优先运行相关接口或服务层的最小验证；涉及数据库结构时确认迁移可执行。
- 前端页面或组件改动后，优先运行对应项目的 `npm run build`。
- 同时影响多个子项目时，分别验证受影响的子项目，不需要为无关子项目做额外构建。
- 如果因为本地依赖、数据库、服务未启动等原因无法验证，应在最终回复中明确说明未验证项和原因。
