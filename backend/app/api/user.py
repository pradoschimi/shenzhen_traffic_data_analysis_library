"""
用户功能 API，包括路段收藏、提交建议、触发数据采集等接口。
挂在 /api/v1/user 路径下，所有接口都需要登录。
"""
import os
import sys
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user_required
from backend.app.core.logger import logger
from backend.app.schemas.user import FavoriteCreate, FavoriteResponse, SuggestionCreate, SuggestionResponse
from backend.app.schemas.traffic import FetchTaskRequest, FetchTaskResponse
from backend.app.services.user_service import UserService

router = APIRouter()


# ==================== 收藏管理：用户可以收藏感兴趣的路段 ====================

@router.get("/favorites", summary="获取我的收藏")
async def get_favorites(
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """返回当前用户收藏的所有路段列表"""
    svc = UserService(db)
    items = svc.get_favorites(int(current_user["sub"]))
    return [
        {"id": f.id, "roadsect_id": f.roadsect_id, "created_at": f.created_at}
        for f in items
    ]


@router.post("/favorites", summary="添加收藏")
async def add_favorite(
    body: FavoriteCreate,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """添加一个路段到收藏，如果已经收藏过会报错提示"""
    svc = UserService(db)
    try:
        fav = svc.add_favorite(int(current_user["sub"]), body.roadsect_id)
        return {"id": fav.id, "roadsect_id": fav.roadsect_id, "message": "收藏成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/favorites/{roadsect_id}", summary="取消收藏")
async def remove_favorite(
    roadsect_id: str,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """取消某个路段的收藏"""
    svc = UserService(db)
    success = svc.remove_favorite(int(current_user["sub"]), roadsect_id)
    if not success:
        raise HTTPException(status_code=404, detail="未找到该收藏")
    return {"message": "已取消收藏"}


# ==================== 建议管理：用户可以提交对交通状况的建议 ====================

@router.get("/suggestions", summary="获取建议列表")
async def get_suggestions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """获取当前用户提交过的建议列表，支持分页"""
    svc = UserService(db)
    total, items = svc.get_suggestions(
        user_id=int(current_user["sub"]), page=page, page_size=page_size
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": s.id,
                "roadsect_id": s.roadsect_id,
                "title": s.title,
                "content": s.content,
                "created_at": s.created_at,
            }
            for s in items
        ],
    }


@router.post("/suggestions", summary="提交建议")
async def create_suggestion(
    body: SuggestionCreate,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """提交一条新的交通建议，可以关联到具体的路段"""
    svc = UserService(db)
    s = svc.create_suggestion(
        user_id=int(current_user["sub"]),
        title=body.title,
        content=body.content,
        roadsect_id=body.roadsect_id or "",
    )
    return {"id": s.id, "title": s.title, "message": "建议提交成功"}


# ==================== 数据采集（仅管理员可用） ====================

def _run_fetch_task(start_page: int, max_pages: int, rows_per_page: int):
    """
    后台执行数据采集任务。
    用 FastAPI 的 BackgroundTasks 在后台跑，不会阻塞前端的请求。
    """
    try:
        ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        if ROOT_DIR not in sys.path:
            sys.path.insert(0, ROOT_DIR)
        from backend.scripts.fetch_data import fetch_and_import

        logger.info(f"[后台任务] 开始采集: 起始页={start_page}, 最大页数={max_pages}, 每页={rows_per_page}条")
        result = fetch_and_import(start_page, max_pages, rows_per_page)
        logger.info(f"[后台任务] 采集完成: {result}")
    except Exception as e:
        logger.error(f"[后台任务] 采集失败: {e}")


@router.post("/fetch", response_model=FetchTaskResponse, summary="触发数据采集")
async def trigger_fetch(
    body: FetchTaskRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """
    触发后台数据采集任务，仅管理员可操作。
    深圳开放平台的数据集有4e1017万条，通过分页方式采集并存入数据库。
    支持断点续采：设置 start_page 为上次中断的页码即可。
    任务在后台异步执行，接口会立刻返回“已提交”的状态。
    """
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="仅管理员可执行数据采集")

    estimated = body.max_pages * body.rows_per_page
    background_tasks.add_task(
        _run_fetch_task, body.start_page, body.max_pages, body.rows_per_page
    )
    return {
        "status": "accepted",
        "message": f"数据采集任务已提交: 从第{body.start_page}页开始, 采集{body.max_pages}页(约{estimated}条)",
        "total_api": 10174000,
        "estimated_records": estimated,
    }
