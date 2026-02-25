"""
数据采集与清洗脚本，从深圳开放数据平台拉取路段交通速度数据。

数据集背景：
  - 这是个静态数据集，一共约 1017 万条记录
  - 时间范围大概是 2018年4月 到 2019年6月
  - 原始字段说明：
    * ROADSECT_ID: 路段编号
    * TIME: 毫秒级时间戳
    * PERIOD: 5分钟时间片编号（1~288，一天 24*60/5=288 个片）
    * GOCOUNT: 车辆数
    * GOTIME: 总行驶时间（秒）
    * GOLEN: 总行驶距离（米）
  - PERIOD 和时刻的映射关系：PERIOD N 对应的起始时刻 = (N-1)*5 分钟
    举例：PERIOD 1 = 00:00, PERIOD 85 = 07:00, PERIOD 205 = 17:00
  - API 不支持按日期筛选，只能通过分页 (page + rows) 来采集
"""
import os
import sys
import time as _time
from datetime import datetime, timezone, timedelta

import httpx
import pandas as pd
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loguru import logger

# 把项目根目录加到 sys.path，这样才能 import backend.xxx
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app.core.config import settings

# 深圳开放数据平台的 API 地址
API_URL = "https://opendata.sz.gov.cn/api/29200_00403590/1/service.xhtml"

# 北京时间（UTC+8），用于把毫秒时间戳转成正确的日期
BJT = timezone(timedelta(hours=8))


# ==================== 网络请求层 ====================

@retry(
    stop=stop_after_attempt(3),                  # 最多重试 3 次
    wait=wait_exponential(multiplier=1, min=2, max=30),  # 指数退避，间隔 2s、4s、8s...
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    before_sleep=lambda retry_state: logger.warning(
        f"请求失败，第 {retry_state.attempt_number} 次重试..."
    ),
)
def fetch_page(page: int, rows: int = 1000) -> dict:
    """
    请求 API 的某一页数据，带自动重试机制（tenacity 库）。
    如果连续失败 3 次就不再重试了，会报错。
    """
    params = {
        "appKey": settings.sz_opendata_app_key,
        "page": page,
        "rows": rows,
    }
    with httpx.Client(timeout=60.0) as client:
        response = client.get(API_URL, params=params)
        response.raise_for_status()
        return response.json()


# ==================== 数据处理层：把 API 返回的原始数据清洗成可以入库的格式 ====================

def process_batch(data_list: list) -> pd.DataFrame:
    """
    处理一批从 API 拿到的原始数据，主要干这些事：
    1. 原始字段转数值类型（API 返回的都是字符串）
    2. TIME 毫秒时间戳 → 北京时间日期
    3. PERIOD 编号 → "HH:MM" 格式的时间字符串
    4. 计算平均速度: (总距离 / 总时间) * 3.6 转换成 km/h
    5. 标记工作日/周末、早高峰/晚高峰/平峰
    6. 剔除无效和异常数据（速度为负或超过 200 km/h）
    """
    if not data_list:
        return pd.DataFrame()

    df = pd.DataFrame(data_list)

    # --- 类型转换：API 返回的都是字符串，转成数值类型才能做计算 ---
    df["GOTIME"] = pd.to_numeric(df["GOTIME"], errors="coerce")
    df["GOLEN"] = pd.to_numeric(df["GOLEN"], errors="coerce")
    df["GOCOUNT"] = pd.to_numeric(df["GOCOUNT"], errors="coerce").fillna(0).astype(int)
    df["ROADSECT_ID"] = df["ROADSECT_ID"].astype(str)
    df["TIME"] = pd.to_numeric(df["TIME"], errors="coerce")
    df["PERIOD"] = pd.to_numeric(df["PERIOD"], errors="coerce").fillna(1).astype(int)

    # --- 把毫秒时间戳转成北京时间的日期（只取日期部分） ---
    df["record_date"] = pd.to_datetime(df["TIME"], unit="ms", utc=True).dt.tz_convert(BJT).dt.date

    # --- PERIOD 编号转成 "HH:MM" 格式 ---
    # 举例：PERIOD 85 -> (85-1)*5=420分钟=7小时0分 -> "07:00"
    total_minutes = (df["PERIOD"] - 1) * 5
    hours = total_minutes // 60
    minutes = total_minutes % 60
    df["period"] = hours.astype(str).str.zfill(2) + ":" + minutes.astype(str).str.zfill(2)
    df["hour"] = hours  # 保留小时数用于高峰判断

    # --- 计算平均速度 ---
    # 公式：速度(km/h) = (距离(m) / 时间(s)) * 3.6
    # GOTIME 为 0 的时候没法算速度，标记为 NaN
    df["avg_speed"] = np.where(
        df["GOTIME"] > 0,
        (df["GOLEN"] / df["GOTIME"]) * 3.6,
        np.nan,
    )

    # --- 数据清洗：去掉空值和不合理的记录 ---
    df = df.dropna(subset=["avg_speed", "record_date"])
    df = df[df["avg_speed"] >= 0].copy()
    # 城市道路上跑 200 km/h 以上肯定是数据异常，直接剔掉
    df = df[df["avg_speed"] <= 200].copy()

    if df.empty:
        return df

    # --- 判断工作日还是周末 ---
    record_dt = pd.to_datetime(df["record_date"])
    df["day_of_week"] = record_dt.dt.dayofweek  # 0=周一
    df["is_workday"] = df["day_of_week"] < 5

    # --- 判断高峰类型 ---
    # 早高峰 7:00-9:00，晚高峰 17:00-19:00，其余时段为平峰
    df["peak_type"] = "平峰"
    df["is_peak"] = False
    morning_peak = df["hour"].between(7, 8)
    evening_peak = df["hour"].between(17, 18)
    df.loc[morning_peak, "peak_type"] = "早高峰"
    df.loc[morning_peak, "is_peak"] = True
    df.loc[evening_peak, "peak_type"] = "晚高峰"
    df.loc[evening_peak, "is_peak"] = True

    return df


# ==================== 数据库写入层 ====================

def insert_batch_to_db(df: pd.DataFrame, db_session) -> int:
    """
    将处理好的数据批量写入数据库。
    这是比较保守的写法，逐条插入，遇到重复的就跳过。
    性能一般，但不会因为重复数据而崩掉。
    更快的版本参见下方的 insert_batch_to_db_fast。
    """
    if df.empty:
        return 0

    from backend.app.models.models import RoadSection, RoadSpeedRecord

    saved_count = 0

    # 1. 确保这批数据涉及的路段都已经在 road_sections 表里了
    #    如果有新路段就先插入，不然后面的外键约束会报错
    road_ids_in_batch = df["ROADSECT_ID"].unique().tolist()
    existing_roads = {
        r.roadsect_id
        for r in db_session.query(RoadSection.roadsect_id)
        .filter(RoadSection.roadsect_id.in_(road_ids_in_batch))
        .all()
    }
    new_roads = [
        RoadSection(roadsect_id=rid)
        for rid in road_ids_in_batch
        if rid not in existing_roads
    ]
    if new_roads:
        db_session.add_all(new_roads)
        db_session.flush()

    # 2. 把 DataFrame 里的每一行转成 ORM 对象
    records = []
    for _, row in df.iterrows():
        records.append(RoadSpeedRecord(
            roadsect_id=row["ROADSECT_ID"],
            record_date=row["record_date"],
            period=row["period"],
            go_time=float(row["GOTIME"]),
            go_count=int(row["GOCOUNT"]),
            go_len=float(row["GOLEN"]),
            avg_speed=round(float(row["avg_speed"]), 2),
            is_peak=bool(row["is_peak"]),
            is_workday=bool(row["is_workday"]),
            peak_type=str(row["peak_type"]),
        ))

    # 3. 逐条尝试插入，遇到唯一约束冲突（重复数据）就回滚跳过
    for rec in records:
        try:
            db_session.add(rec)
            db_session.flush()
            saved_count += 1
        except Exception:
            db_session.rollback()

    db_session.commit()
    return saved_count


def insert_batch_to_db_fast(df: pd.DataFrame, db_session) -> int:
    """
    高速批量写入，用 MySQL 的 INSERT IGNORE 语句。
    INSERT IGNORE 的好处是遇到重复数据会自动跳过而不报错，
    比上面逐条插入的方式快约 50 倍。
    """
    if df.empty:
        return 0

    from sqlalchemy import text
    from backend.app.models.models import RoadSection

    # 1. 同样要确保路段表里有对应记录
    road_ids_in_batch = df["ROADSECT_ID"].unique().tolist()
    existing_roads = {
        r.roadsect_id
        for r in db_session.query(RoadSection.roadsect_id)
        .filter(RoadSection.roadsect_id.in_(road_ids_in_batch))
        .all()
    }
    new_roads = [
        RoadSection(roadsect_id=rid)
        for rid in road_ids_in_batch
        if rid not in existing_roads
    ]
    if new_roads:
        db_session.add_all(new_roads)
        db_session.commit()

    # 2. 拼装要插入的数据列表
    rows_to_insert = []
    for _, row in df.iterrows():
        rows_to_insert.append({
            "roadsect_id": row["ROADSECT_ID"],
            "record_date": row["record_date"],
            "period": row["period"],
            "go_time": float(row["GOTIME"]),
            "go_count": int(row["GOCOUNT"]),
            "go_len": float(row["GOLEN"]),
            "avg_speed": round(float(row["avg_speed"]), 2),
            "is_peak": bool(row["is_peak"]),
            "is_workday": bool(row["is_workday"]),
            "peak_type": str(row["peak_type"]),
        })

    if not rows_to_insert:
        return 0

    # 分批插入，每批 500 条，避免一次性拼出太长的 SQL 语句
    CHUNK_SIZE = 500
    total_inserted = 0
    for i in range(0, len(rows_to_insert), CHUNK_SIZE):
        chunk = rows_to_insert[i:i + CHUNK_SIZE]
        sql = text("""
            INSERT IGNORE INTO road_speed_records
                (roadsect_id, record_date, period, go_time, go_count, go_len,
                 avg_speed, is_peak, is_workday, peak_type)
            VALUES
                (:roadsect_id, :record_date, :period, :go_time, :go_count, :go_len,
                 :avg_speed, :is_peak, :is_workday, :peak_type)
        """)
        result = db_session.execute(sql, chunk)
        total_inserted += result.rowcount
    db_session.commit()
    return total_inserted


# ==================== 采集入库主流程 ====================

def fetch_and_import(
    start_page: int = 1,
    max_pages: int = 100,
    rows_per_page: int = 1000,
) -> dict:
    """
    分页采集并逐页写入数据库的主流程。
    采用「边拉边存」的流式方式，不会一次把所有数据全部加载到内存。
    支持从中间某一页开始采集（断点续采），这在上次中断后很有用。
    """
    from backend.app.core.database import SessionLocal

    logger.info(f"=== 数据采集任务开始 ===")
    logger.info(f"起始页: {start_page}, 最大页数: {max_pages}, 每页: {rows_per_page} 条")

    # 先请求第一页，探测一下数据集的总量
    first_resp = fetch_page(start_page, rows_per_page)
    api_total = first_resp.get("total", 0)
    logger.info(f"数据集总量: {api_total} 条")

    if api_total == 0:
        logger.warning("API 返回 0 条数据")
        return {"total_api": 0, "fetched": 0, "saved": 0, "pages_done": 0}

    # 算一下总共要拉多少页
    total_api_pages = (api_total + rows_per_page - 1) // rows_per_page
    if max_pages <= 0:
        end_page = total_api_pages
    else:
        end_page = min(start_page + max_pages - 1, total_api_pages)

    logger.info(f"API 共 {total_api_pages} 页，本次采集 {start_page} ~ {end_page} 页")

    # 正式开始逐页采集
    total_fetched = 0
    total_saved = 0
    pages_done = 0
    db = SessionLocal()

    try:
        for page_num in range(start_page, end_page + 1):
            t0 = _time.time()

            # 第一页刚才已经请求过了，不用重复请求
            if page_num == start_page:
                resp = first_resp
            else:
                resp = fetch_page(page_num, rows_per_page)

            data_list = resp.get("data", [])
            if not data_list:
                logger.info(f"第 {page_num} 页无数据，采集结束")
                break

            # 清洗转换
            df = process_batch(data_list)
            total_fetched += len(data_list)

            # 写入数据库
            saved = insert_batch_to_db_fast(df, db)
            total_saved += saved
            pages_done += 1

            elapsed = _time.time() - t0
            logger.info(
                f"[{page_num}/{end_page}] "
                f"抓取 {len(data_list)} 条, 处理 {len(df)} 条, "
                f"新增入库 {saved} 条, 耗时 {elapsed:.1f}s"
            )

            # 限流：如果处理太快就稍微等一下，别把人家 API 打太猛
            if elapsed < 0.3:
                _time.sleep(0.3 - elapsed)

    except Exception as e:
        logger.error(f"采集异常(第 {start_page + pages_done} 页): {e}")
    finally:
        db.close()

    logger.info(
        f"=== 采集完成 === "
        f"共 {pages_done} 页, 抓取 {total_fetched} 条, 入库 {total_saved} 条"
    )
    return {
        "total_api": api_total,
        "fetched": total_fetched,
        "saved": total_saved,
        "pages_done": pages_done,
        "last_page": start_page + pages_done - 1 if pages_done > 0 else start_page,
    }


def main():
    """
    命令行入口，可以通过环境变量控制采集参数：
    - FETCH_START_PAGE: 从第几页开始（默认 1）
    - FETCH_MAX_PAGES: 最多采多少页（默认 100）
    - FETCH_ROWS_PER_PAGE: 每页多少条（默认 1000）
    """
    start_page = int(os.environ.get("FETCH_START_PAGE", "1"))
    max_pages = int(os.environ.get("FETCH_MAX_PAGES", "100"))
    rows_per_page = int(os.environ.get("FETCH_ROWS_PER_PAGE", "1000"))

    result = fetch_and_import(start_page, max_pages, rows_per_page)
    logger.info(f"采集结果: {result}")


if __name__ == "__main__":
    main()
