"""
全局配置模块，项目里所有的配置项都在这里统一管理。
用了 pydantic-settings 这个库，它会自动从 .env 文件和系统环境变量里读取配置值，
这样敏感信息（密码、密钥等）就不用写死在代码里了，部署时候改环境变量就行。
"""
import os
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    全局配置类，每个字段对应一个配置项。
    字段名会自动匹配环境变量（不区分大小写），比如 mysql_host 会读取 MYSQL_HOST 环境变量。
    default 是默认值，如果环境变量和 .env 文件里都没设置就用默认的。
    """

    # ----- 深圳开放数据平台的 API 密钥，在平台注册后可以拿到 -----
    sz_opendata_app_key: str = Field(default="", description="深圳开放数据平台 AppKey")

    # ----- MySQL 连接参数 -----
    mysql_host: str = Field(default="127.0.0.1", description="MySQL 主机地址")
    mysql_port: int = Field(default=3306, description="MySQL 端口")
    mysql_user: str = Field(default="sz_traffic", description="MySQL 用户名")
    mysql_password: str = Field(default="", description="MySQL 密码")
    mysql_database: str = Field(default="sz_traffic_db", description="MySQL 数据库名")
    mysql_root_password: str = Field(default="", description="MySQL root 密码")

    # ----- Redis 连接参数（Redis 是可选的，没有也能跑，只是没有缓存加速） -----
    redis_host: str = Field(default="127.0.0.1", description="Redis 主机地址")
    redis_port: int = Field(default=6379, description="Redis 端口")
    redis_password: str = Field(default="", description="Redis 密码")
    redis_db: int = Field(default=0, description="Redis 数据库编号")

    # ----- JWT 认证相关，用来生成和验证用户的登录 Token -----
    jwt_secret_key: str = Field(default="change_me_in_production", description="JWT 密钥")
    jwt_algorithm: str = Field(default="HS256", description="JWT 签名算法")
    jwt_access_token_expire_minutes: int = Field(default=1440, description="Token 有效期，单位分钟，默认 24 小时")

    # ----- 应用本身的运行参数 -----
    app_host: str = Field(default="0.0.0.0", description="服务监听地址，0.0.0.0 表示接受所有网卡的请求")
    app_port: int = Field(default=8000, description="服务端口号")
    app_env: str = Field(default="development", description="运行环境，development 或 production")
    app_debug: bool = Field(default=True, description="调试模式开关")
    app_log_level: str = Field(default="INFO", description="日志级别：DEBUG/INFO/WARNING/ERROR")

    # ----- 时区设置 -----
    tz: str = Field(default="Asia/Shanghai", description="系统时区")

    @property
    def mysql_url(self) -> str:
        """
        拼接出 SQLAlchemy 需要的数据库连接字符串。
        这里用 quote_plus 对密码做 URL 编码，是因为密码里可能有 @ # 等特殊字符，
        不编码的话会把连接字符串搞乱。
        """
        encoded_password = quote_plus(self.mysql_password)
        return (
            f"mysql+pymysql://{self.mysql_user}:{encoded_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset=utf8mb4"
        )

    @property
    def redis_url(self) -> str:
        """拼接 Redis 连接字符串，格式：redis://[:password@]host:port/db"""
        password_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    class Config:
        env_file = ".env"           # 从项目根目录的 .env 文件加载配置
        env_file_encoding = "utf-8"
        case_sensitive = False       # 环境变量名不区分大小写


# 创建一个全局单例，其他模块 import settings 就能用了，不用到处 new
settings = Settings()
