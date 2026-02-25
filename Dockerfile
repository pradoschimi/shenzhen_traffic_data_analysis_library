# ===================================================
# 深圳市路段交通运行速度 Web 可视化分析系统 - 胖容器 Dockerfile
# 一个镜像包含所有服务：MySQL 8.0 + Redis + Python 后端 + Vue3 前端
# 一条 docker run 即可启动完整系统
# ===================================================

FROM ubuntu:22.04

# ---------- 基础环境 ----------
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    LANG=C.UTF-8

# ---------- 安装系统软件包 ----------
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    curl ca-certificates \
    python3 python3-pip python3-dev build-essential \
    mysql-server mysql-client \
    redis-server \
    tzdata && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ---------- MySQL 自定义配置 ----------
# 写入 /etc/mysql/conf.d/ 会被 MySQL 自动加载
# - port=3306         : 确保 TCP 监听
# - bind-address      : 允许容器内所有地址连接
# - default-auth      : PyMySQL 只支持 mysql_native_password
# - skip-host-cache   : 容器环境无需 DNS 缓存
RUN printf '[mysqld]\nport=3306\nbind-address=0.0.0.0\ndefault-authentication-plugin=mysql_native_password\nskip-host-cache\n' \
    > /etc/mysql/conf.d/docker.cnf && \
    # 清空 apt 安装时自动初始化的数据目录（容器首次启动时重新初始化）
    rm -rf /var/lib/mysql/* && \
    # 确保 MySQL 运行目录权限正确
    mkdir -p /var/run/mysqld /var/lib/mysql && \
    chown -R mysql:mysql /var/run/mysqld /var/lib/mysql && \
    chmod 755 /var/run/mysqld

# ---------- 工作目录 ----------
WORKDIR /app

# ---------- Python 依赖（单独一层，利用缓存） ----------
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# ---------- 复制应用代码 ----------
COPY backend/  /app/backend/
COPY deploy/   /app/deploy/
COPY .env.example /app/.env.example

# ---------- 复制前端构建产物 ----------
COPY frontend/dist/ /app/frontend/dist/

# ---------- 启动脚本 ----------
COPY deploy/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# ---------- 端口 / 健康检查 / 持久化 ----------
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD curl -sf http://localhost:8000/api/health || exit 1

VOLUME ["/var/lib/mysql"]

CMD ["/app/start.sh"]
