# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Optometry industry sales training platform — a full-stack web application: FastAPI backend with async SQLAlchemy + MySQL, Vue 3 admin panel (Element Plus), Vue 3 mobile student app (Vant).

## Commands

### Infrastructure
```bash
docker-compose up -d mysql redis       # Start MySQL 8.0 + Redis 7
```

### Backend
```bash
cd backend
pip install -r requirements.txt --break-system-packages
python seed_data/seed_all.py            # Creates tables + seeds initial data (idempotent)
alembic upgrade head                    # Apply incremental migrations on top of seeded schema
uv run python -m uvicorn app.main:app --reload --port 8080
```

API docs at `http://localhost:8080/api/docs`.

The initial migration (`510b2da09aa8`) is a no-op stub — initial schema comes from `Base.metadata.create_all()` inside `seed_all.py`. Two real migrations follow: `a05_video_management_fields` (adds tags + product_ids JSON columns to videos) and `b01_user_must_change_password` (adds must_change_password boolean to users). Run `alembic upgrade head` after seeding to apply them.

### Frontend apps
```bash
cd admin-web       # Vue 3 + Element Plus management panel
npm install && npm run dev       # → http://localhost:3000

cd training-web    # Vue 3 + Vant mobile student platform
npm install && npm run dev       # → http://localhost:3000
```

Both Vite dev servers use port **3000**. They proxy `/api` and `/uploads` to `http://localhost:8080`. Don't run both at once on the same port.

### Default accounts (created by seeder)
| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | super_admin |
| `trainer` | `trainer123` | training_admin |
| `teacher` | `teacher123` | instructor |
| `student` | `student123` | student |

## Architecture

### Backend (`backend/`)

```
app/
├── main.py              # FastAPI app, CORS (*), static /uploads mount, /health endpoint
├── api/v1/
│   ├── router.py        # 13 route modules under /api/v1, Chinese-language tags
│   ├── auth.py          # Login (username+pw, SMS code), password change, token refresh
│   ├── users.py         # CRUD + import/export (xlsx)
│   ├── stores.py        # Store hierarchy (self-referential parent_id)
│   ├── categories.py    # Category hierarchy (self-referential parent_id)
│   ├── videos.py        # CRUD, chunked upload with SHA-256 verification, transcode status polling
│   ├── questions.py     # CRUD, import, AI generation endpoint
│   ├── exam_papers.py   # Exam paper templates (question_ids array)
│   ├── exams.py         # Live exam: start session, submit answers, score, wrong-book
│   ├── learning.py      # Video progress, watch position, favorites, script browsing
│   ├── scripts.py       # Sales scripts CRUD
│   ├── products.py      # Product knowledge base CRUD
│   ├── favorites.py     # User bookmarks (video/product/script)
│   └── dashboard.py     # Aggregated statistics
├── core/
│   ├── config.py        # pydantic-settings: all env vars prefixed SALES_TRAINING_
│   ├── database.py      # Async SQLAlchemy engine (asyncmy) + session factory
│   ├── dependencies.py  # SessionDep, CurrentUserDep, require_role(*roles) factory
│   └── security.py      # bcrypt password hashing, JWT encode/decode (python-jose)
├── models/              # 13 SQLAlchemy ORM models — Base + TimestampMixin + 12 domain models
├── schemas/             # Pydantic request/response schemas
├── services/            # Service layer: ai_service, auth_service, exam_service, question_service, video_service
└── tasks/
    ├── celery_app.py    # Celery config (Redis broker, Asia/Shanghai, 60m hard limit)
    └── tasks.py         # run_transcode (ffmpeg) + generate_questions_task (stub)
```

**Key patterns:**
- **Most routes query models inline** — there's no enforced service layer, but service classes exist for auth, exams, questions, and videos. `SessionDep` provides the async session; `CurrentUserDep` extracts the JWT-authenticated user.
- **Config**: all settings use `SALES_TRAINING_` env prefix. See `core/config.py` for defaults. No `.env` file is committed.
- **API response convention**: list endpoints return `{ items, total, page, page_size, total_pages }`. Single-item endpoints wrap in `ApiResponse(code=200, message, data)`.
- **Pagination**: `default_page_size=20`, `max_page_size=100`.
- **Video upload**: chunked upload with SHA-256 per chunk. Server assembles, verifies digest, dispatches `run_transcode()` via `BackgroundTasks`. ffmpeg produces H.264 MP4 (max 720p) + cover image from first frame. Results written to Redis key `transcode:{upload_id}` (1-hour TTL). Clients poll `/videos/upload/transcode-status/{upload_id}`.
- **Student auth**: SMS verification code login. Dev code hardcoded as `123456`. Admin/instructor uses username+password.
- **AI question generation**: `POST /questions/ai-generate` returns draft questions. The ASR (`transcribe_video`) and LLM (`call_question_llm`) functions in `ai_service.py` are empty stubs — they always produce placeholder questions. There's also a Celery task stub (`generate_questions_task`) ready for async generation.

### Data Model (13 tables)

| Model | Table | Key Relationships |
|---|---|---|
| `User` | `users` | FK→stores; has many learning_progresses, exam_records, favorites |
| `Store` | `stores` | Self-referential parent_id hierarchy; has many users |
| `Category` | `categories` | Self-referential parent_id hierarchy; has many videos, products, questions |
| `Video` | `videos` | FK→categories; has many questions, learning_progresses, favorites; JSON: tags, product_ids |
| `Question` | `questions` | FK→categories, FK→videos; types: single/multiple/true_false/fill/short_answer |
| `ExamPaper` | `exam_papers` | JSON `question_ids` — ordered question ID list |
| `ExamRecord` | `exam_records` | FK→users, FK→exam_papers; has many exam_answers |
| `ExamAnswer` | `exam_answers` | FK→exam_records, FK→questions |
| `LearningProgress` | `learning_progresses` | FK→users, FK→videos; tracks watch position & completion |
| `Favorite` | `favorites` | FK→users; polymorphic via `type` (video/product/script) + `target_id` |
| `Script` | `scripts` | FK→products; categories: general/product/objection/closing |
| `Product` | `products` | FK→categories; JSON fields for specs, FAQ, comparison data |

All models inherit `Base` + `TimestampMixin` (created_at, updated_at in UTC).

### Admin Web (`admin-web/`)

Vue 3 SPA + Element Plus + Pinia + TypeScript + unplugin-auto-import.
- `src/api/index.ts` — Axios instance: baseURL `/api/v1`, 10min timeout. camelCase→snake_case param normalization on requests. On 401: clears localStorage, redirects to `/login`. On error: shows `ElMessage` toast. Exports typed `get/post/put/del` helpers.
- `src/api/*.ts` — 11 domain files (auth, categories, dashboard, exams, products, questions, scripts, stores, users, videos).
- `src/router/index.ts` — `createWebHistory`, beforeEnter guard reads token from `localStorage('auth-store')`. `/login` marked `noAuth`; all other routes nested under `AppLayout`.
- `src/stores/auth.ts` — Pinia setup store; login via username+password; token + userInfo persisted in localStorage under key `auth-store`.
- `src/stores/app.ts` — Sidebar collapse state (persisted) + hardcoded sidebar menu structure (6 groups).
- `src/views/` — 10 domains: categories, dashboard, exams, login, products, questions, scripts, stores, users, videos.

Note: admin-web has **no token refresh** — a 401 immediately logs the user out.

### Training Web (`training-web/`)

Vue 3 mobile-first SPA + Vant 4 + Pinia + TypeScript + postcss-px-to-viewport.
- `src/api/index.ts` — Axios instance: baseURL `/api/v1`, 15s timeout. **Automatic token refresh**: on 401, uses a separate `refreshHttp` instance (no interceptor) to call `/auth/refresh`. Deduped in-flight via shared promise. New tokens dispatched via `CustomEvent('auth-token-refreshed')` so the Pinia store stays in sync. Tokens stored in `auth-token` and `auth-refresh-token` localStorage keys.
- `src/stores/auth.ts` — Pinia setup store; SMS login flow; `mustChangePassword` guard redirects to `/init-password`; listens for `auth-token-refreshed` custom event for cross-layer sync.
- `src/router/index.ts` — Hash-based history; beforeEach guard handles auth check, `mustChangePassword` redirect, login redirect for already-authenticated users. `keepAlive` meta for tab-bar page caching.
- `src/views/` — Home, courses (list/play/script), practice, exam (taking/result/wrong-book), scripts, products, profile with learning records.

### User Roles

| Role | Scope |
|---|---|
| `super_admin` | Full access including store management |
| `training_admin` | Course management, question bank, data views |
| `instructor` | Assigned course management, student progress |
| `student` | Video learning, exams, script practice, product knowledge |

### Product Category Codes

`qingkong` (青控), `xieruoshi` (斜弱视), `jiaosu` (角塑), `yanjiang` (眼镜), `zhoubian` (周边产品), `gongneng` (功能性眼镜), `qiwenhua` (企业文化)
