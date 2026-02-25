"""
数据库表结构定义（ORM 模型）。
用 SQLAlchemy 的声明式映射，每个 class 对应数据库里的一张表。

一共 5 张表：
  - users: 用户表，存账号密码
  - road_sections: 路段基础信息表，存路段的静态属性（名称、区域、方向、长度）
  - road_speed_records: 路段速度记录表，核心数据表，存每个时间片的速度数据
  - user_favorites: 用户收藏路段表
  - user_suggestions: 用户建议表
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date,
    Text, Boolean, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship

from backend.app.core.database import Base


class User(Base):
    """
    用户表，支持注册/登录，通过 JWT Token 做身份认证。
    is_admin 字段区分普通用户和管理员，管理员可以触发数据采集之类的操作。
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username = Column(String(64), unique=True, nullable=False, index=True, comment="用户名")
    hashed_password = Column(String(256), nullable=False, comment="bcrypt哈希密码")
    nickname = Column(String(64), default="", comment="昵称")
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_admin = Column(Boolean, default=False, comment="是否管理员")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关联关系：一个用户可以有多个收藏和多条建议，cascade 表示删用户时连带删除
    favorites = relationship("UserFavorite", back_populates="user", cascade="all, delete-orphan")
    suggestions = relationship("UserSuggestion", back_populates="user", cascade="all, delete-orphan")


class RoadSection(Base):
    """
    路段基础信息表，存储路段的静态属性。
    这张表的数据主要是在数据采集时自动创建的，每遇到一个新的 roadsect_id 就会插一条。
    """
    __tablename__ = "road_sections"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="自增主键")
    roadsect_id = Column(String(64), unique=True, nullable=False, index=True, comment="路段ID（来源数据）")
    road_name = Column(String(128), default="", comment="路段名称")
    district = Column(String(64), default="", comment="所属区域")
    direction = Column(String(32), default="", comment="方向（如：东向西）")
    length_m = Column(Float, default=0.0, comment="路段长度(米)")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关联关系：一个路段有多条速度记录
    speed_records = relationship("RoadSpeedRecord", back_populates="road_section", cascade="all, delete-orphan")


class RoadSpeedRecord(Base):
    """
    路段速度记录表，整个系统最核心的数据表。
    每条记录表示某个路段在某天某个时间片（5分钟）的交通速度数据。
    建了多个索引来加速查询，否则十万级数据量下查询会很慢。
    """
    __tablename__ = "road_speed_records"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="自增主键")
    roadsect_id = Column(String(64), ForeignKey("road_sections.roadsect_id"), nullable=False, comment="路段ID")
    record_date = Column(Date, nullable=False, comment="记录日期")
    period = Column(String(16), nullable=False, comment="时间片（如 08:00-08:15）")
    go_time = Column(Float, default=0.0, comment="总行驶时间(秒)")
    go_count = Column(Integer, default=0, comment="车辆数")
    go_len = Column(Float, default=0.0, comment="总行驶距离(米)")
    avg_speed = Column(Float, default=0.0, comment="平均速度(km/h)")
    is_peak = Column(Boolean, default=False, comment="是否高峰时段")
    is_workday = Column(Boolean, default=True, comment="是否工作日")
    peak_type = Column(String(16), default="平峰", comment="高峰类型：早高峰/晚高峰/平峰")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    # 关联关系：可以通过 record.road_section 拿到对应的路段信息
    road_section = relationship("RoadSection", back_populates="speed_records")

    __table_args__ = (
        # 复合索引：查询“某路段在某日某时段的数据”时走这个索引，速度最快
        Index("idx_road_date_period", "roadsect_id", "record_date", "period"),
        # 日期索引：按日期范围筛选时用
        Index("idx_record_date", "record_date"),
        # 高峰类型索引：按早高峰/晚高峰/平峰筛选时用
        Index("idx_peak_type", "peak_type"),
        # 唯一约束：同一路段+同一天+同一时段不能有重复数据
        UniqueConstraint("roadsect_id", "record_date", "period", name="uq_road_date_period"),
    )


class UserFavorite(Base):
    """
    用户收藏路段表。
    用户可以收藏感兴趣的路段，方便后续关注该路段的数据变化。
    user_id + roadsect_id 联合唯一，保证同一用户不会重复收藏同一路段。
    """
    __tablename__ = "user_favorites"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="自增主键")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    roadsect_id = Column(String(64), nullable=False, comment="收藏的路段ID")
    created_at = Column(DateTime, default=datetime.now, comment="收藏时间")

    # 关联
    user = relationship("User", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "roadsect_id", name="uq_user_road_fav"),  # 同一用户不能重复收藏
        Index("idx_fav_user", "user_id"),  # 按用户查收藏时登这个索引
    )


class UserSuggestion(Base):
    """
    用户建议表。
    用户可以提交对交通状况的建议，可以关联到具体的路段（也可以不关联）。
    """
    __tablename__ = "user_suggestions"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="自增主键")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    roadsect_id = Column(String(64), default="", comment="相关路段ID（可选）")
    title = Column(String(128), nullable=False, comment="建议标题")
    content = Column(Text, nullable=False, comment="建议内容")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    # 关联
    user = relationship("User", back_populates="suggestions")

    __table_args__ = (
        Index("idx_suggestion_user", "user_id"),  # 按用户查建议时走索引
    )
