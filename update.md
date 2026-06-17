# Update Log

## 2026-06-17 管理端数据看板聚焦学习与门店运营

- **变更**：重做管理端数据看板信息层级，移除各试卷/等级统计和错题分析模块，改为重点展示学员视频学习完成度、考试通过率和门店达成情况。
- **影响**：`admin-web/src/views/dashboard/index.vue`；保留现有 `/dashboard/admin-overview` 与学员进度导出接口契约，不新增图表库依赖。
- **展示**：新增纯前端圆环图展示整体完课率/考试通过率，新增门店完成率与通过率柱状对比，并保留视频学习排行、学员学习表现、门店排行和学员进度明细。
- **验证**：已运行管理端 `npm run build`，`vue-tsc` 与 Vite 构建通过；构建输出仅包含既有 Sass legacy API、Rollup 注释和 chunk size 警告。

## 2026-06-17 AI 模型从阿里云百炼切换为火山引擎 Doubao-Seed-2.0-mini

- **变更**：项目全部 AI 调用（视频出题、语音转写、销售方法论、话术演练 Agent）从阿里云百炼切换为火山引擎方舟 Doubao-Seed-2.0-mini（全模态）。
- **端点**：出题 / 转写 / 方法论改用方舟 **Responses API**（官方 `volcenginesdkarkruntime` SDK，`AsyncArk`）；话术演练 Agent 保留 **chat/completions**（方舟兼容 OpenAI，流式 + 工具调用），只换 base_url/model/key。
- **流程**：视频 → ffmpeg 提取音频（≤15MB）→ Doubao 转写为带 `[MM:SS]` 时间戳的转录稿（`input_audio` + Base64 `audio_url`，上限 25MB/120 分钟）→ Doubao 依据转录稿出题。两步均在 Doubao 完成。
- **影响**：`ai_service.py`（重写 client/ASR/出题/方法论，删除 DashScope `Transcription`、urllib chat 调用与多模态视频 base64 机器）、`config.py`（base_url/模型改火山，删除 `ai_video_*` 配置）、`requirements.txt`（移除 `dashscope`，新增 `volcengine-python-sdk[ark]`）、`practice_agent.py`（注释）、`.env`/`.env.example`/`README.md`/`部署方案.md`（火山 ARK Key 与模型）、`tests/test_ai_service.py`+`test_config.py`（按新架构重写）。
- **时间戳**：Doubao 经 ASR 模板提示输出逐句秒级时间戳，解析后转为 `[MM:SS]` 供题目证据引用，保持与原 prompt 兼容。
- **验证**：后端导入检查、单元测试通过；样例音频冒烟测试确认 Responses API、ASR 时间戳、出题与 Agent 流式可用。

## 2026-06-17 清理未使用的占位代码与 Celery/Redis 基础设施

- **变更**：移除项目中从未接入业务的占位代码和未启用的异步任务基础设施。
- **删除的服务层（dead code，从未被 import，API 路由直接用 SQLAlchemy）**：`app/services/auth_service.py`、`exam_service.py`、`video_service.py`、`question_service.py`。
- **删除的 Celery/Redis 体系（实际异步用 FastAPI BackgroundTasks，Redis 无真实缓存用途）**：整个 `app/tasks/` 目录（`celery_app.py`/`tasks.py`）；`config.py` 的 `celery_broker_url`/`celery_result_backend`；`requirements.txt` 的 `celery`/`redis`；`docker-compose.yml` 的 `redis` 服务、`celery-worker` 服务、`redis_data` 卷及 backend 的相关依赖与环境变量；`.env.example` 的 Celery 变量。部署从 5 容器精简为 3 容器（mysql / backend / nginx）。
- **删除的零散文件**：根目录 `_read_docx.py`/`_read_docx.js`/`nul`；`backend/fix_practice_tables.py`（一次性建表修复）；`backend/setup.py`（与 alembic+seed_all 重复的引导脚本）。
- **文档同步**：`README.md`、`部署方案.md`、`prd.md`、`.gitignore` 去除 Celery/Redis 相关内容。
- **验证**：全局 grep 确认无残留引用（业务代码与配置）。

## 2026-06-18 ASR 统一为 qwen3-asr-flash，移除本地 Whisper

- **变更**：删除所有 faster-whisper 本地模型相关代码，ASR 统一使用百炼云端 `qwen3-asr-flash`。
- **影响**：`ai_service.py`（删除三个 Whisper 函数，替换为 async `transcribe_video_audio`）、`videos.py`（去掉 semaphore 和 asyncio.to_thread 包装）、`requirements.txt`（移除 faster-whisper）
- **原因**：`qwen3-asr-flash` 不支持词级时间戳，因此一并去掉 AI 出题 prompt 中的时间戳要求，改为"依据视频音频内容逐项说明"。
- **验证**：后端语法检查通过、App 正常加载、两个前端 vue-tsc 零错误。

## 2026-06-18 视频管线健壮性修复

- **变更**：修复「视频上传 → 转码 → ASR → AI 出题 → 上架」完整链路的可靠性和可重试性。
- **影响**：后端 `videos.py`（管线逻辑 + retry 端点 + pipeline_log）、`ai_service.py`（ASR fallback）、`models/video.py`（pipeline_log 字段）、`schemas/video.py`（VideoResponse）、`config.py`（默认模型名）；管理端 `index.vue`/`edit.vue`/`types/index.ts`/`api/videos.ts`。
- **详细**：
  1. **管线可重试**：压缩失败时回退 `draft`；新增 `POST /videos/{id}/retry` 端点；重试时自动清理旧 AI 题目；`update_video_status` 支持 `transcoding`/`generating` → `draft` 回退。
  2. **前端 UX**：`transcoding`/`generating` 状态显示「重新处理」按钮替代上架/下架；筛选器增加「生成中」选项；编辑页移除手动选择 `transcoding`；类型新增 `generating`。
  3. **配置修复**：`.env`/`.env.example`/`config.py` 补充 `AI_QUESTION_TEXT_MODEL=qwen3.6-flash`，去掉带日期的旧默认值。
  4. **ASR fallback**：本地 `faster-whisper` 不可用时自动降级到 DashScope `qwen3-asr-flash` 云端转写。
  5. **管线日志**：Video 模型新增 `pipeline_log` JSON 字段，管线各步骤写入状态；新增 `GET /videos/{id}/pipeline-log` 接口；前端状态标签 hover 显示步骤进度。
  6. **Celery 清理**：`celery_app.py`/`tasks.py` 加注释说明未启用，导入失败时优雅降级不阻塞启动。
- **验证**：后端语法检查通过、App 加载正常；前端 `vue-tsc --noEmit` 零错误、`vite build` 构建成功。

## 2026-06-05 FR-A05 视频上传与管理

- 补全视频管理后端字段：标签、关联产品、时长、分辨率、文件大小、上下架状态、排序权重、必修标记。
- 完善视频上传流程：限制 mp4/mov/avi、最大 2GB、分片上传合并、保存到本地上传目录，并在可用 ffprobe/ffmpeg 时自动读取视频元信息和截取首帧生成封面图。
- 新增单个状态切换接口、批量上架/下架接口。
- 管理端视频列表支持分类筛选、状态筛选、必修筛选、搜索、批量上架/下架，并展示标签、关联产品、文件大小、时长和分辨率。
- 管理端视频编辑页支持修改基础信息、标签、关联产品、状态、排序、必修和替换视频文件，学习时长直接使用视频时长换算。
- 增加视频字段数据库迁移与 Nginx 静态资源服务示例配置。

## 2026-06-05 FR-A05 视频预览与封面调整

- 自动封面调整为上传视频首帧截取，不再要求管理员手动上传封面。
- 修复管理端视频预览和封面缩略图访问 `/uploads` 静态资源时的开发环境代理问题。
- 去掉编辑页预计学习时长输入项，保存时使用视频时长自动换算学习分钟数。

## 2026-06-05 FR-A05 上传保存体验修复

- 分辨率改为自动获取后的只读字段，避免管理员手动修改。
- 选中视频后前端即时截取首帧用于封面预览，并上传该首帧图片获得正式封面 URL，避免保存 base64 封面导致创建视频失败。
- 保存失败时展示后端错误信息；保存成功后跳转回视频管理页面。
- 后端视频接口增加窄范围表结构自检，自动补齐旧库缺失的 `tags`、`product_ids` 列，避免旧数据库未迁移导致视频保存失败。

## 2026-06-05 管理端删除确认框定位修复

- 为管理端删除确认弹层增加全局样式兜底，修复确认框出现在左上角且文字不清晰的问题。
- 题库批量删除确认改为明确挂载到 `document.body` 的居中 MessageBox，并统一危险操作按钮文案。
- 各管理列表中的删除 Popconfirm 统一启用 teleport 到 body，并增加稳定弹层样式类，避免受表格容器定位影响。

## 2026-06-05 FR-A07 AI 题目生成（Agent）

- 调整 AI 题目生成链路：`/questions/ai-generate` 只返回待审核草稿，不再直接写入题库，避免未审核题目污染正式数据。
- 新增 `/questions/ai-review-save` 接口，管理员编辑、删除、补充并审核通过后再批量入库，入库题目标记来源为 `ai`。
- 生成配置补齐视频选择、题目数量、L1/L2/L3 难度、单选/多选/判断题型比例、知识点、产品分类和可选字幕/转写文本。
- 后端生成流程接入视频信息与产品知识库上下文，并在 `ai_service.py` 中预留 ASR 与 LLM API 接入点；当前使用可运行的占位题目模板返回草稿。
- 管理端 AI 出题页改为审核工作台：支持选择视频生成草稿、逐题编辑题干/选项/答案/解析/标签、删除题目、手动补充题目和审核通过入库。

## 2026-06-05 FR-T01 学员验证码登录
- 培训端登录页接入手机号验证码流程：获取验证码调用 `/auth/send-code`，验证码登录调用 `/auth/phone-login`，并修正登录页中文文案、错误提示和倒计时清理。
- 后端新增学员短信验证码接口，当前开发环境使用本地内存存储验证码，默认验证码为 `123456` 并输出到后端日志，预留真实短信服务商替换点。
- 新增首次登录强制改密状态 `must_change_password`，补充数据库迁移，并在验证码登录返回 `mustChangePassword` 给培训端。
- 培训端新增 `/init-password` 设置密码页面和路由守卫，未完成首次改密的学员会被限制在设置密码流程内。

## 2026-06-05 FR-T01 验证码接口联调修复
- 修正培训端 Vite 开发代理，将 `/api` 从无服务监听的 `localhost:8000` 改为当前后端端口 `localhost:8080`，解决获取验证码时报 `ECONNREFUSED` 的问题。
- 修正 Docker Compose 后端环境变量前缀，统一使用 `SALES_TRAINING_`，避免容器环境读取不到数据库和 JWT 配置。
- 修复 Alembic 初始迁移 `down_revision` 配置，并将视频字段迁移改为幂等检查，保证本地已有字段时仍可继续升级。
- 已将本地数据库升级到 `b01_user_must_change_password`，并补充开发测试学员 `13800000003`。

## 2026-06-05 FR-T01 登录联调补充修复
- 补充 `/stores/all` 后端接口，避免管理端用户表单加载门店下拉时被 `/{store_id}` 动态路由误匹配导致 422。
- 修复门店树和全部门店接口的 MySQL 排序兼容性，去除不兼容的 `NULLS FIRST` SQL。
- 本地补充启用学员账号 `18611203312`，验证码发送接口对该手机号已返回 200。
- `后续接真实短信厂商时，只需要替换 auth.py 里的 _send_sms_code()`

## 2026-06-08 FR-T01 培训端登录态续期修复
- 修复培训端首页 `/learning/stats`、`/learning/recent` 等接口在 access token 过期后直接 401 并清空登录态的问题。
- 后端验证码登录改为返回独立的 30 天 refresh token，`/auth/refresh` 改为校验请求体中的 refresh token 并签发新的 access/refresh token。
- 后端普通鉴权依赖拒绝将 refresh token 当作业务 access token 使用，避免长效 token 被误用于学习接口。
- 培训端请求拦截器遇到 401 时会先串行刷新 token 并重试原请求，刷新失败后才跳转登录页，避免首页并发接口同时触发登出。

## 2026-06-08 话术原型导入分类修复
- 修正 `to_c_training_v11.html` 话术导入逻辑：不再把原型结构标签“原型卡片/原型话术”作为业务分类展示。
- 大师理论卡片按德鲁克、乔·吉拉德、霍普金斯、吉特默、特劳特、李奥·贝纳等大师分类；异议库按价格敏感、拖延犹豫、认知不足、竞品对比、安全担忧等业务场景分类；售后维护表格导入为售后服务话术。
- 保留异议库完整内容，例如 `TC-01 太贵了` 导入为“价格敏感”，内容包含大师技巧、理解、回应、推进四段。
- 后端、管理端和培训端的话术分类名称同步改为业务分类，旧 `prototype_card/prototype_script` 仅作为兼容兜底显示，不再作为新导入分类。

## 2026-06-08 培训端收藏话术修复
- 修复“我的-收藏话术”跳转到旧话术页面导致收藏不可见的问题，统一跳转到新版 `/courses/scripts?favorites=1`。
- 培训端话术列表支持 `favorites=1` 只返回当前用户收藏的话术，并按收藏话术自身分类统计展示。
- 收藏/取消收藏后明确同步本地收藏 store，避免后端已收藏但本地状态未同步时再次点击状态反向错误。
- 后端取消收藏改为幂等返回，避免旧本地状态导致取消接口 404 后前端无法刷新收藏状态。

## 2026-06-08 培训端收藏状态实时刷新修复
- 修复收藏接口返回裸数据导致培训端统一拦截器误判为失败的问题，添加/取消收藏现在统一返回 `{ code, message, data }`。
- 修复当前话术页点击收藏后按钮不变为“已收藏”的问题。
- 收藏话术页监听 `favorites=1` 路由参数变化，取消收藏后列表和分类计数实时移除对应话术。
## 2026-06-08 FR-A10/FR-A11 管理端数据看板
- 扩展管理端 `/dashboard/admin-overview` 接口，聚合培训端学习进度、视频观看、考试记录、错题、学员和门店数据，新增总览、视频维度、学员维度、门店维度、考试统计、错题分析和考试趋势数据。
- 新增 `/dashboard/student-progress-export` 导出接口，管理端可导出学员学习进度 CSV 文件并用 Excel 打开。
- 重做管理端数据看板页面，展示学员总数、活跃学员、完课率、视频观看总时长、人均学习时长、L1/L2/L3 考试通过率、视频排行、学员排行、门店对比、试卷统计、高频错题和薄弱知识点。
- 修复管理端若干阻塞构建的 TypeScript 类型问题与 Header 模板乱码问题，保证管理端完整构建通过。

## 2026-06-08 培训端错题本选项标记精简
- 错题本选项列表去除“你的选择”“正确答案”文字标签，只保留选项内容和颜色状态，答案汇总仍在选项下方统一展示。

## 2026-06-08 培训端错题本选项展示补充
- 错题本卡片新增题目选项列表展示，复盘错题时可同时查看题干、全部选项、自己的选择和正确答案。
- 多选/单选/判断题统一按答案值识别选项状态，错误选择和正确选项使用不同底色与标签标记。
- 错题搜索范围扩展到选项内容，便于按答案关键词定位错题。

## 2026-06-08 培训端考试规则确认弹窗修复
- 修复培训端未引入 Vant 基础样式导致 `showConfirmDialog` 规则确认框被渲染成页面底部普通文字和按钮的问题，点击考试后现在会正常弹出居中确认框。
- 重新整理考试入口页中文文案，确认考试规则后再跳转到答题页，取消确认时停留在当前考试列表页。

## 2026-06-08 FR-T10/FR-T11/FR-T12 考试流程、错题本与成绩记录
- 补齐培训端考试后端接口：新增考试规则、按等级取题、冲刺模式、提交即时评分、成绩详情、错题本、错题统计和成绩趋势接口，统一返回培训端 `{ code, message, data }` 响应格式。
- 提交考试时按题目自动判分并生成考试记录与答题记录，未答题计为错误；结果返回总分、通过状态、分类得分、薄弱分类和错题解析。
- 培训端考试入口改为先读取试卷规则并弹窗确认时长、题量、及格分，再进入倒计时答题页；答题页支持单选、多选、判断、标记题目、倒计时自动交卷和错题重练。
- 错题本支持自动汇总答错题目、按分类/关键字筛选、展示薄弱分类/知识点统计，并可一键进入错题重练。
- 成绩记录页补充历次考试列表和成绩趋势条，可点击趋势或记录查看对应考试结果。

## 2026-06-09 视频快速压缩为手机端 MP4

### 影响范围
- **后端**：`app/api/v1/videos.py`（上传合并后压缩）、`app/services/video_processing.py`（手机端压缩与封面生成）
- **管理端**：`api/videos.ts`、`components/common/VideoUploader.vue`（上传后等待压缩完成）
- **培训端**：无影响（只消费 /uploads 静态文件）

### 变更要点
- 视频分片合并后立即压缩为单个手机端 MP4，压缩成功后只返回最终视频地址、大小、时长、分辨率和封面。
- 分辨率策略：横屏最大 `1280x720`，竖屏最大 `720x1280`，方屏最大 `720x720`；保持原比例，不裁剪、不放大小分辨率视频。
- 编码策略：`libx264 veryfast CRF 28`、`AAC 96k`、`30fps`、`yuv420p`、`movflags +faststart`，保留主音轨并丢弃多余流以降低体积。
- 压缩成功后删除原始大文件；压缩失败时清理临时文件并要求重新上传或更换格式，不再保留失败视频。
- 移除旧的 Redis 轮询状态接口和 `run_transcode` 后台任务，管理端不再轮询，只显示“上传中/压缩中/完成”。
- 删除历史 MOV 转 MP4 迁移脚本，避免保留与当前轻量上传压缩方案无关的脚本信息。
- **前置依赖**：服务器需安装 ffmpeg（含 ffprobe，`ffmpeg -version` 可验证）。

## 2026-06-09 Codex 项目指令初始化
- 新增仓库级 `AGENTS.md`，记录销售培训系统的项目结构、常用启动/构建命令、前后端开发约定和验证建议。
- 将“项目开发时必须维护 `update.md`，每次重要更改都要追加补充说明”固化为 Codex 长期遵守的项目规则。

## 2026-06-09 视频上传压缩依赖检查
- 修复视频上传在 `/videos/upload/merge` 阶段返回 500 但缺少明确原因的问题：根因是当前运行环境未安装或未正确加入 PATH 的 `ffmpeg/ffprobe`。
- 后端新增视频压缩工具可用性检查，上传初始化阶段即检测 `ffmpeg/ffprobe`，缺失时直接返回明确错误，避免用户上传完整大文件后才失败。
- 视频压缩服务在探测、压缩、封面生成前统一检查依赖，并新增单元测试覆盖缺失依赖提示。
- 兼容 Windows WinGet 安装路径：当 `ffmpeg/ffprobe` 未加入 PATH 时，后端会自动查找 `AppData/Local/Microsoft/WinGet/Packages` 下的常见 FFmpeg 包目录。

## 2026-06-09 视频两段式上传与横竖屏播放
- 上传合并接口调整为两段式：第一段快速封装为可播放 MP4 并立即返回，第二段通过后台任务对同一路径视频进行移动端压缩替换。
- 管理端上传完成后提示“可先保存，后台继续压缩”，接口返回 `compression_pending` 表示压缩仍在后台进行。
- 后端学习接口向培训端透传视频 `resolution`，便于播放页提前判断横屏、竖屏或方屏。
- 培训端视频播放页根据 `resolution` 和 `loadedmetadata` 实际宽高自适配 `16:9`、`9:16`、`1:1`，统一使用 `object-fit: contain` 避免裁剪。
## 2026-06-09 管理端用户新增/编辑修复
- 修复管理端用户 API 字段适配：前端继续使用 `realName/storeId/status`，提交给后端时统一转换为 `real_name/store_id/is_active`，后端响应再规范化回前端字段，避免新增学员和编辑姓名失败。
- 后端用户创建/更新 schema 兼容管理端 camelCase 入参，并为用户列表增加 `status` 状态筛选支持。
- 修复用户状态开关调用不存在的 `/users/{id}/status` 接口，改为复用现有 `PUT /users/{id}` 更新 `is_active`。
- 用户表单增加手机号必填和格式校验，保存失败时展示后端错误信息，避免页面看起来卡住。
- 补充用户 schema 兼容性测试，覆盖 `realName/storeId/isActive` 入参解析。

## 2026-06-09 培训端视频进度同步节流修复
- 修复培训端播放页进度上报过于频繁的问题：本地播放进度仍每秒更新，但后端 `POST /learning/progress` 只在观看时长较上次同步增加至少 5 秒、暂停、离开或播放完成时触发。
- 增加进度上报单飞控制，同一时间最多保留一个进行中的进度请求；请求未结束时不会继续堆积新的 `progress` 请求，避免网络面板大量超时。
- 保留本地学习进度缓存，网络失败时不影响视频播放，下一次满足同步条件后继续尝试上报。

## 2026-06-10 AI 出题接入硅基流动大模型
- 后端 `app/services/ai_service.py` 接入硅基流动 OpenAI 兼容 Chat Completions API，默认模型为 `Qwen/Qwen3.5-4B`，通过 `SALES_TRAINING_AI_*` 环境变量配置 API Key、Base URL、模型和超时时间。
- `/questions/ai-generate` 保持返回待审核草稿的既有流程，但生成来源改为真实大模型；大模型未配置、超时、空响应或 JSON 格式异常时返回明确 502 错误，不再静默返回占位题。
- 请求体按硅基流动文档使用 `enable_thinking=false` 与 `response_format=json_schema`，约束返回 `questions` JSON 数组，保留管理员审核后再调用 `/questions/ai-review-save` 入库的流程。
- `docker-compose.yml` 增加 AI 环境变量透传，`README.md` 补充硅基流动配置说明，避免将真实 API Key 写入仓库。
- 新增 `backend/tests/test_ai_service.py` 覆盖硅基流动请求体、JSON 解析、空响应报错和不再回退占位题；已通过后端 unittest 发现集验证。

## 2026-06-10 AI 出题 502 配置加载修复
- 定位管理端点击 AI 生成题目返回 502 的根因：后端运行时未读取到 `SALES_TRAINING_AI_API_KEY`，服务层因此返回“AI_API_KEY 未配置”错误。
- 调整后端配置加载路径，`Settings` 同时读取项目根目录 `.env` 和 `backend/.env`，兼容从仓库根目录或 `backend/` 目录启动后端服务。
- 配置解析增加 `extra="ignore"`，避免本地 `.env` 中存在其他环境变量时导致后端启动失败。
- 本地补充未提交的 `backend/.env` 运行配置后，已通过真实硅基流动接口生成 1 道题目草稿，验证 `/questions/ai-generate` 依赖的服务层链路可用。
- 新增 `backend/tests/test_config.py` 覆盖 `.env` 候选路径配置，避免后续启动目录变化再次导致 AI Key 读取失败。

## 2026-06-10 AI 出题严格依据视频内容
- 管理端 AI 出题页删除“字幕/转写”输入，只保留“补充要求”可选项，作为用户出题角度建议传给后端。
- 后端 `/questions/ai-generate` 请求结构删除 `transcript` 字段，新增 `user_requirements` 字段，并禁止额外字段，避免旧字幕/转写参数继续混入生成链路。
- AI 服务改为使用视频 `description` 作为唯一视频内容文本来源传给大模型；视频内容为空时直接返回明确错误，避免模型只凭标题、知识点或用户建议发挥。
- 大模型提示词强化为“题干、答案和解析必须能从 video_content 直接得到支撑”，并明确用户补充要求只能作为建议，不能替代或扩展视频事实。
- 补充后端测试覆盖视频内容必填、用户建议透传、移除字幕/转写字段和严格提示词结构；管理端构建已通过。

## 2026-06-10 AI 出题接入硅基流动多模态视频输入
- 按硅基流动多模态视觉文档调整 AI 出题请求，`/questions/ai-generate` 现在通过 Chat Completions 的 `video_url` content part 传入视频画面，由多模态模型直接读取视频内容生成题目。
- 当时默认模型改为 `Qwen/Qwen3.5-397B-A17B`，并新增 `SALES_TRAINING_AI_VIDEO_DETAIL`、`SALES_TRAINING_AI_VIDEO_MAX_FRAMES`、`SALES_TRAINING_AI_VIDEO_FPS`、`SALES_TRAINING_AI_VIDEO_MAX_INLINE_MB` 配置控制视频抽帧和本地视频内联大小。
- 对 `http(s)` 视频地址直接传 URL；对 `/uploads` 本地视频，在不超过内联大小上限时转为 `data:video/...;base64,...` 发送给硅基流动；文件缺失或过大时返回明确错误。
- 管理端 AI 出题页文案改为“根据视频画面内容生成题目”，补充要求继续作为建议传给模型，不能替代视频事实。
- 后端新增多模态请求体、本地视频 data URL、远程视频 URL 和缺失文件错误测试；后端 unittest 与管理端构建均已通过。

## 2026-06-10 AI 出题多模态模型与错误日志修复
- 根据硅基流动视频输入文档，将默认多模态模型从图片视觉模型 `Qwen/Qwen2.5-VL-72B-Instruct` 调整为视频示例模型 `Qwen/Qwen3.5-397B-A17B`，避免供应商返回 `Model disabled`。
- 后端 `/questions/ai-generate` 捕获 AI 生成异常时新增 warning 日志，后续 502 会在后端日志中明确输出视频 ID 与供应商返回原因。
- 本地同视频复测确认模型禁用问题已消除；当前硅基流动返回 `account balance is insufficient`，需要在供应商账户充值或更换可用 API Key/模型后才能继续生成。

## 2026-06-10 AI 模型配置切回 Qwen3.5-4B
- 按要求将后端默认 AI 模型、Docker Compose 环境变量默认值、README 示例和本地 `backend/.env` 统一改为 `Qwen/Qwen3.5-4B`。
- 保留现有多模态视频输入请求结构与视频帧参数配置；若供应商侧该模型不支持 `video_url` 视频输入，需更换为支持视频能力的模型或调整供应商模型权限。

## 2026-06-10 AI 出题切换阿里云百炼平台
- 后端 AI 出题默认供应商从硅基流动切换为阿里云百炼 OpenAI 兼容接口，默认 `SALES_TRAINING_AI_BASE_URL` 改为 `https://dashscope.aliyuncs.com/compatible-mode/v1`，默认模型改为 `qwen3.6-flash`。
- 按百炼视频理解文档调整多模态请求体，`video_url` 仅保留视频 `url`，抽帧频率通过同级 `fps` 字段传入，不再发送旧供应商相关的 `detail`、`max_frames`、`enable_thinking` 和 `response_format` 字段。
- 本地未提交的 `backend/.env` 已写入百炼 API Key、模型、Base URL、超时时间和视频内联大小配置；真实 API Key 仍不写入 README、Docker Compose 或其他受版本控制文件。
- `docker-compose.yml` 与 `README.md` 同步百炼环境变量示例，并将本地视频 data URL 内联上限默认调整为 100MB，降低已上传视频因默认上限过小导致生成失败的概率。
- 后端测试已更新为校验百炼视频请求结构、data URL 编码和异常处理，管理端 AI 出题页面继续通过“补充要求”向大模型传递用户建议。

## 2026-06-10 AI 出题切换 Qwen-Omni 全模态模型
- 根据 PPT 讲解类视频需要同时理解画面和讲解音频的需求，AI 出题模型从 `qwen3.6-flash` 调整为百炼 `qwen3.5-omni-flash`，题目依据扩展为视频画面和音频讲解，用户补充要求仍仅作为出题角度建议。
- 按 Qwen-Omni 文档要求将 Chat Completions 请求改为 `stream=true`，并新增流式 SSE 响应解析，继续从模型输出中提取 `questions` JSON。
- 按文档中 Base64 文件小于 10MB 的限制，将 `SALES_TRAINING_AI_VIDEO_MAX_DATA_URL_CHARS` 默认改为 `10000000`，避免再次触发百炼请求体字符串过长错误。
- 本地 `/uploads` 视频超过 Base64 限制时，会自动生成 `uploads/ai-cache/*.ai.mp4` AI 识别压缩版；压缩版降低分辨率和码率但保留音频，确保 PPT + 人声讲解视频仍能被全模态模型理解。
- `backend/.env`、`docker-compose.yml`、`README.md` 和后端测试同步新增 `SALES_TRAINING_AI_VIDEO_COMPRESS_AUDIO_BITRATE` 等配置，覆盖 Omni 模型、流式载荷和保留音频压缩行为。

## 2026-06-10 AI 出题答案与解析校验修复
- 后端 AI 出题提示词补强题型约束：单选答案只能为 A/B/C/D 中一个，多选答案只能使用 A/B/C/D 并以英文逗号分隔，判断题 `true_false` 只能使用 A/B，且固定 A=正确、B=错误，禁止返回 C/D。
- 后端要求每道题 `analysis` 必须与题目和答案严格对应，明确引用视频画面或音频讲解中的时间段证据，并逐项说明每个选项正确或错误的原因；判断题也必须说明该陈述为何正确或错误。
- 后端规范化 AI 题目时新增答案范围校验，若判断题返回 C/D 或任意题型答案不在实际选项内，会直接返回 AI 生成错误，避免无效题目进入管理端审核和题库。
- 管理端 AI 审核保存前补充答案范围校验，防止异常草稿或人工编辑后的非法答案继续入库。
- 补充后端单元测试覆盖判断题非法答案拦截，以及提示词中 A/B 判断题规则、时间段证据和逐项解析规则。

## 2026-06-10 管理端删除确认弹窗居中修复
- 新增管理端统一危险操作确认工具，所有删除/归档确认统一使用居中的 Element Plus MessageBox，不再使用贴着表格行展示的 Popconfirm。
- 题目管理、用户管理、门店管理、分类管理、试卷管理、产品知识、话术管理和视频管理的单条删除/归档按钮改为普通文本按钮，点击后弹出居中确认框。
- 题目管理的批量删除按钮同步改为统一居中确认框，保证单条删除和批量删除的确认体验一致。
- 管理端构建已通过，保留现有 Sass legacy API、Rollup 注释和 chunk size 警告。

## 2026-06-10 管理端删除确认弹窗样式优化
- 管理端保留现有 `confirmDanger()` 和 Element Plus MessageBox 交互链路，仅调整 `.confirm-dialog` 危险确认弹窗样式。
- 删除确认弹窗改为标准居中危险操作视觉：标题区分隔更清晰，关闭按钮固定在右上角，内容区留白正常，底部按钮右对齐。
- 确认按钮在 `.confirm-dialog` 内统一显示为红色危险按钮，取消按钮保持 Element Plus 默认次级按钮样式，避免影响普通 MessageBox 弹窗。

## 2026-06-10 培训端用户姓名刷新修复
- 确认培训端用户已通过后端 `/auth/phone-login` 和 `/auth/user-info` 与数据库 `users.real_name` 关联，页面显示姓名来源为 `authStore.userName`。
- 新增培训端用户信息规范化逻辑，兼容后端返回的 `name`、`real_name`、`realName` 和 `username` 字段，避免字段形状不一致时姓名显示异常。
- 调整培训端路由鉴权逻辑：有 token 时每次应用启动至少刷新一次 `/auth/user-info`，用数据库最新姓名覆盖浏览器 `localStorage` 中旧的 `auth-user` 缓存。
- 补充用户信息规范化测试，并通过培训端 `npm run build` 验证。

## 2026-06-11 AI 开发文档维护规则固化
- 在 `AGENTS.md` 中明确 `AGENTS.md`、`README.md`、`update.md` 三类文档的职责边界：AI 协作规则入口、使用者/开发者手册、持续追加变更日志。
- 固化文档触发更新规则：长期协作规则和开发约定变化更新 `AGENTS.md`，环境依赖、启动配置和使用方式变化更新 `README.md`，重要功能、接口、配置、数据库或业务流程变化追加 `update.md`。
- 明确 `update.md` 记录格式需包含日期、变更主题、影响范围和要点，并规定文档规范本身变更也需要追加变更日志。

## 2026-06-11 产品分类与 AI 出题表单修复
- 管理端 AI 出题页将“关联视频”默认值从 `0` 调整为空选择状态，默认展示“请选择视频”，并优化生成配置表单在窄宽度下的标签、滑块和数字输入布局，避免用户横向滑动才能看完整表单。
- 管理端分类页面文案统一为产品分类语义，分类列表的视频数量改为读取后端返回的真实 `video_count`，用于展示每个产品分类下已关联视频数量。
- 后端分类接口新增按 `videos.category_id` 统计的视频数量返回，并在删除分类时拦截已有视频关联的产品分类，避免视频挂到已停用分类。
- 视频上传/编辑流程将所属分类改为必填：管理端增加表单校验，后端 `VideoCreate.category_id` 改为必填，并在创建和更新时校验分类存在且启用。
- 补充后端 `unittest` 覆盖分类响应视频数量和视频创建分类必填；已通过后端相关测试和管理端 `npm run build` 验证。

## 2026-06-11 产品分类上级分类选择框修复
- 修复管理端产品分类新增弹窗中“上级分类”选择框点击选择后消失的问题。
- 根因是选择框显示条件直接绑定 `form.parentId`，选择父分类后组件被 `v-if` 卸载；现改为使用独立的 `parentSelectorVisible` 控制显示，选择值变化不会影响控件存在。
- 已通过最小回归检查确认不再存在 `v-if="!form.parentId"` 绑定，并通过管理端 `npm run build` 验证。

## 2026-06-11 销售角色与权限调整需求文档
- 新增 `docs/sales-role-permission-adjustment.md`，固化管理端单管理员角色、培训端销售/学员双角色的权限划分。
- 明确销售看板和销售方法论对所有销售角色可见，销售可上传个人销售语音文件，管理员可后台查看全部销售语音文件。
- 明确 Agent 话术演练本阶段只做培训端前端入口展示，入口放在“实战演练”页面最上方，管理员后台暂不查看演练记录，后续再完善记录、评分和复盘闭环。

## 2026-06-11 生产环境部署配置

### 影响范围
- **基础设施**：`docker-compose.yml`、`backend/Dockerfile`、新增 `nginx/default.conf`、`.env.example`、`admin-web/vite.config.ts`、`admin-web/.env.production`
- **管理端**：vite.config.ts 增加 `base` 环境变量支持，新增 `.env.production` 设置 VITE_BASE=/admin/
- **培训端**：无变动（Hash 路由 + 根路径部署）
- **后端**：Dockerfile 增加 ffmpeg 系统依赖

### 变更要点
- `docker-compose.yml` 重写为生产版：新增 `celery-worker`（AI 出题异步任务）与 `nginx`（统一入口）服务；各服务端口不再对外暴露（仅 Nginx 80 端口对外）；backend 去掉 `--reload` 热重载标志；MySQL/Redis 端口注释掉不再暴露到宿主机。
- `backend/Dockerfile` 增加 `ffmpeg` 系统包，确保容器内视频转码可用。
- 新建 `nginx/default.conf`：统一入口配置，培训端 `/`（默认），管理端 `/admin`，`/api` 反向代理到 backend，`/uploads` 由 Nginx 直接返回静态文件提高性能，限制上传 500MB。
- 新建 `.env.example` 生产环境变量模板，覆盖数据库、JWT、AI 出题、分页等全部可配项。
- `admin-web/vite.config.ts` 增加 `base` 从环境变量 `VITE_BASE` 读取，新建 `admin-web/.env.production` 设置 `VITE_BASE=/admin/`，使管理端构建产物正确匹配 Nginx `/admin` 子路径部署。
- 新建 `deploy.sh` 一键部署脚本，自动检查依赖、构建前端、启动服务、运行迁移。
- 保留现有 `backend/deploy/nginx-videos.conf` 作为参考，生产使用 `nginx/default.conf`。

## 2026-06-12 销售角色与权限调整（角色统一 + 销售功能）

### 影响范围
- **后端**：`core/dependencies.py`、`api/v1/users.py`、`api/v1/stores.py`、`api/v1/categories.py`、`api/v1/videos.py`、`api/v1/scripts.py`、`api/v1/products.py`、`api/v1/questions.py`、`api/v1/exam_papers.py`、`api/v1/dashboard.py`、`api/v1/auth.py`、新增 `api/v1/sales.py`、新增 `models/sales_methodology.py`、新增 `models/sales_audio_file.py`、新增迁移 `c01_role_unify_sales_tables.py`、`schemas/user.py`、`seed_data/seed_all.py`
- **管理端**：`types/index.ts`、`router/index.ts`、`stores/auth.ts`、`stores/app.ts`、`views/users/index.vue`、`views/users/detail.vue`
- **培训端**：`types/index.ts`、`stores/auth-user.ts`、`stores/auth.ts`、`router/index.ts`、`components/layout/TabBar.vue`、`views/practice/index.vue`、新增 `api/sales.ts`、新增 `views/sales/dashboard.vue`、新增 `views/sales/methodology.vue`

### 变更要点

**角色统一**
- 系统角色由旧的 `super_admin`/`training_admin`/`instructor`/`student` 统一为 `admin`/`sales`/`student` 三种。
- 新增 Alembic 迁移 `c01_role_unify_sales_tables.py`，upgrade 时自动将旧角色值迁移为 `admin`，并创建 `sales_methodologies` 和 `sales_audio_files` 两张新表。
- 测试种子账号同步更新：admin(admin123)、admin2(admin123)、sales1(sales123)、student(student123/验证码 123456)。

**后端权限收紧**
- 新增四个权限依赖快捷函数：`require_admin()`、`require_training_user()`（sales+student）、`require_sales()`、`require_sales_or_admin()`。
- `/users`、`/stores`、`/questions`、`/exam-papers` 全部接口限 admin；`/categories`、`/videos`、`/scripts`、`/products` 写操作限 admin；`/dashboard/admin-overview` 和导出接口限 admin。
- 手机验证码登录支持 `sales` 和 `student` 角色（旧版仅 `student`）。
- 登录返回的 `TrainingUserResponse` 新增 `role` 字段，培训端可感知当前登录角色。

**新增销售专属 API**（`/api/v1/sales/`）
- `GET /sales/dashboard`：销售看板统计（sales/admin 可访问）。
- `GET/POST/PUT/DELETE /sales/methodologies`：销售方法论 CRUD（读操作 sales/admin，写操作 admin）。
- `POST /sales/audio-files`：销售上传个人语音文件（仅 sales）。
- `GET /sales/audio-files/my`：查看自己上传的语音文件（仅 sales）。
- `GET /sales/admin/audio-files`：管理员查看全部销售语音文件（仅 admin）。

**管理端调整**
- `UserInfo.role` 类型更新为 `'admin' | 'sales' | 'student'`。
- 路由守卫：登录后检查 `role !== 'admin'`，非管理员角色跳回登录页（含 `error=no_permission` 参数）。
- 用户管理角色选项和表格 Tag 统一为管理员/销售/学员，移除旧的"培训师"选项。
- 侧边栏用户管理子菜单增加"销售管理"入口。

**培训端调整**
- `UserInfo` 增加 `role` 字段；auth store 暴露 `userRole` 和 `isSales` computed。
- 路由守卫：非 `sales`/`student` 角色自动退出；带 `requiresSales: true` 的路由对学员不可访问。
- TabBar 根据角色动态显示：sales 角色额外展示「看板」和「方法论」两个 tab。
- 新增销售看板页（`/sales/dashboard`）和销售方法论列表页（`/sales/methodology`）。
- 实战演练页面顶部新增 AI 话术演练横幅卡片（当前为占位入口，点击弹 Toast，后续对接实际 Agent）。

**文档同步**
- 更新 `README.md`：默认账号表、角色说明、端口说明。
- 更新 `AGENTS.md`：角色系统说明、常用命令（含 seed 数据步骤）、端口说明。

## 2026-06-12 后端视频接口启动报错修复
- 影响范围：后端 `app/api/v1/videos.py` 启动导入链路；管理端、培训端页面和接口契约无变化。
- 要点：补充 `fastapi.Depends` 导入，修复视频路由中 `Depends(require_admin())` 在模块加载阶段触发 `NameError`，恢复后端启动导入。

## 2026-06-12 管理端登录跳转修复 + 响应格式统一

### 影响范围
- **后端**：`app/schemas/user.py`（新增 `LoginTokenPayload`）、`app/api/v1/auth.py`（`/auth/login` 响应改为 `ApiResponse` 包裹）
- **管理端**：`stores/auth.ts`（`login()` 兼容新旧格式 + token 缺失显式 throw）、`views/login/index.vue`（catch 加 `console.error`）、`router/index.ts`（`beforeEach` 加诊断 `console.warn`）
- **基础设施**：`docker-compose.yml`（MySQL/Redis 端口重新暴露给宿主机）

### 变更要点
- `docker-compose.yml`：MySQL `3306` 和 Redis `6379` 端口取消注释，恢复宿主机可访问，确保本地开发后端可直接连接容器内数据库。
- 后端 `/auth/login` 响应统一为 `{ code, message, data: { token, refreshToken, user } }` 格式，与 `/auth/phone-login` 保持一致；`LoginTokenPayload` 包含 `token`、`refreshToken`、`user` 三个字段。
- 管理端 `authStore.login()` 支持 ApiResponse 包裹和旧裸格式双路径，token 或 user 缺失时显式 throw 明确错误，避免 `undefined` token 写入 localStorage 后 `JSON.stringify` 丢弃该键，导致 `router.beforeEach` 将登录态误判为空并踢回登录页。
- 管理端路由守卫 `beforeEach` 兼容旧角色值（`super_admin`/`training_admin`/`instructor`）按 admin 放行；`authStore.login()` 存储前自动将旧角色值标准化为 `admin`，双重防御。
- 修复本地数据库 admin 用户 role 仍为 `super_admin` 的问题（UPDATE 为 `admin`），根因是旧 seed 数据未随迁移更新。

## 2026-06-12 管理端销售管理页面

### 影响范围
- **后端**：`app/api/v1/sales.py`（新增 `GET /sales/admin/sales-list`）、`app/models/sales_methodology.py`（修复 TEXT 列默认值）、`alembic/versions/c01_role_unify_sales_tables.py`（修复 TEXT 列 server_default）
- **管理端**：`stores/app.ts`（侧边栏菜单重组合并）、新增 `views/sales/index.vue`（卡片网格页面）、新增 `api/sales.ts`、`router/index.ts`（新增 `/sales` 路由）

### 变更要点
- 管理端侧边栏「用户管理」子菜单从 3 项（管理员/销售管理/学员管理）重组合并为 2 项：「账号管理」（`/users`）和「销售管理」（`/sales`）。
- 新建销售管理页：卡片网格展示每位销售的头像、姓名、销售次数、成交次数、方法论数量；点击「查看方法论」弹窗展示该销售的方法论列表。
- 后端新增 `GET /sales/admin/sales-list` 接口，一次性返回所有销售用户及其方法论列表，避免前端多次请求。
- 修复 Alembic 迁移 `c01_role_unify_sales_tables` 中 TEXT 列设置 `server_default` 导致 MySQL 1101 错误的问题；同步修正 `SalesMethodology.tags` 模型定义。

## 2026-06-12 培训端销售看板与方法论改造

### 影响范围
- **后端**：`app/api/v1/sales.py`（`/admin/sales-list` 权限放宽为 `require_sales_or_admin`；`POST /methodologies` 创建权限放宽；新增 `POST /methodologies/generate` AI 生成草稿接口）
- **培训端**：`components/layout/TabBar.vue`（导航栏重排序）、`views/sales/dashboard.vue`（卡片网格重做）、`views/sales/methodology.vue`（上传→AI生成→保存流程）、`api/sales.ts`（新增 `getSalesList`、`createMethodology`）

### 变更要点
- 培训端底部导航栏重排序：顺序变为「首页 | 课程 | 演练 | 考试 | 看板 | 方法论 | 我的」，「我的」固定在最右端。
- 培训端销售看板改为卡片网格布局：每个销售一个卡片，展示头像、销售次数、成交次数、方法论数量，点击按钮弹窗查看方法论。
- 培训端方法论页面改为全流程：上传录音 → 调用 AI 生成方法论草稿 → 预览 → 保存到账户，保存后显示在个人方法论列表中。
- 后端新增 `POST /sales/methodologies/generate`：两段式 AI 管道 — ① `qwen3-asr-flash`（DashScope）语音转写 ② `qwen3.6-flash`（OpenAI 兼容 Chat Completions）提炼方法论 JSON。新增 `dashscope` 依赖和 `methodology_model` 配置。AI 未配置时返回占位说明。
- 修复培训端 axios 全局 `Content-Type: application/json` 导致 FormData 文件上传报 422 的问题，改为不设默认头由 axios 自动判断。
- 修复方法论页上传按钮 `<label>` 嵌套导致点击事件重复触发的问题。

## 2026-06-13 AI 话术演练 Agent 功能

### 影响范围
- **后端**：新增 `app/models/practice_session.py`（PracticeSession/PracticeMessage/LongTermMemory 模型）、新增 `alembic/versions/d01_add_practice_tables.py` 迁移、新增 `app/services/practice_agent.py`（Agent 循环引擎 + SSE 流式）、新增 `app/services/practice_tools.py`（MCP 工具层：search_scripts/get_product_info/get_methodology/evaluate_response）、新增 `app/services/practice_memory.py`（三层记忆管理）、新增 `app/services/user_profile.py`（用户画像服务）、新增 `app/api/v1/practice.py`（会话 CRUD + SSE 聊天端点）、新增 `app/schemas/practice.py`（Pydantic schema）、修改 `app/core/config.py`（agent_model 等配置）、修改 `app/api/v1/router.py`、修改 `requirements.txt`（新增 mcp 依赖）
- **培训端**：新增 `views/practice/agent.vue`（场景选择 + 对话聊天页）、新增 `api/practice.ts`（SSE 流式 API 封装）、修改 `router/index.ts`（新增 `/practice/agent/:moduleCode?` 路由）、修改 `views/practice/index.vue`（横幅跳转至 Agent 页）、修改 `types/index.ts`（新增实践相关类型）

### 变更要点
- **Agent 引擎**：实现完整 Agent 循环，支持 MCP 工具调用（最多 3 次迭代）。每轮对话自动注入用户画像 + 当前会话上下文 + 相关长期记忆。流式输出使用 SSE（text/tool_call/tool_result/evaluation/done 事件）。
- **MCP 工具层**：4 个注册工具 — `search_scripts`（话术搜索）、`get_product_info`（产品查询）、`get_methodology`（方法论检索）、`evaluate_response`（回复质量评估 1-5 分）。
- **三层记忆**：用户画像（聚合 6 类数据源）→ 当前会话（最近 N 轮上下文）→ 长期记忆（重要性评分 + 召回计数 + 去重合并）。会话结束后自动提取洞察写入长期记忆。
- **培训端对话页**：8 个演练场景选择 → 聊天气泡 UI → SSE 实时流式渲染 → 每轮评估卡片（亮星 + 亮点 + 改进建议）→ 会话结束评分。
- **模型配置**：默认使用 `qwen3.6-plus-2026-04-02`，通过 `SALES_TRAINING_AGENT_MODEL` 环境变量配置，复用现有 `SALES_TRAINING_AI_BASE_URL` 和 `SALES_TRAINING_AI_API_KEY`。
- 新增 `mcp>=1.0.0` Python 依赖；数据库新增 `practice_sessions`、`practice_messages`、`long_term_memories` 三张表。

## 2026-06-15 培训端图标显示修复

### 影响范围
- **培训端**：课程分类页、产品知识页、实战演练页、考试页、话术详情/列表复制按钮。

### 变更要点
- 修复培训端使用不存在的 Vant 图标名导致图标空白的问题，将 `medical-o`、`aiming-o`、`glasses-o`、`scan-o`、`flash-o`、`copy-o` 替换为 Vant 4 已支持且语义接近的内置图标。
- 课程分类中“斜弱视”改用 `closed-eye`，“角塑”改用 `aim`，保证截图所示分类卡片能正常显示图标。
- 同步检查其余培训端硬编码 Vant 图标，确认静态图标名均存在于本地 Vant 图标字体中。
- 已通过培训端 `npm run build` 验证。

## 2026-06-15 分类管理修复与视频分类导入

### 影响范围
- **后端**：分类 Schema、分类创建接口。
- **管理端**：分类管理页面（间接，无需改前端）。

### 变更要点
- 修复分类管理「添加子分类」失败的问题：根因是 `CategoryCreate` schema 的 `code` 字段为必填但管理端表单从未发送该字段，后端返回 422 校验错误。
- 将 `CategoryCreate.code` 改为 `Optional[str]`（默认 `None`）；`create_category` 端点新增自动生成逻辑：若 code 为空则通过 `pypinyin` 根据 name 生成拼音编码，并自动追加后缀去重。
- 新增依赖 `pypinyin>=0.55.0` 写入 `requirements.txt`。
- 新增导入脚本 `backend/seed_data/import_video_categories.py`：遍历 `C:\Users\Admin\Desktop\培训视频` 文件夹结构，将 4 个一级文件夹导入为顶级分类、29 个二级子文件夹导入为对应父分类下的子分类。脚本幂等，按 `name + parent_id` 去重。

## 2026-06-15 视频上传流程改造与批量导入

### 影响范围
- **后端**：`videos.py`（create / update_video_status / batch_update_video_status 端点）、视频导入脚本。
- **管理端**：视频上传页（edit.vue）、视频列表页（index.vue）、types 定义。

### 变更要点
- **上传=草稿**：`create_video` 端点不再自动触发后台转码，新建视频固定为 `draft` 状态，从 `BackgroundTasks` 移除转码触发。
- **手动上架才转码**：`update_video_status` 和 `batch_update_video_status` 端点在目标状态为 `published` 时，先设为 `transcoding` 再通过 `background_tasks` 触发 `_transcode_and_publish` 后台转码。转码完成后自动更新 `file_size`、`resolution`、`cover_url` 并设为 `published`，转码后文件原地替换原文件（`compress_mobile_mp4_in_place` 逻辑不变）。
- **管理端上传页**：新建视频时隐藏"上下架状态"选择器，固定显示"草稿"标签+提示文字；编辑已有视频时增加 `transcoding` 选项。
- **管理端列表页**：`transcoding` 状态时显示"转码中..."标签，隐藏上架/下架操作按钮，避免重复触发转码。
- **类型更新**：`Video`/`VideoUploadParams` 的 `status` 类型新增 `'transcoding'`。
- 新增批量导入脚本 `backend/seed_data/import_videos.py`：遍历培训视频文件夹，匹配二级分类，复制视频到 `uploads/videos/` 并做 faststart remux + 元数据提取 + 封面生成，创建 `draft` 状态记录。共导入 175 个视频。

## 2026-06-15 考试模块 L1/L2/L3 等级改革

### 影响范围
- **后端**：`app/api/v1/exams.py`（LEVEL_RULES、ensure_paper_for_level、questions_for_level、submit_exam、exam_record_payload、get_exam_config）
- **培训端**：`views/exam/index.vue`（默认卡片和确认文案）、`views/exam/result.vue`（通过标准和差几题提示）、`types/index.ts`（ExamConfig/ExamRecord 增加 passRate）
- **管理端**：`views/exams/index.vue`（列表及格分列显示百分比）、`views/exams/edit.vue`（概要卡及格分显示百分比）

### 变更要点
- **等级参数调整**：L1 改为 20 题/80% 通过（passScore=16/totalScore=20）、L2 改为 25 题/85% 通过（passScore=22/totalScore=25）、L3 改为 30 题/90% 通过（passScore=27/totalScore=30）。每题值 1 分，passScore = ceil(题数 × 通过率)。
- **随机抽题**：每次考试从题库中按难度过滤后 `random.shuffle()` 随机选取题目，不再复用固定试卷的 `question_ids`，确保每次考试题目不同。
- **提交安全**：submit_exam 对 L1/L2/L3 优先使用用户提交的 body.answers 中的 questionIds，避免并发请求覆盖 paper.question_ids 导致评分错乱。
- **通过率展示**：后端配置和记录接口均返回 `passRate` 字段；培训端考试入口确认框和结果页展示"正确率 ≥ XX% 及格"；结果页未通过时提示"还差 X 题即可通过"。
- **管理端**：试卷列表和编辑页的及格分旁增加百分比换算显示。

## 2026-06-15 考试模块难度去除与时长统一

### 影响范围
- **后端**：`app/api/v1/exams.py`（LEVEL_RULES 删除 difficulty、find_paper_for_level 简化、ensure_paper_for_level/questions_for_level 不再按难度过滤、question_payload 增加 exam_level 参数、submit_exam 创建试卷不再写入 difficulty_level）
- **培训端**：`views/exam/index.vue`（defaultCards duration 统一为 60）

### 变更要点
- **去除难度过滤**：L1/L2/L3 考试不再按 `difficulty` 字段过滤题目，改为从全量启用题库随机抽取。`LEVEL_RULES` 中所有 level 删除 `difficulty` 键。
- **抽题 fallback 修复**：原逻辑按 difficulty 过滤后候选集可能不足 `questionCount`，且只在候选集为空时才回退全库；现改为直接从全库随机抽取，天然保证题量充足。
- **时长统一**：L1/L2/L3 `duration` 统一改为 60 分钟（原 30/40/50），前后端同步。
- **向后兼容**：`Question.difficulty` 数据库列保留；`difficulty_to_level()` 函数保留作为 `question_payload` 和 `paper_level` 的 fallback；管理端题库管理仍可显示 difficulty 字段。

## 2026-06-17 话术演练 Agent tool_call_id 缺失修复

- **变更**：修复 `run_practice_agent` 重建历史会话消息时，`tool_results` 被错误处理导致发送给 LLM 的 `role: "tool"` 消息缺少 `tool_call_id` 参数，触发 API 400 `MissingParameter` 错误。
- **影响**：`backend/app/services/practice_agent.py` — 会话上下文重建循环（第 457-482 行）：assistant 消息先正常追加，`tool_results` list 中每条 tool result 单独创建 `{role: "tool", tool_call_id, content}` 消息追加，兼容旧版单 dict 格式。
- **验证**：人工审查代码语法正确，缩进和逻辑一致。
