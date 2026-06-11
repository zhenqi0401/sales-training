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

AI 出题使用阿里云百炼 OpenAI 兼容接口，后端启动前需配置：

```bash
SALES_TRAINING_AI_API_KEY=你的百炼APIKey
SALES_TRAINING_AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
SALES_TRAINING_AI_MODEL=qwen3.5-omni-flash
SALES_TRAINING_AI_REQUEST_TIMEOUT_SECONDS=120
SALES_TRAINING_AI_VIDEO_FPS=1
SALES_TRAINING_AI_VIDEO_MAX_INLINE_MB=100
SALES_TRAINING_AI_VIDEO_MAX_DATA_URL_CHARS=10000000
SALES_TRAINING_AI_VIDEO_COMPRESS_MAX_WIDTH=480
SALES_TRAINING_AI_VIDEO_COMPRESS_CRF=38
SALES_TRAINING_AI_VIDEO_COMPRESS_AUDIO_BITRATE=32k
```

AI 出题会按百炼 Qwen-Omni 全模态文档的 OpenAI 兼容 `video_url` 输入格式读取视频画面和音频讲解生成题目，`SALES_TRAINING_AI_VIDEO_FPS` 用于控制抽帧频率。Qwen-Omni 使用 Base64 传文件时，编码后的 Base64 字符串必须小于 10MB；对于 `/uploads` 本地视频，后端会在文件不超过 `SALES_TRAINING_AI_VIDEO_MAX_INLINE_MB` 时编码为 data URL 发送，如果超过 `SALES_TRAINING_AI_VIDEO_MAX_DATA_URL_CHARS`，会自动用 ffmpeg 生成低分辨率、保留音频的 AI 识别压缩版视频再发送。生产环境建议配置可公网访问的视频 URL。使用 Docker Compose 启动后端时，可在宿主机环境或本地 `.env` 中设置上述变量；不要将真实 API Key 提交到仓库。

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
| 异步任务 | Celery + Redis (AI出题) |

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
