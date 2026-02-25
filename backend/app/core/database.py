"""
数据库连接管理模块。
这里用 SQLAlchemy 创建了数据库引擎和会话工厂，
整个项目所有和数据库打交道的地方都依赖这个模块。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator

from backend.app.core.config import settings

# 创建数据库引擎（相当于一个连接池管理器）
# 连接池的好处是不用每次请求都新建连接，省了握手开销
engine = create_engine(
    settings.mysql_url,
    pool_size=10,           # 连接池里常驻 10 个连接
    max_overflow=20,        # 高峰期最多再临时创建 20 个，用完就释放
    pool_recycle=3600,      # 每个连接最多用 1 小时就回收，防止 MySQL 那边超时断开
    pool_pre_ping=True,     # 每次从池子里取连接前先 ping 一下，确保连接还活着
    echo=False,             # 设成 True 可以在控制台看到所有执行的 SQL，调试时有用但太吵
)

# 会话工厂：用它来创建数据库会话（Session）对象
# autocommit=False 表示需要手动 commit，autoflush=False 表示不自动把内存中的改动刷到数据库
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# 声明式基类，所有 ORM 模型类都要继承它
# 这样 SQLAlchemy 才知道它们是数据库表的映射
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    给 FastAPI 的依赖注入系统用的。
    在每个 API 请求处理函数里，通过 Depends(get_db) 就能拿到一个数据库会话，
    请求处理完之后（不管成功还是抛异常），finally 里都会自动关闭这个会话，
    这样就不会出现连接泄漏的问题。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
