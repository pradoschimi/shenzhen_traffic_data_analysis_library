#!/bin/bash
# ===================================================
# 容器启动入口脚本
# ===================================================

echo "========================================"
echo " 深圳市路段交通运行速度 Web 可视化分析系统"
echo " 容器启动中..."
echo "========================================"

# ==================== 0. 环境变量 ====================
export TZ="${TZ:-Asia/Shanghai}"
export MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
export MYSQL_USER="${MYSQL_USER:-sz_traffic}"
export MYSQL_PASSWORD="${MYSQL_PASSWORD:-SzTraffic@2026}"
export MYSQL_DATABASE="${MYSQL_DATABASE:-sz_traffic_db}"
export MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-SzTraffic@2026Root}"
export REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export APP_HOST="${APP_HOST:-0.0.0.0}"
export APP_PORT="${APP_PORT:-8000}"
export APP_LOG_LEVEL="${APP_LOG_LEVEL:-INFO}"

# 容器内强制 MySQL 端口 3306（本地开发可能用 3307）
export MYSQL_PORT=3306

ln -snf "/usr/share/zoneinfo/$TZ" /etc/localtime && echo "$TZ" > /etc/timezone
echo "[启动] 时区: $TZ"

# ==================== 1. MySQL 初始化和启动 ====================
echo "[启动] 正在启动 MySQL..."

SENTINEL="/var/lib/mysql/.initialized"
NEED_INIT=false

# 如果标志文件不存在，说明需要首次初始化
if [ ! -f "$SENTINEL" ]; then
    NEED_INIT=true

    # 如果 mysql 系统数据库不存在，先 initialize
    if [ ! -d "/var/lib/mysql/mysql" ]; then
        echo "[启动] 首次运行 → 初始化 MySQL 数据目录..."
        mysqld --initialize-insecure --user=mysql --datadir=/var/lib/mysql 2>&1
        echo "[启动] 数据目录初始化完成"
    fi
fi

# ** 正常启动 MySQL（不用 skip-grant-tables）**
# 配置文件 /etc/mysql/conf.d/docker.cnf 已经设置了 port=3306 和 bind-address
mysqld --user=mysql &
MYSQL_PID=$!

# 等待 MySQL 就绪（通过 TCP 探测，最多 60 秒）
echo "[启动] 等待 MySQL 就绪..."
OK=false
for i in $(seq 1 30); do
    if mysqladmin ping -h 127.0.0.1 -P 3306 --silent 2>/dev/null; then
        echo "[启动] MySQL 已就绪（第 ${i} 次探测，TCP:3306）"
        OK=true
        break
    fi
    sleep 2
done
if [ "$OK" != "true" ]; then
    echo "[错误] MySQL 启动超时，查看错误日志："
    tail -20 /var/log/mysql/error.log 2>/dev/null
    exit 1
fi

# ==================== 2. 数据库初始化（仅首次） ====================
if [ "$NEED_INIT" = "true" ]; then
    echo "[启动] 首次启动 → 执行数据库初始化..."

    # initialize-insecure 创建的 root 密码为空
    # 通过 localhost（走 Unix socket）连接，不走 TCP
    # 这样不受 mysql 用户 host 限制
    MCMD="mysql -u root -h localhost"

    # 2a. 创建数据库
    echo "[启动]   → 创建数据库..."
    $MCMD -e "CREATE DATABASE IF NOT EXISTS \`$MYSQL_DATABASE\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

    # 2b. 创建应用用户（使用 mysql_native_password 认证插件）
    echo "[启动]   → 创建应用用户 '$MYSQL_USER'..."
    $MCMD -e "
        CREATE USER IF NOT EXISTS '$MYSQL_USER'@'%'         IDENTIFIED WITH mysql_native_password BY '$MYSQL_PASSWORD';
        CREATE USER IF NOT EXISTS '$MYSQL_USER'@'localhost'  IDENTIFIED WITH mysql_native_password BY '$MYSQL_PASSWORD';
        GRANT ALL PRIVILEGES ON \`$MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'%';
        GRANT ALL PRIVILEGES ON \`$MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'localhost';
        FLUSH PRIVILEGES;
    "

    # 2c. 建表 + 插入默认管理员
    echo "[启动]   → 创建数据表..."
    $MCMD "$MYSQL_DATABASE" < /app/deploy/init.sql

    # 2d. 设置 root 密码
    echo "[启动]   → 设置 root 密码..."
    $MCMD -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '$MYSQL_ROOT_PASSWORD'; FLUSH PRIVILEGES;"

    # 写入标志
    touch "$SENTINEL"
    echo "[启动] 数据库初始化全部完成 ✓"
fi

# ==================== 3. 启动 Redis ====================
if command -v redis-server &>/dev/null; then
    echo "[启动] 启动 Redis..."
    redis-server --daemonize yes --bind 127.0.0.1 --port "$REDIS_PORT"
    echo "[启动] Redis 已启动 (端口 $REDIS_PORT)"
fi

# ==================== 4. 自动采集初始展示数据 ====================
# 检测数据表是否为空
RECORD_COUNT=$(mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -h 127.0.0.1 -P 3306 \
    -N -e "SELECT COUNT(*) FROM $MYSQL_DATABASE.road_speed_records" 2>/dev/null || echo "0")

if [ "$RECORD_COUNT" = "0" ] || [ -z "$RECORD_COUNT" ]; then
    echo "[启动] 数据表为空，启动自动数据采集..."
    cd /app
    # generate_sample_data.py 内部通过 SQLAlchemy 连接数据库
    python3 -m backend.scripts.generate_sample_data 2>&1 | tail -20
    RET=$?
    if [ $RET -eq 0 ]; then
        echo "[启动] 数据采集完成 ✓"
    else
        echo "[警告] 数据采集脚本退出码 $RET，可能部分失败，可稍后手动重新执行"
    fi
else
    echo "[启动] 数据库已有 $RECORD_COUNT 条记录，跳过采集"
fi

# ==================== 5. 启动 FastAPI 并接管生命周期 ====================
echo "========================================"
echo " 所有服务启动完成！"
echo " Web 界面: http://localhost:${APP_PORT}"
echo " 默认管理员: admin / admin123"
echo "========================================"

UVICORN_LOG_LEVEL=$(echo "$APP_LOG_LEVEL" | tr '[:upper:]' '[:lower:]')

cd /app

# 1. 以后台模式启动 FastAPI，保存 PID
python3 -m uvicorn backend.app.main:app \
    --host "$APP_HOST" \
    --port "$APP_PORT" \
    --workers 2 \
    --log-level "$UVICORN_LOG_LEVEL" &
UVICORN_PID=$!

# 2. 定义优雅关机函数
shutdown_handler() {
    echo ""
    echo "[系统] 收到容器停止信号 (SIGTERM/SIGINT)，开始优雅关闭服务..."
    
    # 步骤 A：停止 FastAPI，拒绝新请求
    echo "[关闭] 正在停止 FastAPI..."
    kill -TERM "$UVICORN_PID" 2>/dev/null
    wait "$UVICORN_PID" 2>/dev/null
    
    # 步骤 B：停止 Redis
    if command -v redis-cli &>/dev/null; then
        echo "[关闭] 正在停止 Redis..."
        redis-cli -p "$REDIS_PORT" shutdown 2>/dev/null
    fi

    # 步骤 C：停止 MySQL，释放底层文件锁并刷盘
    echo "[关闭] 正在停止 MySQL，等待 InnoDB 安全退出并释放锁..."
    kill -TERM "$MYSQL_PID" 2>/dev/null
    wait "$MYSQL_PID" 2>/dev/null
    
    echo "[系统] 所有服务已安全退出，容器平稳停止。"
    exit 0
}

# 3. 捕获 Docker 发出的停止信号
trap shutdown_handler SIGTERM SIGINT

# 4. 保持脚本存活，并等待核心业务进程。
# 当执行 docker stop 时，这里会被打断并去执行 shutdown_handler
wait "$UVICORN_PID"
