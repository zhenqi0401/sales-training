# AGENTS.md

本文件用于记录在本项目中需要长期遵守的项目约定。后续在本仓库内开展开发、修复、重构、排查问题或生成文档时，应优先阅读并遵守本文件。

## 项目概览

- 项目名称：销售培训系统。
- 后端：`backend/`，FastAPI + SQLAlchemy Async + Alembic + Celery + Redis。
- 管理端：`admin-web/`，Vue 3 + TypeScript + Vite + Element Plus + Pinia。开发端口 3000，仅 `admin` 角色可登录。
- 培训端：`training-web/`，Vue 3 + TypeScript + Vite + Vant + Pinia，移动端优先。开发端口 3001（或 3000 未被占时为 3000），仅 `sales`/`student` 角色可登录。
- 基础设施：`docker-compose.yml` 提供 MySQL、Redis 等本地依赖。

## 角色系统

系统统一三种角色，旧角色 `super_admin`/`training_admin`/`instructor` 已通过 Alembic 迁移统一为 `admin`。

| 角色 | 值 | 使用端 |
|------|----|--------|
| 管理员 | `admin` | 仅管理端 |
| 销售 | `sales` | 仅培训端 |
| 学员 | `student` | 仅培训端 |

- 后端权限依赖：`require_admin()`、`require_training_user()`（sales+student）、`require_sales()`、`require_sales_or_admin()` 均定义在 `backend/app/core/dependencies.py`。
- 管理端路由守卫：读取 `localStorage` 中 `auth-store.role`，非 `admin` 时跳回登录页。
- 培训端路由守卫：非 `sales`/`student` 角色自动退出；`requiresSales: true` 路由对学员不可见。

## 重要维护规则

- 本仓库必须长期维护 `AGENTS.md`、`README.md`、`update.md` 三类文档，三者职责不同，不要相互替代。
- `AGENTS.md` 是 AI 开发工具的项目规则入口，应保持短小、稳定、可执行；用于记录项目结构、技术栈、开发约定、验证方式、文档维护规则和跨端一致性要求。新增或调整长期协作规则、开发流程、技术栈约束时，必须同步更新本文件。
- `README.md` 是人类使用者和开发者手册，应说明项目用途、环境依赖、安装启动、配置项、常见命令和部署/使用注意事项。涉及环境变量、启动方式、依赖安装、外部服务、部署流程或用户使用方式变化时，必须同步更新 `README.md`。
- `update.md` 是持续追加的变更日志。每次进行重要更改时，必须在 `update.md` 末尾追加记录，不覆盖历史内容。
- `update.md` 每条记录应包含日期、变更主题、影响范围和要点；需要说明本次变更影响了哪些端、接口、页面、配置、数据库结构或业务流程。
- 重要更改包括但不限于：新增/修改功能、修复影响用户或业务流程的问题、接口契约变化、数据库结构变化、配置或环境依赖变化、跨端联调调整、权限/登录/考试/学习进度/收藏/视频上传/AI 出题等核心流程变化。
- 仅进行格式化、注释、无行为变化的小范围整理时，可不追加 `update.md`；如果不确定是否属于重要更改，默认追加。
- 修改上述三类文档本身也属于项目规范变更，应在 `update.md` 追加记录。
- 处理用户未要求的无关改动时，不要顺手重构或回滚。当前工作区可能存在用户或其他工具留下的未提交变更，应只改动完成任务所必需的文件。
- 涉及环境改变、增加安装包等需要找到对应的md文档或requirements进行修改。

## 常用命令

### 后端

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
python seed_data/seed_all.py     # 写入测试账号（可选）
uv run python -m uvicorn app.main:app --reload --port 8080
```

后端接口文档位于 `http://localhost:8080/api/docs`。

### 管理端

```bash
cd admin-web
npm install
npm run dev    # http://localhost:3000（admin 角色账号）
npm run build
```

### 培训端

```bash
cd training-web
npm install
npm run dev    # http://localhost:3001（sales/student 角色账号）
npm run build
```

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
