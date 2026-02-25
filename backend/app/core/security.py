"""
用户认证与密码安全模块。
包含两大块功能：
  1. 密码的哈希和校验（用 bcrypt 算法，数据库里存的是哈希值而不是明文）
  2. JWT Token 的生成和解析（前端用户登录后拿到 Token，之后每次请求带上 Token 来证明身份）
"""
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from backend.app.core.config import settings

# 密码哈希工具，用 bcrypt 算法。这个算法的好处是即使数据库泄露，攻击者也很难反推出原始密码
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 的 Token 提取器，告诉 FastAPI 从请求头的 Authorization: Bearer xxx 里取 Token
# auto_error=False 表示没传 Token 时不报错而是返回 None，方便做「可选登录」的逻辑
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """把用户的明文密码变成 bcrypt 哈希值，注册时调用"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验用户输入的密码和数据库里存的哈希值是否匹配，登录时调用"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    生成一个 JWT 访问令牌。
    参数 data 里一般会放 user_id、username 等信息，这些信息会被编码进 Token 里。
    前端拿到 Token 后存在 localStorage 里，之后每次请求 API 时带上它。
    Token 有过期时间，默认是配置文件里的 jwt_access_token_expire_minutes（24 小时）。
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})  # exp 是 JWT 规范里的过期时间字段
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码 JWT Token，拿到里面的载荷数据（包括 user_id 等）。
    如果 Token 无效或已过期，就返回 None。
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme)):
    """
    可选登录的依赖注入。
    有些接口登录和不登录都能访问，但登录用户可能看到更多内容，就用这个。
    - 没传 Token → 返回 None（代表匿名访客）
    - 传了 Token 但无效 → 也返回 None
    - 传了有效 Token → 返回解码后的用户信息
    """
    if token is None:
        return None
    payload = decode_access_token(token)
    if payload is None:
        return None
    return payload


async def get_current_user_required(token: Optional[str] = Depends(oauth2_scheme)):
    """
    强制登录的依赖注入。
    必须提供有效的 Token 才能继续，否则直接报 401 错误。
    大部分需要登录才能用的接口都依赖这个。
    """
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证凭据无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
