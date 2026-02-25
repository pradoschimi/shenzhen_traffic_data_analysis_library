"""
交通数据相关的请求/响应数据模型（Pydantic Schema）。
这些模型用来做两件事：
  1. 请求参数校验：前端传过来的数据是否合法（比如页码不能小于 1）
  2. 响应格式定义：后端返回给前端的数据的字段和类型
"""
from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ==================== 查询请求参数 ====================

class TrafficQuery(BaseModel):
    """交通数据通用查询参数，所有字段都是可选的，不传就不筛选"""
    start_date: Optional[str] = Field(default=None, description="起始日期(YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="结束日期(YYYY-MM-DD)")
    roadsect_id: Optional[str] = Field(default=None, description="路段ID（精确匹配）")
    peak_type: Optional[str] = Field(default=None, description="高峰类型: 早高峰/晚高峰/平峰")
    is_workday: Optional[bool] = Field(default=None, description="是否工作日")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=50, ge=1, le=500, description="每页条数")

class DateRangeQuery(BaseModel):
    """日期范围查询，起始和结束日期都必填"""
    start_date: str = Field(..., description="起始日期(YYYY-MM-DD)")
    end_date: str = Field(..., description="结束日期(YYYY-MM-DD)")


# ==================== 路段基础信息响应 ====================

class RoadSectionInfo(BaseModel):
    """路段基础信息，对应 road_sections 表的字段"""
    id: int
    roadsect_id: str
    road_name: str
    district: str
    direction: str
    length_m: float

    class Config:
        from_attributes = True


# ==================== 速度记录相关 ====================

class SpeedRecordItem(BaseModel):
    """单条速度记录，对应 road_speed_records 表的一行数据"""
    roadsect_id: str
    record_date: date
    period: str
    go_time: float
    go_count: int
    go_len: float
    avg_speed: float
    is_peak: bool
    is_workday: bool
    peak_type: str

    class Config:
        from_attributes = True

class SpeedRecordPage(BaseModel):
    """分页查询的响应结构，包括总条数、当前页码和实际数据列表"""
    total: int = Field(..., description="总条数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
    items: List[SpeedRecordItem] = Field(default_factory=list, description="数据列表")


# ==================== 图表聚合分析用的响应模型 ====================
# 下面这些都是给前端图表接口返回数据用的结构定义

class HourlySpeedPoint(BaseModel):
    """按小时聚合的速度数据点，用于 24 小时速度波动图"""
    hour: int = Field(..., description="小时(0-23)")
    avg_speed: float = Field(..., description="平均速度(km/h)")
    min_speed: float = Field(default=0, description="最小速度")
    max_speed: float = Field(default=0, description="最大速度")
    std_speed: float = Field(default=0, description="速度标准差")
    record_count: int = Field(default=0, description="记录数")

class DailySpeedPoint(BaseModel):
    """按日聚合的速度数据点，用于每日趋势图"""
    date: str = Field(..., description="日期")
    avg_speed: float = Field(..., description="平均速度(km/h)")
    min_speed: float = Field(default=0, description="最小速度")
    max_speed: float = Field(default=0, description="最大速度")
    record_count: int = Field(default=0, description="记录数")

class PeakCompareItem(BaseModel):
    """早高峰/晚高峰/平峰对比数据"""
    peak_type: str = Field(..., description="高峰类型")
    avg_speed: float = Field(..., description="平均速度")
    std_speed: float = Field(default=0, description="标准差")
    record_count: int = Field(default=0, description="记录数")

class DistrictSpeedItem(BaseModel):
    """路段平均速度统计，用于柱状图"""
    district: str = Field(default="未知", description="区域")
    avg_speed: float = Field(..., description="平均速度")
    record_count: int = Field(default=0, description="记录数")

class RoadRankItem(BaseModel):
    """拥堵排名的单条数据，按平均速度升序（速度最低的最堵）"""
    roadsect_id: str = Field(..., description="路段ID")
    road_name: str = Field(default="", description="路段名称")
    avg_speed: float = Field(..., description="平均速度")
    record_count: int = Field(default=0, description="记录数")

class SpeedDistributionItem(BaseModel):
    """速度分布直方图的一个区间，比如 0-10 km/h 有多少条记录"""
    bin_label: str = Field(..., description="区间标签")
    count: int = Field(..., description="记录数")

class HeatmapCell(BaseModel):
    """热力图的一个单元格，横轴是小时，纵轴是星期几"""
    day: int = Field(..., description="星期(0=周一)")
    hour: int = Field(..., description="小时(0-23)")
    avg_speed: float = Field(..., description="平均速度")

class BoxplotItem(BaseModel):
    """箱线图数据，包含最小值/Q1/中位数/Q3/最大值，以及超出正常范围的离群点"""
    label: str = Field(..., description="分类标签")
    min_val: float = Field(..., description="最小值")
    q1: float = Field(..., description="下四分位数")
    median: float = Field(..., description="中位数")
    q3: float = Field(..., description="上四分位数")
    max_val: float = Field(..., description="最大值")
    outliers: List[float] = Field(default_factory=list, description="离群点")

class ScatterPoint(BaseModel):
    """散点图数据点，每个点代表一个路段，x轴是均值，y轴是标准差"""
    roadsect_id: str
    avg_speed: float = Field(..., description="均值")
    std_speed: float = Field(..., description="标准差")
    cv: float = Field(default=0, description="变异系数(%)")

class OverviewStats(BaseModel):
    """系统总览统计指标，Dashboard 页面最上方的数字卡片就是这些数据"""
    total_roads: int = Field(default=0, description="路段总数")
    total_records: int = Field(default=0, description="记录总数")
    global_avg_speed: float = Field(default=0, description="全局平均速度(km/h)")
    global_max_speed: float = Field(default=0, description="全局最高速度")
    global_min_speed: float = Field(default=0, description="全局最低速度")
    latest_date: Optional[str] = Field(default=None, description="最新数据日期")


# ==================== 数据采集任务相关 ====================

class FetchTaskRequest(BaseModel):
    """
    数据采集任务请求参数。
    深圳开放平台的数据集是静态的（约 1017 万条），不支持按日期筛选，只能通过分页来采集。
    支持断点续采：记住上次采到第几页，下次从那里继续。
    """
    start_page: int = Field(default=1, ge=1, description="起始页码(支持断点续采)")
    max_pages: int = Field(default=100, ge=1, le=20000, description="最大采集页数")
    rows_per_page: int = Field(default=1000, ge=10, le=10000, description="每页条数")

class FetchTaskResponse(BaseModel):
    """数据采集任务的响应，告诉前端任务已提交、预计采集多少条等信息"""
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="详情信息")
    total_api: int = Field(default=0, description="API数据集总量")
    estimated_records: int = Field(default=0, description="本次预估采集条数")
