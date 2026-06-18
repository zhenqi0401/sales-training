# 销售培训系统

> 眼视光行业销售人员培训平台 — 前后端分离 Web 应用

## 项目结构

```
销售培训系统/
├── backend/              # FastAPI 后端 (Python 3.12)
│   ├── app/
│   ├── scripts/          # 运维脚本（OSS 迁移、孤儿清理）
│   └── requirements.txt
├── admin-web/            # 管理端 (Vue 3 + Element Plus)
├── training-web/         # 培训端 (Vue 3 + Vant 移动优先)
├── nginx/
│   └── default.conf      # Nginx 站点配置（docker compose 使用）
├── docker-compose.yml
└── README.md
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 管理端 | Vue 3 + Element Plus + Pinia + Vite |
| 培训端 | Vue 3 + Vant 4 + Pinia + Vite（移动优先） |
| 后端 | FastAPI + SQLAlchemy Async |
| 数据库 | MySQL 8.0 |
| 视频存储 | 阿里云 OSS（私有桶 + 签名 URL 播放） |
| AI | 火山引擎方舟 Doubao（ASR 转写 / 出题 / 话术演练） |
| 认证 | JWT + bcrypt |
| 部署 | Docker Compose + Nginx |

---

## 本地开发启动

### 0. 系统依赖

| 工具 | 用途 | 安装 |
|------|------|------|
| **ffmpeg**（含 ffprobe） | 发布视频时提取音频做 ASR 转写 | `winget install ffmpeg` / `brew install ffmpeg` / `apt install ffmpeg` |
| **Docker Compose v2** | 本地数据库 | `curl -fsSL https://get.docker.com \| sh` |
| **Node.js 18+** | 前端开发 | https://nodejs.org |

验证：`ffmpeg -version`、`docker compose version`

### 1. 启动数据库

```bash
docker compose up -d mysql
```

### 2. 配置环境变量

```bash
cd backend
```

创建 `backend/.env`，至少填以下内容：

```bash
# 数据库
SALES_TRAINING_DATABASE_URL=mysql+asyncmy://training:training123@localhost:3306/sales_training

# 火山引擎方舟 API Key（AI 出题 / ASR / 话术演练）
SALES_TRAINING_AI_API_KEY=ark-你的Key

# OSS（可选，本地开发可不填，视频存本地）
SALES_TRAINING_OSS_ENABLED=false
```

所有可用配置项见 `backend/app/core/config.py`。

### 3. 启动后端

```bash
cd backend
pip install -r requirements.txt --break-system-packages
alembic upgrade head
python seed_data/seed_all.py   # 首次灌入默认数据
uvicorn app.main:app --reload --port 8080
```

API 文档：http://localhost:8080/api/docs

### 4. 启动管理端

```bash
cd admin-web && npm install && npm run dev
```

管理端：http://localhost:3000

### 5. 启动培训端

```bash
cd training-web && npm install && npm run dev
```

培训端：http://localhost:3001

---

## 视频上传流程

```
管理端分片上传 MP4
  → 后端合并
  → OSS_ENABLED=true：上传到 OSS videos/{YYYYMM}/{uuid}.mp4，删本地
  → OSS_ENABLED=false：保存到本地 uploads/videos/
  → 管理员发布 → 后台任务：从 OSS/本地读取视频
  → ffmpeg 提取音频（16kHz MP3）→ Doubao ASR 转写
  → Doubao 依转录稿生成考题 → 视频状态 published
```

**学员端播放**：后端实时签发 12 小时 HTTPS 签名 URL，浏览器直连 OSS，不经 Nginx。

**上传格式**：仅支持 MP4。

---

## 默认账号（seed 数据）

| 角色 | 账号 | 密码 | 手机号 | 登录端 |
|------|------|------|--------|--------|
| 管理员 | admin | admin123 | 13800000000 | 管理端 |
| 销售 | sales1 | sales123 | 13800000002 | 培训端 |
| 学员 | student | student123 | 13800000003 | 培训端 |

> 管理端与培训端相互隔离：`admin` 只能登录管理端，`sales`/`student` 只能登录培训端。

---

## 用户角色

| 角色 | 使用端 | 权限 |
|------|--------|------|
| `admin` | 管理端 | 用户/门店/课程/题库/试卷/数据看板/销售语音/方法论管理 |
| `sales` | 培训端 | 通用学习 + 销售看板、方法论查看、上传个人销售语音 |
| `student` | 培训端 | 课程学习、话术、考试、Agent 演练、收藏、学习记录 |

---

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

---

## 生产部署

见 [`交付说明-给同事完整版.md`](交付说明-给同事完整版.md)。
