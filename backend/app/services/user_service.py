"""
用户相关的业务逻辑层。
把具体的业务逻辑（注册、登录、收藏、建议）从 API 路由层抽出来放在这里，
保持 API 层只做参数接收和返回，业务逻辑不会散落在各处。
"""
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.models import User, UserFavorite, UserSuggestion
from backend.app.core.security import hash_password, verify_password, create_access_token
from backend.app.core.logger import logger


class UserService:
    """用户业务服务，每次请求创建一个实例，传入当前请求的数据库会话"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 注册登录 ====================

    def register(self, username: str, password: str, nickname: str = "") -> User:
        """
        用户注册。
        先检查用户名是否已存在，存在就报错；
        不存在就创建新用户，密码存的是 bcrypt 哈希值。
        """
        existing = self.db.query(User).filter(User.username == username).first()
        if existing:
            raise ValueError("用户名已存在")

        user = User(
            username=username,
            hashed_password=hash_password(password),
            nickname=nickname or username,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        logger.info(f"新用户注册: {username} (ID={user.id})")
        return user

    def login(self, username: str, password: str) -> Optional[dict]:
        """
        用户登录。
        验证用户名密码，成功后生成 JWT Token 并返回。
        失败的情况：用户不存在、密码错误、账号被禁用，都返回 None。
        """
        user = self.db.query(User).filter(User.username == username).first()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None

        # 生成 JWT Token，sub 字段放用户 ID，后续解码时用它来识别是谁
        token = create_access_token(data={
            "sub": str(user.id),
            "username": user.username,
            "is_admin": user.is_admin,
        })
        logger.info(f"用户登录: {username} (ID={user.id})")
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "is_admin": user.is_admin,
        }

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据 ID 查找用户，找不到返回 None"""
        return self.db.query(User).filter(User.id == user_id).first()

    # ==================== 收藏功能 ====================

    def add_favorite(self, user_id: int, roadsect_id: str) -> UserFavorite:
        """添加路段收藏，如果已经收藏过就报错"""
        existing = self.db.query(UserFavorite).filter(
            UserFavorite.user_id == user_id,
            UserFavorite.roadsect_id == roadsect_id,
        ).first()
        if existing:
            raise ValueError("已经收藏过该路段")

        fav = UserFavorite(user_id=user_id, roadsect_id=roadsect_id)
        self.db.add(fav)
        self.db.commit()
        self.db.refresh(fav)
        return fav

    def remove_favorite(self, user_id: int, roadsect_id: str) -> bool:
        """取消收藏，成功返回 True，找不到对应收藏返回 False"""
        fav = self.db.query(UserFavorite).filter(
            UserFavorite.user_id == user_id,
            UserFavorite.roadsect_id == roadsect_id,
        ).first()
        if not fav:
            return False
        self.db.delete(fav)
        self.db.commit()
        return True

    def get_favorites(self, user_id: int) -> List[UserFavorite]:
        """获取用户的所有收藏，按收藏时间倒序排列"""
        return (
            self.db.query(UserFavorite)
            .filter(UserFavorite.user_id == user_id)
            .order_by(UserFavorite.created_at.desc())
            .all()
        )

    # ==================== 建议功能 ====================

    def create_suggestion(
        self, user_id: int, title: str, content: str, roadsect_id: str = ""
    ) -> UserSuggestion:
        """创建一条用户建议并入库"""
        suggestion = UserSuggestion(
            user_id=user_id,
            title=title,
            content=content,
            roadsect_id=roadsect_id,
        )
        self.db.add(suggestion)
        self.db.commit()
        self.db.refresh(suggestion)
        logger.info(f"新建议: 用户{user_id} - {title}")
        return suggestion

    def get_suggestions(
        self, user_id: Optional[int] = None, page: int = 1, page_size: int = 20
    ) -> Tuple[int, List[UserSuggestion]]:
        """获取建议列表，可以按用户筛选，支持分页"""
        query = self.db.query(UserSuggestion)
        if user_id:
            query = query.filter(UserSuggestion.user_id == user_id)
        total = query.count()
        items = (
            query.order_by(UserSuggestion.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return total, items
