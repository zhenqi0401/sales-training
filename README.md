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

### 0. 系统依赖

视频上传后会自动压缩为适配手机端播放的 H.264 MP4，需要 **ffmpeg**（含 ffprobe）：

```bash
# macOS
brew install ffmpeg

# Debian / Ubuntu
sudo apt install ffmpeg

# Windows
winget install ffmpeg
```

验证：`ffmpeg -version`

### 1. 启动基础设施

```bash
docker-compose up -d mysql
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

AI 出题 / 语音转写 / 话术演练统一使用火山引擎方舟 Doubao（全模态），后端启动前需配置：

```bash
SALES_TRAINING_AI_API_KEY=ark-你的火山方舟APIKey
SALES_TRAINING_AI_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
SALES_TRAINING_AI_MODEL=doubao-seed-2-0-mini-260428
SALES_TRAINING_AI_QUESTION_TEXT_MODEL=doubao-seed-2-0-mini-260428
SALES_TRAINING_METHODOLOGY_MODEL=doubao-seed-2-0-mini-260428
SALES_TRAINING_AGENT_MODEL=doubao-seed-2-0-mini-260428
SALES_TRAINING_AGENT_MAX_TURNS=15
SALES_TRAINING_AGENT_MAX_TOOL_ITERATIONS=3
SALES_TRAINING_AI_REQUEST_TIMEOUT_SECONDS=120
```

出题流程为：视频上传后由 ffmpeg 提取音频（自动压到 15MB 以内）→ Doubao 转写为带 `[MM:SS]` 时间戳的转录稿（方舟 Responses API，音频以 Base64 内联传入，上限 25MB / 120 分钟）→ Doubao 依据转录稿生成题目，解析引用时间戳作为证据。语音转写、方法论提取走 Responses API，话术演练 Agent 走方舟 OpenAI 兼容的 chat/completions（流式 + 工具调用）。`SALES_TRAINING_AI_API_KEY` 填火山引擎 ARK API Key。使用 Docker Compose 启动时，可在宿主机环境或本地 `.env` 中设置上述变量；不要将真实 API Key 提交到仓库。

### 3. 启动管理端

```bash
cd admin-web
npm install
npm run dev
```

管理端：http://localhost:3000（需要 `admin` 角色账号登录）

### 4. 启动培训端

```bash
cd training-web
npm install
npm run dev
```

培训端：http://localhost:3001（3000 已被管理端占用时自动顺延；需要 `sales` 或 `student` 角色）

### 默认账号

| 角色 | 账号 | 密码 | 手机号 | 登录端 |
|------|------|------|--------|--------|
| 管理员 | admin | admin123 | 13800000000 | 管理端 |
| 销售 | sales1 | sales123 | 13800000002 | 培训端（密码登录）|
| 学员 | student | student123 | 13800000003 | 培训端（验证码 123456）|

## 技术栈

| 层级 | 技术 |
|------|------|
| 管理端 | Vue 3 + Element Plus + Pinia + Vite |
| 培训端 | Vue 3 + Vant 4 + Pinia + Vite (移动优先) |
| 后端 | FastAPI + SQLAlchemy Async |
| 数据库 | MySQL 8.0 |
| 认证 | JWT + bcrypt |
| 异步任务 | FastAPI BackgroundTasks (视频处理 / AI 出题) |

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

| 角色 | 值 | 使用端 | 权限范围 |
|------|----|--------|---------|
| 管理员 | `admin` | 管理端 | 全部后台功能：用户/门店/课程/题库/试卷/数据看板/销售语音文件查看/销售方法论管理 |
| 销售 | `sales` | 培训端 | 通用学习能力 + 销售看板、销售方法论查看、上传个人销售语音文件 |
| 学员 | `student` | 培训端 | 课程学习、话术学习、考试、Agent 话术演练、收藏、学习记录 |

> 管理端与培训端相互隔离：`admin` 只能登录管理端，`sales`/`student` 只能登录培训端。
