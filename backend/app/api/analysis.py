"""
数据分析 API，给前端的各种图表提供聚合数据。
所有聚合都在后端用 SQL 的 GROUP BY 完成，前端只用拿结果画图就行。
这样做的好处是不用把十万级的明细数据传给前端，既省带宽又省前端计算资源。
挂在 /api/v1/analysis 路径下，大部分接口不需要登录。
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user_optional
from backend.app.schemas.traffic import (
    HourlySpeedPoint, DailySpeedPoint, PeakCompareItem, DistrictSpeedItem,
    RoadRankItem, SpeedDistributionItem, HeatmapCell,
    BoxplotItem, ScatterPoint,
)
from backend.app.services.traffic_service import TrafficService

router = APIRouter()


# 公共的日期查询参数提取，避免每个接口都写一遍
def _date_params(
    start_date: Optional[str] = Query(None, description="起始日期(YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期(YYYY-MM-DD)"),
):
    return start_date, end_date


@router.get("/hourly", response_model=List[HourlySpeedPoint], summary="24小时速度波动")
async def hourly_speed(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    roadsect_id: Optional[str] = Query(None, description="可选路段ID"),
    db: Session = Depends(get_db),
):
    """
    图表1: 返回每小时的平均速度、最大值、最小值和标准差。
    前端用这些数据画一天 24 小时的速度波动折线图。
    不需要登录。
    """
    svc = TrafficService(db)
    return svc.get_hourly_speed(start_date, end_date, roadsect_id)


@router.get("/daily", response_model=List[DailySpeedPoint], summary="每日速度趋势")
async def daily_speed(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    roadsect_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """图表: 每天的平均速度趋势，前端用来画时间线图"""
    svc = TrafficService(db)
    return svc.get_daily_speed(start_date, end_date, roadsect_id)


@router.get("/workday-weekend", summary="工作日/周末对比")
async def workday_weekend(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    图表2: 工作日和周末的 24 小时速度对比。
    返回两组数据（工作日 / 周末），前端画成两条线对比着看。
    """
    svc = TrafficService(db)
    return svc.get_workday_weekend_compare(start_date, end_date)


@router.get("/heatmap", response_model=List[HeatmapCell], summary="时间片热力图")
async def heatmap(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    图表3: 热力图数据，横轴是小时（0-23），纵轴是星期几（周一到周日），
    每个格子的值是平均速度，颜色深浅代表速度快慢。
    """
    svc = TrafficService(db)
    return svc.get_heatmap_data(start_date, end_date)


@router.get("/peak-compare", response_model=List[PeakCompareItem], summary="早晚高峰对比")
async def peak_compare(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    图表4: 早高峰 / 晚高峰 / 平峰三种时段的速度对比。
    前端用柱状图展示，可以直观看出高峰期速度下降多少。
    """
    svc = TrafficService(db)
    return svc.get_peak_compare(start_date, end_date)


@router.get("/district", response_model=List[DistrictSpeedItem], summary="区域平均速度")
async def district_speed(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    图表5: 每个路段的平均速度柱状图，显示速度最差的 30 个路段。
    """
    svc = TrafficService(db)
    return svc.get_district_speed(start_date, end_date)


@router.get("/congestion-rank", response_model=List[RoadRankItem], summary="拥堵排名")
async def congestion_rank(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(20, ge=5, le=50),
    db: Session = Depends(get_db),
):
    """
    图表6: 拥堵路段排名，按平均速度从低到高排序，取前 N 名。
    速度越低表示越堵。
    """
    svc = TrafficService(db)
    return svc.get_congestion_ranking(start_date, end_date, limit)


@router.get("/distribution", response_model=List[SpeedDistributionItem], summary="速度分布")
async def speed_distribution(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    图表7: 速度分布直方图，每 10 km/h 一个区间，统计各区间的记录数。
    可以看出大部分路段的速度集中在什么范围。
    """
    svc = TrafficService(db)
    return svc.get_speed_distribution(start_date, end_date)


@router.get("/boxplot", response_model=List[BoxplotItem], summary="箱线图")
async def boxplot(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    图表8: 按高峰类型分组的箱线图，展示数据分布和离群点。
    箱线图能直观显示中位数、四分位数、极值和异常值。
    """
    svc = TrafficService(db)
    return svc.get_boxplot_by_peak(start_date, end_date)


@router.get("/scatter", response_model=List[ScatterPoint], summary="散点图-均值vs标准差")
async def scatter(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    图表9: 每个路段的平均速度 vs 速度标准差散点图。
    标准差大的路段说明速度波动大，交通状况不稳定。
    """
    svc = TrafficService(db)
    return svc.get_scatter_mean_std(start_date, end_date)


@router.get("/favorite-heatmap", summary="收藏热度排名")
async def favorite_heatmap(db: Session = Depends(get_db)):
    """
    图表10: 路段被用户收藏的次数排名，可以看出哪些路段最受关注。
    """
    svc = TrafficService(db)
    return svc.get_favorite_heatmap()


@router.get("/direction-compare", summary="路段早晚高峰速度差异对比")
async def direction_compare(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(20, ge=5, le=50),
    db: Session = Depends(get_db),
):
    """
    图表11: 同一路段的早高峰和晚高峰速度差异对比图。
    差异大的路段可能存在明显的方向性拥堵，
    比如早上进城方向堵而晚上出城方向堵。
    """
    svc = TrafficService(db)
    return svc.get_direction_compare(start_date, end_date, limit)
