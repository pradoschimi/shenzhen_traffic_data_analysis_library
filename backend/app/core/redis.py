"""
Redis 缓存管理模块。
用 Redis 缓存查询结果，避免每次都查数据库。
如果 Redis 没部署或者挂了也不影响系统运行，会自动降级到内存字典做缓存。
只是内存缓存重启就没了，不过这也没什么大不了的。
"""
import json
import hashlib
import time as _time
from typing import Any, Optional

import redis

from backend.app.core.config import settings
from backend.app.core.logger import logger

# ============ Redis 客户端单例 ============
_redis_client: Optional[redis.Redis] = None
_redis_available: bool = False

# 内存回退缓存，字典结构：{key: (缓存值, 写入时的时间戳)}
_MEM_CACHE: dict[str, tuple[Any, float]] = {}

CACHE_TTL = 600  # 缓存有效期 10 分钟
CACHE_KEY_PREFIX = "sz_traffic:"  # 给所有 key 加个前缀，避免和其他应用的 key 冲突


def get_redis() -> Optional[redis.Redis]:
    """
    获取 Redis 客户端，第一次调用时尝试连接。
    连上了就返回客户端对象，连不上就返回 None，后续调用会走内存缓存。
    """
    global _redis_client, _redis_available
    if _redis_client is not None:
        return _redis_client if _redis_available else None

    try:
        _redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password or None,
            db=settings.redis_db,
            decode_responses=True,       # 自动把 bytes 解码成字符串
            socket_connect_timeout=2,    # 连接超时 2 秒，不想因为 Redis 的问题拖慢启动
            socket_timeout=2,
        )
        _redis_client.ping()  # 试着 ping 一下，能通说明连接成功
        _redis_available = True
        logger.info(f"Redis 连接成功: {settings.redis_host}:{settings.redis_port}/{settings.redis_db}")
        return _redis_client
    except Exception as e:
        _redis_available = False
        logger.warning(f"Redis 连接失败，回退到内存缓存: {e}")
        return None


def cache_get(key: str) -> Optional[Any]:
    """
    从缓存里取数据。优先走 Redis，Redis 不可用时走内存字典。
    内存缓存会检查 TTL，过期了就返回 None。
    """
    full_key = CACHE_KEY_PREFIX + key
    r = get_redis()
    if r:
        try:
            val = r.get(full_key)
            if val is not None:
                return json.loads(val)
        except Exception:
            pass
        return None

    # Redis 不可用，走内存缓存
    hit = _MEM_CACHE.get(full_key)
    if hit and (_time.time() - hit[1]) < CACHE_TTL:
        return hit[0]
    return None


def cache_set(key: str, value: Any, ttl: int = CACHE_TTL) -> None:
    """
    往缓存里写数据。优先写 Redis，Redis 不可用时写内存字典。
    Redis 的 setex 命令可以同时设置值和过期时间。
    """
    full_key = CACHE_KEY_PREFIX + key
    r = get_redis()
    if r:
        try:
            r.setex(full_key, ttl, json.dumps(value, ensure_ascii=False, default=str))
            return
        except Exception:
            pass

    # Redis 不可用，写内存
    _MEM_CACHE[full_key] = (value, _time.time())


def cache_clear(pattern: str = "*") -> int:
    """
    清除缓存，返回清除的 key 数量。
    可以传通配符来清除特定前缀的缓存，默认清除全部。
    """
    full_pattern = CACHE_KEY_PREFIX + pattern
    r = get_redis()
    cleared = 0
    if r:
        try:
            keys = r.keys(full_pattern)
            if keys:
                cleared = r.delete(*keys)
            logger.info(f"Redis 缓存已清除 {cleared} 个 key")
            return cleared
        except Exception:
            pass

    # 内存回退：遍历字典找出匹配的 key 删掉
    to_del = [k for k in _MEM_CACHE if k.startswith(CACHE_KEY_PREFIX)]
    for k in to_del:
        del _MEM_CACHE[k]
    cleared = len(to_del)
    logger.info(f"内存缓存已清除 {cleared} 个 key")
    return cleared


def make_cache_key(fn_name: str, args: tuple, kwargs: dict) -> str:
    """
    把函数名 + 参数组合成一个 MD5 哈希值作为缓存 key。
    相同的函数和参数会得到相同的 key，这样就能实现“相同查询承缓存”的效果。
    """
    raw = f"{fn_name}|{args}|{sorted(kwargs.items())}"
    return hashlib.md5(raw.encode()).hexdigest()
