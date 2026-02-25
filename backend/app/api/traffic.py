"""
交通数据查询 API，提供路段信息和速度记录的查询接口。
挂在 /api/v1/traffic 路径下。
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user_optional, get_current_user_required
from backend.app.schemas.traffic import (
    SpeedRecordPage, RoadSectionInfo, OverviewStats, TrafficQuery
)
from backend.app.services.traffic_service import TrafficService

router = APIRouter()


@router.get("/overview", response_model=OverviewStats, summary="系统总览统计")
async def get_overview(db: Session = Depends(get_db)):
    """
    返回系统的概览统计数据：路段总数、记录总数、平均速度、最大最小速度等。
    前端 Dashboard 页面最上方的数字卡片就是调这个接口。
    这个接口不需要登录，任何人都能看。
    """
    svc = TrafficService(db)
    return svc.get_overview_stats()


@router.get("/roads", summary="路段信息列表")
async def get_roads(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """获取路段基础信息列表，支持分页，管理员页面用"""
    svc = TrafficService(db)
    total, items = svc.get_road_sections(page, page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": r.id,
                "roadsect_id": r.roadsect_id,
                "road_name": r.road_name,
                "district": r.district,
                "direction": r.direction,
                "length_m": r.length_m,
            }
            for r in items
        ],
    }


@router.get("/records", response_model=SpeedRecordPage, summary="速度记录查询")
async def get_records(
    start_date: Optional[str] = Query(None, description="起始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    roadsect_id: Optional[str] = Query(None, description="路段ID"),
    peak_type: Optional[str] = Query(None, description="高峰类型"),
    is_workday: Optional[bool] = Query(None, description="是否工作日"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """
    查询速度明细记录，支持按日期、路段、高峰类型、工作日等条件筛选。
    需要登录才能调用，因为明细数据量较大，不对匿名用户开放。
    """
    svc = TrafficService(db)
    total, items = svc.get_speed_records(
        start_date, end_date, roadsect_id, peak_type, is_workday, page, page_size
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "roadsect_id": r.roadsect_id,
                "record_date": r.record_date,
                "period": r.period,
                "go_time": r.go_time,
                "go_count": r.go_count,
                "go_len": r.go_len,
                "avg_speed": r.avg_speed,
                "is_peak": r.is_peak,
                "is_workday": r.is_workday,
                "peak_type": r.peak_type,
            }
            for r in items
        ],
    }
