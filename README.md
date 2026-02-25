# 深圳市路段交通运行速度 Web 可视化分析系统

## 1. 项目简介

基于深圳开放数据平台的路段交通运行速度数据，实现**数据采集 → 存储 → 分析 → 可视化**全流程的 Web 系统。支持 10 种图表分析、CSV 导出、图片保存、用户管理、路段收藏等功能。

### 核心功能

| 功能模块     | 说明                                                 |
| ------------ | ---------------------------------------------------- |
| **数据概览** | 统计卡片 + 4 种核心图表预览                          |
| **图表分析** | 10 种 ECharts 图表（折线、柱状、热力、箱线、散点等） |
| **数据导出** | 一键 CSV 导出，图表支持保存为图片                    |
| **用户系统** | 注册/登录、JWT 认证、管理员角色                      |
| **路段收藏** | 收藏感兴趣的路段，查看收藏热度排名                   |
| **建议反馈** | 用户可提交交通改善建议                               |
| **数据管理** | 管理员可查看路段数据、触发数据采集                   |

### 图表一览

1. **24小时速度波动折线图** — 全天速度变化趋势（含最值、标准差）
2. **工作日/周末速度对比** — 双线对比工作日与周末的速度差异
3. **星期-小时速度热力图** — 发现周期性拥堵规律
4. **早晚高峰速度对比** — 早高峰/晚高峰/平峰统计对比
5. **拥堵路段排名 (Top 20)** — 速度最低的路段排行
6. **路段平均速度柱状图 (Top 30)** — 各路段速度分布
7. **速度分布直方图** — 速度区间频率统计
8. **高峰类型速度箱线图** — IQR 离群点识别
9. **路段速度均值-标准差散点图** — 含变异系数(CV)的稳定性分析
10. **每日速度趋势折线图** — 多日速度变化趋势

## 2. 技术栈

| 层级       | 技术                                      |
| ---------- | ----------------------------------------- |
| **前端**   | Vue 3 + Vite 7 + ECharts 6 + Element Plus |
| **后端**   | Python 3.10 + FastAPI + SQLAlchemy        |
| **数据库** | MySQL 8.0                                 |
| **缓存**   | Redis 6 (不可用时自动回退内存缓存)        |
| **部署**   | Docker 胖容器 (一个镜像包含所有服务)      |

## 3. 项目结构

```
.
├── backend/                  # Python 后端
│   ├── app/
│   │   ├── api/             # API 路由 (auth/traffic/analysis/user)
│   │   ├── core/            # 核心模块 (数据库/Redis/认证/日志/配置)
│   │   ├── models/          # SQLAlchemy ORM 模型
│   │   ├── schemas/         # Pydantic 数据校验
│   │   ├── services/        # 业务逻辑层 (SQL 预聚合 + Redis 缓存)
│   │   └── main.py          # FastAPI 应用入口
│   └── scripts/             # 数据采集脚本
│       ├── fetch_data.py    # 全量采集
│       └── generate_sample_data.py  # 样本采集 (推荐)
├── frontend/                 # Vue3 前端
│   ├── src/
│   │   ├── views/           # 页面组件 (Dashboard/Charts/Favorites/Admin)
│   │   ├── components/      # 图表组件 (12个)
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── api/             # Axios API 客户端
│   │   └── router/          # Vue Router
│   └── dist/                # 构建产物 (npm run build 生成)
├── deploy/                   # 部署相关
│   ├── init.sql             # 数据库初始化 (建库建表建用户)
│   └── start.sh             # 容器启动脚本
├── Dockerfile                # 胖容器构建文件
├── .env.example              # 环境变量模板
├── requirements.txt          # Python 依赖
└── README.md                 # 本文件
```

## 4. Docker 部署（推荐）

> 以下操作均在 **Linux** 环境下进行。需要预先安装 **Docker** 和 **Node.js**（用于编译前端）。

### 4.1 前提条件

```bash
# 确认 Docker 已安装
docker --version    # 需要 20.10+

# 确认 Node.js 已安装（仅构建前端时需要）
node --version      # 需要 18+
npm --version
```

如未安装 Docker：

```bash
# Ubuntu / Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 重新登录 shell 使组权限生效
```

### 4.2 获取项目代码

```bash
git clone https://github.com/pradoschimi/shenzhen_traffic_data_analysis_library.git
```

### 4.3 编译前端

```bash
cd frontend
npm install
npm run build       # 产物输出到 frontend/dist/
cd ..
```

### 4.4 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，**必须修改**以下项：

```dotenv
# 深圳开放数据平台 API Key（从 https://opendata.sz.gov.cn 申请）
SZ_OPENDATA_APP_KEY=你的AppKey

# ⚠️ 安全相关，务必修改为复杂密码
MYSQL_PASSWORD=你的MySQL密码
MYSQL_ROOT_PASSWORD=你的Root密码
JWT_SECRET_KEY=一个随机长字符串
```

> 可用 `openssl rand -base64 48` 生成随机 JWT 密钥。

### 4.5 构建 Docker 镜像

```bash
docker build -t sz-traffic-analysis .
```

构建过程约 3-8 分钟（取决于网络速度），镜像约 1.2GB。

### 4.6 运行容器

```bash
docker run -d \
  --name sz-traffic \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  sz-traffic-analysis
```

### 4.7 查看启动日志

```bash
docker logs -f sz-traffic
```

正常启动后会看到：

```
========================================
 所有服务启动完成！
 Web 应用地址: http://0.0.0.0:8000
 默认管理员: admin / admin123
========================================
```

### 4.8 访问系统

打开浏览器访问：**http://服务器IP:8000**

- 默认管理员账号：`admin`
- 默认密码：`admin123`
- 首次启动如配置了 API Key，会自动采集约 13000+ 条样本数据（耗时 2-5 分钟）

### 4.9 常用运维命令

```bash
# 查看容器状态
docker ps

# 查看实时日志
docker logs -f sz-traffic

# 健康检查
curl http://localhost:8000/api/health

# 停止容器
docker stop sz-traffic

# 重启容器
docker restart sz-traffic

# 删除容器（数据库数据会保留在 Docker volume 中）
docker rm -f sz-traffic

# 进入容器调试
docker exec -it sz-traffic bash

# 在容器内手动采集数据
docker exec sz-traffic python3 -m backend.scripts.generate_sample_data

# 在容器内清除 Redis 缓存
docker exec sz-traffic redis-cli FLUSHDB
```

### 4.10 数据持久化

数据库文件存储在 Docker Volume `/var/lib/mysql`。删除容器不会丢失数据，但删除 Volume 会：

```bash
# 查看 Volume
docker volume ls

# ⚠️ 危险操作：彻底删除包含所有数据
docker rm -f sz-traffic
docker volume prune
```

如需将数据挂载到宿主机：

```bash
docker run -d \
  --name sz-traffic \
  -p 8000:8000 \
  --env-file .env \
  -v /path/to/mysql-data:/var/lib/mysql \
  --restart unless-stopped \
  sz-traffic-analysis
```

## 5. 本地开发

适用于需要修改代码、调试功能的开发者。

### 5.1 环境要求

- Python 3.10+
- Node.js 18+ (推荐 20)
- MySQL 8.0+
- Redis 6+ (可选)

### 5.2 后端启动

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入本地数据库连接信息

# 初始化数据库（在 MySQL 中执行 deploy/init.sql）
mysql -u root -p < deploy/init.sql

# 启动后端
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5.3 前端启动

```bash
cd frontend
npm install
npm run dev        # 开发服务器 http://localhost:5173
```

### 5.4 采集数据

```bash
source venv/bin/activate
python backend/scripts/generate_sample_data.py
```

## 6. API 接口文档

启动后访问 **http://服务器IP:8000/docs** 查看 Swagger UI 自动生成的接口文档。

主要接口：

| 路径                            | 方法 | 说明                     |
| ------------------------------- | ---- | ------------------------ |
| `/api/v1/auth/login`            | POST | 用户登录，返回 JWT Token |
| `/api/v1/auth/register`         | POST | 用户注册                 |
| `/api/v1/traffic/overview`      | GET  | 数据概览统计             |
| `/api/v1/traffic/roads`         | GET  | 路段列表                 |
| `/api/v1/analysis/hourly`       | GET  | 24小时速度波动           |
| `/api/v1/analysis/daily`        | GET  | 每日速度趋势             |
| `/api/v1/analysis/heatmap`      | GET  | 热力图数据               |
| `/api/v1/analysis/peak-compare` | GET  | 早晚高峰对比             |
| `/api/v1/analysis/boxplot`      | GET  | 箱线图                   |
| `/api/v1/analysis/scatter`      | GET  | 散点图 (含CV)            |
| `/api/v1/analysis/district`     | GET  | 路段平均速度             |
| `/api/health`                   | GET  | 健康检查                 |

## 7. 架构说明

```
┌──────────────────────────────────────────┐
│              Docker 容器                  │
│                                          │
│  ┌─────────┐  ┌───────┐  ┌───────────┐  │
│  │ MariaDB │  │ Redis │  │  FastAPI   │  │
│  │ :3306   │  │ :6379 │  │  :8000    │  │
│  └────┬────┘  └───┬───┘  └─────┬─────┘  │
│       │           │            │         │
│       └───────────┴────────────┘         │
│                    │                     │
│            SQLAlchemy ORM                │
│                    │                     │
│         TrafficService (SQL聚合)         │
│           + Redis 缓存 (10min)           │
│                    │                     │
│            FastAPI 路由层                 │
│           ┌────────┼────────┐            │
│           │        │        │            │
│        API 接口  静态文件  健康检查       │
│                    │                     │
│            Vue3 SPA (dist/)              │
└──────────────────────────────────────────┘
                     │
                 :8000 暴露
                     │
                 浏览器访问
```

### 性能优化

- **SQL 预聚合**：所有图表数据通过 `GROUP BY` 在数据库层完成聚合，不传输原始数据
- **Redis 缓存**：相同查询参数 10 分钟内直接返回缓存（冷查询 ~20ms，缓存 ~2ms）
- **缓存降级**：Redis 不可用时自动回退到进程内存缓存，系统不会中断
- **前端静态托管**：构建产物由 FastAPI 直接提供，无需额外 Nginx

## 8. 数据来源

- **深圳市开放数据平台**：https://opendata.sz.gov.cn
- **数据集**：城市路段交通运行速度 (资源 ID: 29200_00403590)
- **数据量**：约 1017 万条历史记录
- **样本采集**：系统默认采集约 13000+ 条覆盖 14 天的样本数据

## 9. 常见问题

### Q: 容器启动后无法访问？

检查端口映射：`docker ps` 确认 `0.0.0.0:8000->8000/tcp`。防火墙需放行 8000 端口。

### Q: 数据为空/图表不显示？

进入容器手动采集：`docker exec sz-traffic python3 -m backend.scripts.generate_sample_data`

### Q: 如何修改管理员密码？

登录后在系统内修改，或进入容器用 MySQL 客户端更新 `users` 表。

### Q: 忘记密码？

```bash
docker exec -it sz-traffic mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e \
  "UPDATE sz_traffic_db.users SET hashed_password='\$2b\$12\$LJ3m4ys3Lk0TSwHjSK6gT.3YdQIG/7RG6.MZfNqVMcPnKYD1GxEXC' WHERE username='admin';"
```

密码将重置为 `admin123`。

### Q: 如何更换端口？

```bash
docker run -d -p 80:8000 --env-file .env sz-traffic-analysis
# 此时通过 http://服务器IP 访问（80端口不需要写端口号）
```

## 10. 许可证

本项目仅供学习交流使用。数据版权归深圳市开放数据平台所有。
