"""
用户相关的请求/响应数据模型。
注册、登录、用户信息、收藏、建议等接口的输入输出格式都定义在这里。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ==================== 登录注册相关 ====================

class UserRegister(BaseModel):
    """注册接口的请求体，用户名和密码必填，昵称可选"""
    username: str = Field(..., min_length=3, max_length=64, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    nickname: Optional[str] = Field(default="", max_length=64, description="昵称")

class UserLogin(BaseModel):
    """登录接口的请求体"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

class TokenResponse(BaseModel):
    """登录/注册成功后返回的数据，前端会把 token 存起来用于后续请求的身份认证"""
    access_token: str = Field(..., description="JWT 令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    user_id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    nickname: str = Field(default="", description="昵称")
    is_admin: bool = Field(default=False, description="是否管理员")

class UserInfo(BaseModel):
    """用户信息响应，/auth/me 接口用来返回当前登录用户的详细信息"""
    id: int
    username: str
    nickname: str
    is_active: bool
    is_admin: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 收藏功能相关 ====================

class FavoriteCreate(BaseModel):
    """添加收藏请求，只需要传一个路段 ID"""
    roadsect_id: str = Field(..., description="路段ID")

class FavoriteResponse(BaseModel):
    """收藏列表里每一项的数据结构"""
    id: int
    roadsect_id: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 建议功能相关 ====================

class SuggestionCreate(BaseModel):
    """提交建议的请求体，标题和内容必填，路段 ID 可选"""
    roadsect_id: Optional[str] = Field(default="", description="相关路段ID")
    title: str = Field(..., min_length=1, max_length=128, description="建议标题")
    content: str = Field(..., min_length=1, description="建议内容")

class SuggestionResponse(BaseModel):
    """建议列表里每一项的数据结构"""
    id: int
    user_id: int
    roadsect_id: str
    title: str
    content: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
