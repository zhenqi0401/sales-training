# 交付说明（OSS 版增量）— 给部署同事

> 本文件是对原 `部署方案.md` 的**增量补充**。原文档整体流程仍然有效，本文只标注
> **接入阿里云 OSS 后新增 / 变化 / 需要你做的事**。先读本文，再按 `部署方案.md` 走流程。

---

## 0. 一句话变化

视频文件从「存服务器本地 `uploads/`」改为「上传到**阿里云 OSS 私有桶**」。
学员播放时后端实时签发**带时效的 https 签名 URL**，浏览器直连 OSS，**不再经过 Nginx**。
你这边主要多做两件事：**① 在 `.env` 填 OSS 配置；② 确认服务器能出网访问 OSS。**

---

## 1. 我已补齐的两个缺失文件（原仓库里没有，会导致 compose 起不来）

| 文件 | 说明 |
|------|------|
| `nginx/default.conf` | `docker-compose.yml` 挂载的 Nginx 站点配置，原仓库**缺失**，已补。你按需改 `server_name` / 加 HTTPS。 |
| `.env.example` | 已补 OSS 配置段（第 2 节） |

> `backend/deploy/nginx-videos.conf` 是过时示例（路径写的 `/data/videos/`），**忽略它**，以 `nginx/default.conf` 为准。

---

## 2. `.env` 必填 —— 新增 OSS 段（关键）

`docker-compose.yml` 里 `backend` 服务 `env_file: - .env`，所以**根目录 `.env`** 必须包含以下变量。
真实的 AccessKey / Secret / Bucket 由我（系统负责人）单独给你，**不要进 git、不要写进任何文档**：

```bash
# ---------- 阿里云 OSS ----------
SALES_TRAINING_OSS_ENABLED=true
SALES_TRAINING_OSS_ACCESS_KEY_ID=<我单独给你>
SALES_TRAINING_OSS_ACCESS_KEY_SECRET=<我单独给你>
SALES_TRAINING_OSS_BUCKET=<我单独给你，如 training-site-assets>
SALES_TRAINING_OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com   # 杭州地域
SALES_TRAINING_OSS_PUBLIC_BASE_URL=                        # 留空即可（没接 CDN）
```

- `OSS_ENABLED=false` 时系统回退到本地存储（老逻辑），便于排障对照。
- 其余原有必填项（数据库密码、JWT、AI Key、CORS、DEBUG=false）**照 `部署方案.md` 第 4 节不变**。

---

## 3. OSS 桶权限 —— 保持「私有」，不要改公共读 ⚠️

- 桶 ACL **保持私有（private）**。学员播放靠后端签名 URL，不需要公共读。
- **不要**为了图省事把桶设成公共读——那样视频链接会永久公开。

> 可选（暂不需要）：若将来培训端改用 HLS/JS fetch 拉流，需在 OSS 桶配置 **CORS 规则**放行你的域名。
> 当前用浏览器原生 `<video>` 标签播放，**不需要**配 OSS CORS。

---

## 4. 网络要求 —— 后端容器需出网访问 OSS

后端在「上传合并」和「发布出题（从 OSS 下载视频提取音频做 ASR）」时会访问 OSS。
请确认服务器**出站**可达（一般默认放行，无需开入站端口）：

```
出站 HTTPS 443 → *.oss-cn-hangzhou.aliyuncs.com
```

验证（在服务器上）：
```bash
curl -I https://<你的bucket>.oss-cn-hangzhou.aliyuncs.com   # 通即可（403 也算通，说明网络可达）
```

> 同时后端仍需出网访问火山引擎 ARK（AI 出题/ASR），这条原本就需要。

---

## 5. 历史 77G 本地视频怎么处理（需你和我确认）

OSS 只对**上线后新上传**的视频生效。**老视频（约 77G）仍是本地 `/uploads/` 路径**，两条路二选一：

| 方案 | 做法 | Nginx |
|------|------|-------|
| **A. 保留本地（推荐，省事）** | 照 `部署方案.md` 第 7 节把 77G rsync 进 `uploads_data` 卷 | 保留 `nginx/default.conf` 里的 `location /uploads/` |
| **B. 全量迁移到 OSS** | 我方提供迁移脚本，把老视频传 OSS 并改库里 `file_url` | 可删 `location /uploads/`，不用传 77G |

> 默认先按 **A** 来，最稳。要走 B 我再给你迁移脚本和停机窗口安排。
> 新老视频可共存：库里 `file_url` 是 `https://...oss...` 的走 OSS，是 `/uploads/...` 的走本地。

---

## 6. 你负责的 Nginx / 域名 / HTTPS

- **入口配置**：`nginx/default.conf`（已给），路由：`/`→培训端、`/admin/`→管理端、`/api/`→后端、`/uploads/`→历史视频、`/health`→健康检查。
- **域名**：把 `server_name _;` 改成实际域名。
- **HTTPS**：文件末尾有 443/SSL 模板，放开注释、挂载证书即可。
  - 上 HTTPS 后无需担心视频：OSS 签名 URL 已是 **https**，https 页面播放不会触发混合内容拦截（这点我已在代码层修过）。
- **CORS**：后端 `.env` 的 `SALES_TRAINING_CORS_ORIGINS` 填你的实际域名（别用 `["*"]`）。

---

## 7. 部署后验收（在原清单基础上加这几条）

```bash
# 1) 后端能看到 OSS 已启用
docker compose exec backend python -c "from app.core.config import settings; print('OSS:', settings.oss_enabled, settings.oss_bucket)"

# 2) 健康检查
curl http://localhost/health
```

- [ ] `.env` 里 OSS 五项已填，`OSS_ENABLED=true`
- [ ] 服务器能出站访问 `*.oss-cn-hangzhou.aliyuncs.com`
- [ ] OSS 桶**保持私有**（未误设公共读）
- [ ] 管理端**上传一个新视频并发布**：状态能从「生成中」变「已发布」（说明上传→OSS→下载→ASR→出题全通）
- [ ] 培训端打开该新视频**能正常播放**（拿到的是带 `?Signature=` 的 https 链接）
- [ ] 历史视频按方案 A/B 处理完毕，老视频也能播
- [ ] 域名 / HTTPS / CORS 配好

---

## 8. 常见问题速查

| 现象 | 原因 / 处理 |
|------|------------|
| 新视频播放报 `403 AccessDenied` | 多半是签名 URL 过期（默认 12h）或 `.env` 的 AccessKey 不对；刷新页面会重新签发 |
| 上传后发布卡在「生成中」并回退草稿 | 后端无法访问 OSS（出网不通）或 ffmpeg/ARK 异常；看 `docker compose logs -f backend` |
| 后端日志报 `oss2` 找不到 | 镜像没装依赖；`requirements.txt` 已含 `oss2`，重新 `docker compose build` |
| 老视频(/uploads)打不开 | 77G 没灌进卷，或 `location /uploads/` 被删；见第 5 节 |

---

有任何 OSS 相关的报错，把 `docker compose logs backend` 的相关片段发我即可。
