# 部署指南

## 你会收到

| 文件 | 说明 |
|------|------|
| `.env` | 所有密钥配置，放项目根目录 |
| `sales_training_dump.sql` | 完整数据库（含所有课程/题目/用户） |

视频已全部迁移到阿里云 OSS，**服务器无需存储任何视频文件**。

---

## 服务器要求

- Linux，≥ 2 核 / 4 GB 内存 / 20 GB 磁盘
- Docker + Docker Compose v2，Git，Node.js 18+
- 出站 HTTPS 443 可访问 `*.oss-cn-hangzhou.aliyuncs.com`

---

## 部署步骤

### 1. 安装依赖

```bash
# Docker
curl -fsSL https://get.docker.com | sh

# Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs
```

### 2. 拉取代码

```bash
git clone https://github.com/zhenqi0401/sales-training.git
cd sales-training
```

### 3. 放入 `.env`

把收到的 `.env` 文件放到项目根目录（与 `docker-compose.yml` 同级）。

**生产必改**：

```bash
SALES_TRAINING_DEBUG=false
SALES_TRAINING_JWT_SECRET_KEY=<openssl rand -base64 48>
SALES_TRAINING_CORS_ORIGINS=["https://你的域名"]
MYSQL_ROOT_PASSWORD=<强密码>
MYSQL_PASSWORD=<强密码>
SALES_TRAINING_DATABASE_URL=mysql+asyncmy://training:<强密码>@mysql:3306/sales_training
```

### 4. 构建前端

```bash
cd admin-web && npm install && npm run build && cd ..
cd training-web && npm install && npm run build && cd ..
```

### 5. 启动数据库

```bash
docker compose up -d mysql
docker compose ps   # 等 mysql 显示 (healthy)
```

### 6. 导入数据库

```bash
docker exec -i training-mysql mysql \
  -u root -p<MYSQL_ROOT_PASSWORD> \
  sales_training < sales_training_dump.sql

docker compose run --rm backend alembic upgrade head
```

> ⚠️ 不要运行 `seed_all.py`。

### 7. 启动所有服务

```bash
docker compose build --pull
docker compose up -d
docker compose logs -f backend   # 确认无报错
```

### 8. 验证

```bash
curl http://localhost/health
```

浏览器打开 `http://服务器IP`，登录后点开任意视频能播放即成功。

---

## Nginx / 域名 / HTTPS

`nginx/default.conf` 已在仓库，需要改的地方：

```nginx
server_name _;   # 改成你的域名
```

HTTPS：文件末尾有 443/SSL 注释模板，放开并挂载证书即可。

同时修改 `.env`：
```bash
SALES_TRAINING_CORS_ORIGINS=["https://你的域名"]
```

---

## 安全加固（必做）

关闭 MySQL 公网端口，编辑 `docker-compose.yml`：

```yaml
# mysql 的 ports 改为：
ports:
  - "127.0.0.1:3306:3306"
```

---

## 常见问题

| 现象 | 处理 |
|------|------|
| 视频播放 403 | `.env` 的 OSS 密钥不对，或刷新页面重新获取签名 URL |
| 发布视频卡在「生成中」 | 服务器出网不通 OSS；检查防火墙 443 出站 |
| 封面图不显示 | `docker compose logs backend` 查报错 |
| `/admin` 页面 404 | 重新执行第 4 步构建前端 |
| 容器启动失败 | `docker compose logs backend`，多为 `.env` 配置缺失 |

---

## 日常运维

```bash
docker compose logs -f backend        # 查日志
docker compose restart backend        # 重启后端
git pull && docker compose build && docker compose up -d   # 更新部署
```
