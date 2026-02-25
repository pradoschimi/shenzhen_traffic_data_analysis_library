"""
整个后端的入口文件，也就是 FastAPI 应用跑起来的地方。
主要干了这几件事：
  1. 配置跨域（CORS），让前端开发服务器能正常调接口
  2. 把各个模块的路由（auth/traffic/analysis/user）挂到对应的 URL 前缀上
  3. 在生产环境下托管前端打包后的静态文件（Vue 的 dist 目录）
  4. 管理应用的启动和关闭事件，打日志方便排查问题
"""
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 把项目根目录加到 Python 的模块搜索路径里，否则 import backend.xxx 会找不到
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app.core.config import settings
from backend.app.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 的生命周期管理器，用 async with 的方式控制启动和关闭。
    yield 之前的代码在应用启动时执行，yield 之后的在应用关闭时执行。
    如果以后要加数据库连接池初始化、定时任务之类的，都可以放在这里。
    """
    # ===== 启动阶段：打印一些关键配置信息，方便看日志确认环境是否正确 =====
    logger.info("深圳市路段交通运行速度分析系统 正在启动...")
    logger.info(f"运行环境: {settings.app_env} | 日志级别: {settings.app_log_level}")
    logger.info(f"数据库: {settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}")
    yield
    # ===== 关闭阶段：可以在这里做资源清理，比如关连接池什么的 =====
    logger.info("系统正在关闭...")


# 创建 FastAPI 应用实例，这里的 title/description 会显示在 Swagger 文档页面上
app = FastAPI(
    title="深圳市路段交通运行速度分析系统",
    description="基于深圳开放数据平台的路段交通速度采集、分析与可视化系统",
    version="1.0.0",
    lifespan=lifespan,
)

# 跨域配置：开发环境直接放行所有来源，不然前端 localhost:5173 调不了后端 localhost:8000
# 上线的时候记得把 allow_origins 改成实际的域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 把各业务模块的路由注册进来，每个模块负责一块功能 =====
from backend.app.api import auth, traffic, analysis, user

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])        # 登录注册相关
app.include_router(traffic.router, prefix="/api/v1/traffic", tags=["交通数据"])  # 路段和速度数据查询
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["数据分析"])  # 各种聚合分析图表接口
app.include_router(user.router, prefix="/api/v1/user", tags=["用户"])        # 收藏、建议、数据采集等用户功能


@app.get("/api/health", tags=["系统"])
async def health_check():
    """健康检查接口，部署的时候容器编排工具（比如 Docker）会定期调这个来确认服务是否正常"""
    return {"status": "ok", "message": "深圳市路段交通运行速度分析系统运行正常"}


# ===== 在生产环境下，后端同时负责返回前端页面 =====
# 前端 npm run build 之后会生成 frontend/dist 目录，里面就是编译好的 HTML/JS/CSS
FRONTEND_DIST = os.path.join(ROOT_DIR, "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    # 先把 assets 目录（JS/CSS/图片等静态资源）单独挂载，这样请求 /assets/xxx 会直接返回文件
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", tags=["前端"])
    async def serve_frontend(full_path: str):
        """
        兜底路由：所有没被上面 API 路由匹配到的请求，都走这里。
        如果请求的路径对应一个实际文件（比如 favicon.ico），就返回那个文件；
        否则统一返回 index.html，让前端的 Vue Router（history 模式）来处理路由。
        这就是为什么刷新页面不会 404 的原因。
        """
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
