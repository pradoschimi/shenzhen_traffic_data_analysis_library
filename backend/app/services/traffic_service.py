"""
交通数据的查询和分析服务层。

重要设计决策：
  1. 所有聚合分析都在 SQL 层用 GROUP BY 完成，不把明细数据拉到 Python 内存里算，
     这样即使数据量很大也不会内存爆掉。
  2. 查询结果通过 Redis 缓存 10 分钟，Redis 不可用时自动回退到内存缓存。
     因为我们的数据是历史数据（不会变），同样的查询每次结果都一样，缓存很合适。
"""
import hashlib
import time as _time
from datetime import date, datetime, timedelta
from typing import Optional, List, Tuple, Any

from sqlalchemy import func, text, case, and_, desc, asc, cast, Integer
from sqlalchemy.orm import Session

from backend.app.models.models import RoadSection, RoadSpeedRecord, UserFavorite
from backend.app.core.logger import logger
from backend.app.core.redis import cache_get, cache_set, make_cache_key, CACHE_TTL


def _cached(fn):
    """
    缓存装饰器，用在服务方法上。
    第一次调用时查数据库并把结果存进缓存，
    之后相同参数再调用就直接从缓存里拿，不用再查数据库了。
    """
    def wrapper(self, *args, **kwargs):
        key = make_cache_key(fn.__name__, args, kwargs)
        hit = cache_get(key)
        if hit is not None:
            return hit
        result = fn(self, *args, **kwargs)
        cache_set(key, result, CACHE_TTL)
        return result
    wrapper.__name__ = fn.__name__
    return wrapper


class TrafficService:
    """交通数据查询与分析服务，每次请求创建一个实例"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 基础查询：总览 + 分页列表 ====================

    def get_overview_stats(self) -> dict:
        """获取系统总览数据：路段总数、记录总数、全局平均速度、最新数据日期等"""
        total_roads = self.db.query(func.count(RoadSection.id)).scalar() or 0
        total_records = self.db.query(func.count(RoadSpeedRecord.id)).scalar() or 0

        speed_stats = self.db.query(
            func.avg(RoadSpeedRecord.avg_speed),
            func.max(RoadSpeedRecord.avg_speed),
            func.min(RoadSpeedRecord.avg_speed),
        ).first()

        latest_date = self.db.query(
            func.max(RoadSpeedRecord.record_date)
        ).scalar()

        return {
            "total_roads": total_roads,
            "total_records": total_records,
            "global_avg_speed": round(float(speed_stats[0] or 0), 2),
            "global_max_speed": round(float(speed_stats[1] or 0), 2),
            "global_min_speed": round(float(speed_stats[2] or 0), 2),
            "latest_date": str(latest_date) if latest_date else None,
        }

    def get_road_sections(self, page: int = 1, page_size: int = 50) -> Tuple[int, list]:
        """获取路段信息列表，支持分页，按路段 ID 排序"""
        total = self.db.query(func.count(RoadSection.id)).scalar() or 0
        items = (
            self.db.query(RoadSection)
            .order_by(RoadSection.roadsect_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return total, items

    def get_speed_records(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        roadsect_id: Optional[str] = None,
        peak_type: Optional[str] = None,
        is_workday: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[int, list]:
        """
        查询速度明细记录，支持按日期、路段、高峰类型、工作日等多条件筛选，
        结果分页返回。
        """
        query = self.db.query(RoadSpeedRecord)
        if start_date:
            query = query.filter(RoadSpeedRecord.record_date >= start_date)
        if end_date:
            query = query.filter(RoadSpeedRecord.record_date <= end_date)
        if roadsect_id:
            query = query.filter(RoadSpeedRecord.roadsect_id == roadsect_id)
        if peak_type:
            query = query.filter(RoadSpeedRecord.peak_type == peak_type)
        if is_workday is not None:
            query = query.filter(RoadSpeedRecord.is_workday == is_workday)

        total = query.count()
        items = (
            query.order_by(RoadSpeedRecord.record_date.desc(), RoadSpeedRecord.period)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return total, items

    # ==================== SQL 聚合分析：给前端图表提供数据 ====================

    # period 字段格式是 "HH:MM"，取前两位转成整数就是小时数
    _hour_expr = cast(func.left(RoadSpeedRecord.period, 2), Integer)

    def _default_dates(self, start_date, end_date):
        """
        如果前端没传日期参数，默认只查最新一天的数据。
        这样做是为了避免全表扫描——十万级数据不加条件查会很慢。
        """
        if not start_date and not end_date:
            latest = self.db.query(func.max(RoadSpeedRecord.record_date)).scalar()
            if latest:
                return str(latest), str(latest)
            return None, None
        return start_date, end_date

    def _apply_filters(self, query, start_date, end_date, roadsect_id=None):
        """给查询加上日期和路段 ID 的过滤条件，多个图表接口都要用这个，抽出来避免重复代码"""
        start_date, end_date = self._default_dates(start_date, end_date)
        if start_date:
            query = query.filter(RoadSpeedRecord.record_date >= start_date)
        if end_date:
            query = query.filter(RoadSpeedRecord.record_date <= end_date)
        if roadsect_id:
            query = query.filter(RoadSpeedRecord.roadsect_id == roadsect_id)
        return query

    @_cached
    def get_hourly_speed(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        roadsect_id: Optional[str] = None,
    ) -> List[dict]:
        """图表1: 24小时速度波动，每小时返回均值/最值/标准差/记录数"""
        hour = self._hour_expr.label("hour")
        query = self.db.query(
            hour,
            func.avg(RoadSpeedRecord.avg_speed).label("avg_speed"),
            func.min(RoadSpeedRecord.avg_speed).label("min_speed"),
            func.max(RoadSpeedRecord.avg_speed).label("max_speed"),
            func.stddev_pop(RoadSpeedRecord.avg_speed).label("std_speed"),
            func.count(RoadSpeedRecord.id).label("cnt"),
        )
        query = self._apply_filters(query, start_date, end_date, roadsect_id)
        rows = query.group_by("hour").order_by("hour").all()
        return [
            {"hour": int(r.hour), "avg_speed": round(float(r.avg_speed or 0), 2),
             "min_speed": round(float(r.min_speed or 0), 2),
             "max_speed": round(float(r.max_speed or 0), 2),
             "std_speed": round(float(r.std_speed or 0), 2),
             "record_count": int(r.cnt)}
            for r in rows
        ]

    @_cached
    def get_daily_speed(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        roadsect_id: Optional[str] = None,
    ) -> List[dict]:
        """每日平均速度趋势，按日期分组统计"""
        query = self.db.query(
            RoadSpeedRecord.record_date.label("dt"),
            func.avg(RoadSpeedRecord.avg_speed).label("avg_speed"),
            func.min(RoadSpeedRecord.avg_speed).label("min_speed"),
            func.max(RoadSpeedRecord.avg_speed).label("max_speed"),
            func.count(RoadSpeedRecord.id).label("cnt"),
        )
        query = self._apply_filters(query, start_date, end_date, roadsect_id)
        rows = query.group_by("dt").order_by("dt").all()
        return [
            {"date": str(r.dt), "avg_speed": round(float(r.avg_speed or 0), 2),
             "min_speed": round(float(r.min_speed or 0), 2),
             "max_speed": round(float(r.max_speed or 0), 2),
             "record_count": int(r.cnt)}
            for r in rows
        ]

    @_cached
    def get_workday_weekend_compare(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[dict]:
        """图表2: 工作日 vs 周末的 24 小时速度对比，按 is_workday 和 hour 分组"""
        hour = self._hour_expr.label("hour")
        query = self.db.query(
            RoadSpeedRecord.is_workday,
            hour,
            func.avg(RoadSpeedRecord.avg_speed).label("avg_speed"),
        )
        query = self._apply_filters(query, start_date, end_date)
        rows = query.group_by(RoadSpeedRecord.is_workday, "hour").order_by(
            RoadSpeedRecord.is_workday.desc(), "hour"
        ).all()
        groups: dict = {}
        for r in rows:
            label = "工作日" if r.is_workday else "周末"
            groups.setdefault(label, []).append(
                {"hour": int(r.hour), "avg_speed": round(float(r.avg_speed or 0), 2)}
            )
        return [{"label": k, "data": v} for k, v in groups.items()]

    @_cached
    def get_heatmap_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[dict]:
        """图表3: 星期 x 小时的热力图数据，用 MySQL 的 dayofweek 函数取星期几"""
        hour = self._hour_expr.label("hour")
        dow = ((func.dayofweek(RoadSpeedRecord.record_date) + 5) % 7).label("dow")
        query = self.db.query(
            dow, hour,
            func.avg(RoadSpeedRecord.avg_speed).label("avg_speed"),
        )
        query = self._apply_filters(query, start_date, end_date)
        rows = query.group_by("dow", "hour").all()
        return [
            {"day": int(r.dow), "hour": int(r.hour),
             "avg_speed": round(float(r.avg_speed or 0), 2)}
            for r in rows
        ]

    @_cached
    def get_peak_compare(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[dict]:
        """图表4: 早高峰/晚高峰/平峰三组对比，按 peak_type 分组统计"""
        query = self.db.query(
            RoadSpeedRecord.peak_type,
            func.avg(RoadSpeedRecord.avg_speed).label("avg_speed"),
            func.stddev_pop(RoadSpeedRecord.avg_speed).label("std_speed"),
            func.count(RoadSpeedRecord.id).label("cnt"),
        )
        query = self._apply_filters(query, start_date, end_date)
        rows = query.group_by(RoadSpeedRecord.peak_type).all()
        return [
            {"peak_type": r.peak_type or "平峰",
             "avg_speed": round(float(r.avg_speed or 0), 2),
             "std_speed": round(float(r.std_speed or 0), 2),
             "record_count": int(r.cnt)}
            for r in rows
        ]

    @_cached
    def get_district_speed(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[dict]:
        """图表: 每个路段的平均速度柱状图，取速度最低的 30 个"""
        sd, ed = self._default_dates(start_date, end_date)
        query = self.db.query(
            RoadSpeedRecord.roadsect_id,
            func.avg(RoadSpeedRecord.avg_speed).label("avg_speed"),
            func.count(RoadSpeedRecord.id).label("cnt"),
        )
        if sd:
            query = query.filter(RoadSpeedRecord.record_date >= sd)
        if ed:
            query = query.filter(RoadSpeedRecord.record_date <= ed)
        rows = (
            query.group_by(RoadSpeedRecord.roadsect_id)
            .order_by(func.avg(RoadSpeedRecord.avg_speed).asc())
            .limit(30)
            .all()
        )
        return [
            {"district": r[0], "avg_speed": round(float(r[1]), 2),
             "record_count": int(r[2])}
            for r in rows
        ]

    @_cached
    def get_congestion_ranking(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20,
    ) -> List[dict]:
        """图表6: 拥堵路段排名，平均速度最低的前 N 名"""
        sd, ed = self._default_dates(start_date, end_date)
        query = self.db.query(
            RoadSpeedRecord.roadsect_id,
            func.avg(RoadSpeedRecord.avg_speed).label("avg_speed"),
            func.count(RoadSpeedRecord.id).label("cnt"),
        )
        if sd:
            query = query.filter(RoadSpeedRecord.record_date >= sd)
        if ed:
            query = query.filter(RoadSpeedRecord.record_date <= ed)
        rows = query.group_by(RoadSpeedRecord.roadsect_id).order_by(asc("avg_speed")).limit(limit).all()

        # 批量查询路段名称，用于显示在前端图表上（光显示 ID 不直观）
        ids = [r[0] for r in rows]
        name_map = {}
        if ids:
            roads = self.db.query(RoadSection.roadsect_id, RoadSection.road_name).filter(
                RoadSection.roadsect_id.in_(ids)).all()
            name_map = {r[0]: r[1] for r in roads}
        return [
            {"roadsect_id": r[0], "road_name": name_map.get(r[0], ""),
             "avg_speed": round(float(r[1]), 2), "record_count": int(r[2])}
            for r in rows
        ]

    @_cached
    def get_speed_distribution(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[dict]:
        """图表7: 速度分布直方图，每 10 km/h 一个桶，统计各桶的记录数"""
        sd, ed = self._default_dates(start_date, end_date)
        bin_expr = case(
            *[(RoadSpeedRecord.avg_speed < (i + 1) * 10, f"{i * 10}-{(i + 1) * 10}") for i in range(12)],
            else_="110-120",
        ).label("speed_bin")
        query = self.db.query(bin_expr, func.count(RoadSpeedRecord.id).label("cnt"))
        if sd:
            query = query.filter(RoadSpeedRecord.record_date >= sd)
        if ed:
            query = query.filter(RoadSpeedRecord.record_date <= ed)
        rows = query.group_by("speed_bin").all()
        result_map = {r[0]: int(r[1]) for r in rows}
        bins = [f"{i * 10}-{i * 10 + 10}" for i in range(12)]
        return [{"bin_label": b, "count": result_map.get(b, 0)} for b in bins]

    @_cached
    def get_boxplot_by_peak(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[dict]:
        """
        图表8: 按高峰类型的箱线图。
        用 MySQL 的 NTILE(4) 窗口函数把数据分成 4 等份，然后取每份的最大值得到 Q1/中位数/Q3。
        还会用 IQR 规则检测离群点（小于 Q1-1.5*IQR 或大于 Q3+1.5*IQR 的值）。
        """
        sd, ed = self._default_dates(start_date, end_date)
        date_cond = ""
        params: dict = {}
        if sd:
            date_cond += " AND record_date >= :sd"
            params["sd"] = sd
        if ed:
            date_cond += " AND record_date <= :ed"
            params["ed"] = ed
        sql = text(f"""
            WITH ranked AS (
                SELECT peak_type, avg_speed,
                       NTILE(4) OVER (PARTITION BY peak_type ORDER BY avg_speed) AS q
                FROM road_speed_records WHERE 1=1 {date_cond}
            )
            SELECT peak_type,
                   MIN(avg_speed) AS min_v,
                   MAX(CASE WHEN q=1 THEN avg_speed END) AS q1,
                   MAX(CASE WHEN q=2 THEN avg_speed END) AS median,
                   MAX(CASE WHEN q=3 THEN avg_speed END) AS q3,
                   MAX(avg_speed) AS max_v
            FROM ranked GROUP BY peak_type
        """)
        rows = self.db.execute(sql, params).fetchall()
        result = []
        for r in rows:
            q1, q3 = float(r[2] or 0), float(r[4] or 0)
            iqr = q3 - q1
            lower_fence = q1 - 1.5 * iqr
            upper_fence = q3 + 1.5 * iqr

            # 查询离群点：速度超出 IQR 围栅范围的值
            outlier_sql = text(f"""
                SELECT DISTINCT ROUND(avg_speed, 2) AS v
                FROM road_speed_records
                WHERE peak_type = :pt {date_cond}
                  AND (avg_speed < :lower OR avg_speed > :upper)
                ORDER BY v
                LIMIT 50
            """)
            outlier_params = {**params, "pt": r[0], "lower": lower_fence, "upper": upper_fence}
            outlier_rows = self.db.execute(outlier_sql, outlier_params).fetchall()
            outliers = [float(o[0]) for o in outlier_rows]

            result.append({
                "label": r[0] or "平峰",
                "min_val": round(max(float(r[1] or 0), lower_fence), 2),
                "q1": round(q1, 2),
                "median": round(float(r[3] or 0), 2),
                "q3": round(q3, 2),
                "max_val": round(min(float(r[5] or 0), upper_fence), 2),
                "outliers": outliers,
            })
        return result

    @_cached
    def get_scatter_mean_std(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[dict]:
        """图表9: 每个路段的均值 vs 标准差散点图，还计算了变异系数 CV（标准差/均值）"""
        query = self.db.query(
            RoadSpeedRecord.roadsect_id,
            func.avg(RoadSpeedRecord.avg_speed).label("avg_speed"),
            func.stddev_pop(RoadSpeedRecord.avg_speed).label("std_speed"),
        )
        query = self._apply_filters(query, start_date, end_date)
        rows = query.group_by(RoadSpeedRecord.roadsect_id).all()
        return [
            {"roadsect_id": r[0],
             "avg_speed": round(float(r[1] or 0), 2),
             "std_speed": round(float(r[2] or 0), 2),
             "cv": round(float(r[2] or 0) / float(r[1]) * 100, 1) if float(r[1] or 0) > 0 else 0}
            for r in rows
        ]

    def get_favorite_heatmap(self) -> List[dict]:
        """图表10: 路段收藏热度排名，统计每个路段被收藏的次数"""
        rows = (
            self.db.query(
                UserFavorite.roadsect_id,
                func.count(UserFavorite.id).label("fav_count"),
            )
            .group_by(UserFavorite.roadsect_id)
            .order_by(desc("fav_count"))
            .limit(30)
            .all()
        )
        return [{"roadsect_id": row[0], "fav_count": int(row[1])} for row in rows]

    @_cached
    def get_direction_compare(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20,
    ) -> List[dict]:
        """
        图表: 路段早晚高峰速度差异对比。
        差值 = 早高峰均速 - 晚高峰均速，可以推断路段的方向性通勤特征。
        比如某路段早高峰均速明显低于晚高峰，说明早上进城方向更堵。
        """
        sd, ed = self._default_dates(start_date, end_date)
        date_cond = ""
        params: dict = {}
        if sd:
            date_cond += " AND record_date >= :sd"
            params["sd"] = sd
        if ed:
            date_cond += " AND record_date <= :ed"
            params["ed"] = ed
        sql = text(f"""
            SELECT roadsect_id,
                   ROUND(AVG(CASE WHEN peak_type='早高峰' THEN avg_speed END), 2) AS am_speed,
                   ROUND(AVG(CASE WHEN peak_type='晚高峰' THEN avg_speed END), 2) AS pm_speed,
                   ROUND(AVG(CASE WHEN peak_type='早高峰' THEN avg_speed END)
                       - AVG(CASE WHEN peak_type='晚高峰' THEN avg_speed END), 2) AS diff
            FROM road_speed_records
            WHERE peak_type IN ('早高峰', '晚高峰') {date_cond}
            GROUP BY roadsect_id
            HAVING am_speed IS NOT NULL AND pm_speed IS NOT NULL
            ORDER BY ABS(diff) DESC
            LIMIT :lim
        """)
        params["lim"] = limit
        rows = self.db.execute(sql, params).fetchall()
        return [
            {"roadsect_id": r[0],
             "am_speed": float(r[1] or 0),
             "pm_speed": float(r[2] or 0),
             "diff": float(r[3] or 0)}
            for r in rows
        ]
