#!/usr/bin/env bash
# ================================================================
# 销售培训系统 — 一键部署脚本
# 在服务器项目根目录下执行：bash deploy.sh
# ================================================================
set -e

echo "========================================"
echo "  销售培训系统 - 生产环境部署"
echo "========================================"

# ---- 1. 检查依赖 ----
echo ""
echo "[1/6] 检查系统依赖..."

if ! command -v docker &>/dev/null; then
    echo "❌ 未安装 Docker，请先安装: curl -fsSL https://get.docker.com | sh"
    exit 1
fi
echo "  ✓ Docker $(docker --version)"

if ! docker compose version &>/dev/null; then
    echo "❌ Docker Compose 不可用，请安装 Docker Compose v2"
    exit 1
fi
echo "  ✓ Docker Compose $(docker compose version --short)"

# ---- 2. 检查 .env ----
echo ""
echo "[2/6] 检查配置文件..."

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "  ⚠ .env 不存在，从 .env.example 复制..."
        cp .env.example .env
        echo "  ⚠  请编辑 .env 文件，修改数据库密码、JWT Secret 和 AI API Key 后重新运行本脚本"
        echo "     nano .env"
        exit 1
    else
        echo "❌ .env.example 不存在，无法自动创建配置"
        exit 1
    fi
fi
echo "  ✓ .env 已就绪"

# ---- 3. 构建前端 ----
echo ""
echo "[3/6] 构建前端（这可能需要几分钟）..."

# 管理端
if [ -d admin-web ]; then
    echo "  → 构建管理端 (admin-web)..."
    cd admin-web
    npm install --silent
    npm run build -- --base=/admin/
    cd ..
    echo "  ✓ 管理端构建完成"
else
    echo "  ⚠ admin-web 目录不存在，跳过"
fi

# 培训端
if [ -d training-web ]; then
    echo "  → 构建培训端 (training-web)..."
    cd training-web
    npm install --silent
    npm run build
    cd ..
    echo "  ✓ 培训端构建完成"
else
    echo "  ⚠ training-web 目录不存在，跳过"
fi

# ---- 4. 构建镜像并启动 ----
echo ""
echo "[4/6] 构建 Docker 镜像并启动服务..."

docker compose build --pull
docker compose up -d

echo "  ✓ 服务已启动"

# ---- 5. 等待就绪 ----
echo ""
echo "[5/6] 等待服务就绪..."

# 等待后端健康
for i in $(seq 1 30); do
    if curl -s http://localhost/health > /dev/null 2>&1; then
        echo "  ✓ 后端已就绪"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  ⚠ 后端启动超时，请手动检查: docker compose logs backend"
    fi
    sleep 2
done

# ---- 6. 数据库迁移 ----
echo ""
echo "[6/6] 运行数据库迁移与初始化..."

docker compose exec -T backend alembic upgrade head
docker compose exec -T backend python seed_data/seed_all.py

echo "  ✓ 数据库已就绪"

# ---- 完成 ----
echo ""
echo "========================================"
echo "  ✅ 部署完成！"
echo "========================================"
echo ""
echo "访问地址："
echo "  培训端：  http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '服务器IP')"
echo "  管理端：  http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '服务器IP')/admin"
echo "  API 文档：http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '服务器IP')/api/docs"
echo ""
echo "默认账号：admin / admin123"
echo ""
echo "常用命令："
echo "  查看日志：  docker compose logs -f"
echo "  重启服务：  docker compose restart"
echo "  停止服务：  docker compose down"
echo "  更新部署：  git pull && bash deploy.sh"
