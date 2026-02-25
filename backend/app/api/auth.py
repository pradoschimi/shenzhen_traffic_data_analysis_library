"""
认证相关的 API 路由，包括用户注册、登录、获取当前用户信息。
这里的接口都挂在 /api/v1/auth 路径下。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user_required
from backend.app.schemas.user import UserRegister, UserLogin, TokenResponse, UserInfo
from backend.app.services.user_service import UserService

router = APIRouter()


@router.post("/register", response_model=TokenResponse, summary="用户注册")
async def register(body: UserRegister, db: Session = Depends(get_db)):
    """
    注册新用户。注册成功后会自动登录，直接返回 Token，
    这样前端注册完不用再跳到登录页，体验更好。
    """
    svc = UserService(db)
    try:
        user = svc.register(body.username, body.password, body.nickname)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 注册成功后自动登录，省得用户再手动登录一遍
    result = svc.login(body.username, body.password)
    if not result:
        raise HTTPException(status_code=500, detail="注册成功但自动登录失败")
    return result


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(body: UserLogin, db: Session = Depends(get_db)):
    """
    用户名 + 密码登录，成功后返回 JWT Token 和用户基本信息。
    前端收到后把 Token 存到 localStorage 里，之后请求接口时带上它。
    """
    svc = UserService(db)
    result = svc.login(body.username, body.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    return result


@router.get("/me", response_model=UserInfo, summary="获取当前用户信息")
async def get_me(
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """
    根据 Token 获取当前登录用户的详细信息。
    前端一般在页面初始化时调用这个接口，确认 Token 是否还有效。
    """
    svc = UserService(db)
    user = svc.get_user_by_id(int(current_user["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user
