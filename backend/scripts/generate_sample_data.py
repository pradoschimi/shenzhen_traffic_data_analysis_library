"""
样本数据生成脚本，从 API 选择性爬取约 2 万条真实数据。

背景：
  完整数据集有 1000 多万条，全部拉下来太慢了，对于演示&开发来说只需要一个小而美的子集。
  这个脚本只抽取 2018年4月6日~19日（14天）的数据，并且在时间上尽量均匀分布。

策略：
  - 把 14天 × 24小时 = 336 个时间桶，每个桶最多 60 条
  - 不是每页都请求，而是每隔几页取一页（默认每隔 4 页），这样能快速扫描整个数据集
  - 凑够 2 万条就停下来
"""
import os
import sys
import time as _time
from datetime import datetime, date, timezone, timedelta
from collections import defaultdict

import httpx
import pandas as pd
import numpy as np

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from sqlalchemy import text
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.models.models import RoadSection

API_URL = "https://opendata.sz.gov.cn/api/29200_00403590/1/service.xhtml"
BJT = timezone(timedelta(hours=8))

# 采集目标配置
TARGET_TOTAL = 20000       # 总共要采多少条
TARGET_START = date(2018, 4, 6)   # 目标日期范围开始
TARGET_END = date(2018, 4, 19)    # 目标日期范围结束
BUCKET_LIMIT = 60  # 每个(日期+小时)组合最多保留的条数，超过就丢弃


def fetch_page(page: int, rows: int = 1000) -> list:
    """请求 API 某一页的数据，返回原始记录列表"""
    params = {"appKey": settings.sz_opendata_app_key, "page": page, "rows": rows}
    with httpx.Client(timeout=60.0) as client:
        r = client.get(API_URL, params=params)
        r.raise_for_status()
        return r.json().get("data", [])


def process_rows(data_list: list) -> list:
    """
    解析一批原始数据，只保留目标日期范围内的有效记录。
    返回值里带了 _date 和 _hour 临时字段，方便后面做分桶筛选。
    """
    results = []
    for row in data_list:
        try:
            ts = int(row["TIME"])
            period_num = int(row["PERIOD"])
            dt = datetime.fromtimestamp(ts / 1000, tz=BJT)
            rec_date = dt.date()

            if rec_date < TARGET_START or rec_date > TARGET_END:
                continue

            # PERIOD -> "HH:MM"
            total_min = (period_num - 1) * 5
            hour = total_min // 60
            minute = total_min % 60
            period_str = f"{hour:02d}:{minute:02d}"

            go_time = float(row.get("GOTIME", 0) or 0)
            go_len = float(row.get("GOLEN", 0) or 0)
            go_count = int(float(row.get("GOCOUNT", 0) or 0))

            if go_time <= 0:
                continue
            avg_speed = round((go_len / go_time) * 3.6, 2)
            if avg_speed < 0 or avg_speed > 200:
                continue

            dow = rec_date.weekday()
            is_workday = dow < 5
            if 7 <= hour <= 8:
                peak_type, is_peak = "早高峰", True
            elif 17 <= hour <= 18:
                peak_type, is_peak = "晚高峰", True
            else:
                peak_type, is_peak = "平峰", False

            results.append({
                "roadsect_id": str(row["ROADSECT_ID"]),
                "record_date": str(rec_date),
                "period": period_str,
                "go_time": round(go_time, 2),
                "go_count": go_count,
                "go_len": round(go_len, 2),
                "avg_speed": avg_speed,
                "is_peak": is_peak,
                "is_workday": is_workday,
                "peak_type": peak_type,
                "_date": rec_date,
                "_hour": hour,
            })
        except (ValueError, KeyError):
            continue
    return results


def main():
    db = SessionLocal()

    # 1. 先清空以前的数据，保证每次生成的都是全新的样本
    print("清空旧速度记录...")
    db.execute(text("DELETE FROM road_speed_records"))
    db.commit()
    print("已清空")

    # 2. 准备分桶计数器，用来控制每个时间桶的数据量
    bucket_counts = defaultdict(int)  # key: (日期, 小时) -> 已收集数量
    total_kept = 0
    all_records = []  # 暂存要插入的记录
    pages_scanned = 0

    # 3. 扫描策略：不是每页都拉，而是每隔 STEP 页取一页
    #    这样能快速扫过整个数据集，同时保证时间分布均匀
    STEP = 4
    MAX_PAGE = 10174  # API 数据集总页数（约 1017 万条 / 每页 1000 条）

    print(f"开始从 API 选择性爬取数据...")
    print(f"目标: {TARGET_TOTAL} 条, 日期范围: {TARGET_START} ~ {TARGET_END}")
    print(f"扫描策略: 每隔 {STEP} 页取 1 页, 最大页码 {MAX_PAGE}")
    print()

    page = 1
    while page <= MAX_PAGE and total_kept < TARGET_TOTAL:
        t0 = _time.time()

        try:
            data_list = fetch_page(page, 1000)
        except Exception as e:
            print(f"  page {page}: 请求失败 ({e}), 跳过")
            page += STEP
            continue

        if not data_list:
            print(f"  page {page}: 无数据, 采集结束")
            break

        # 从这一页解析出目标日期范围的记录
        parsed = process_rows(data_list)

        # 按分桶筛选：超过上限的桶就不要了
        kept_this_page = 0
        for rec in parsed:
            bucket_key = (rec["_date"], rec["_hour"])
            if bucket_counts[bucket_key] >= BUCKET_LIMIT:
                continue
            bucket_counts[bucket_key] += 1
            total_kept += 1
            kept_this_page += 1
            # 去掉临时字段，只保留要写入数据库的字段
            clean = {k: v for k, v in rec.items() if not k.startswith("_")}
            all_records.append(clean)

            if total_kept >= TARGET_TOTAL:
                break

        pages_scanned += 1
        elapsed = _time.time() - t0

        if pages_scanned % 50 == 0 or kept_this_page > 0:
            # 获取该页的日期信息
            if parsed:
                page_date = parsed[0]["_date"]
                print(f"  page {page:>5} ({page_date}): "
                      f"原始 {len(data_list)}, 范围内 {len(parsed)}, "
                      f"保留 {kept_this_page}, 累计 {total_kept}/{TARGET_TOTAL} "
                      f"({elapsed:.1f}s)")

        # 限流，别请求太快
        if elapsed < 0.2:
            _time.sleep(0.2 - elapsed)

        page += STEP

    print(f"\n扫描完成: 共扫描 {pages_scanned} 页, 保留 {total_kept} 条")

    # 4. 确保所有路段 ID 都在 road_sections 表里，不然外键约束会报错
    print("确保路段表完整...")
    road_ids_needed = set(r["roadsect_id"] for r in all_records)
    existing = set(
        r[0] for r in db.query(RoadSection.roadsect_id)
        .filter(RoadSection.roadsect_id.in_(list(road_ids_needed)))
        .all()
    )
    new_roads = [RoadSection(roadsect_id=rid) for rid in road_ids_needed - existing]
    if new_roads:
        db.add_all(new_roads)
        db.commit()
        print(f"  新增 {len(new_roads)} 条路段")

    # 5. 用 INSERT IGNORE 批量写入，每批 500 条
    print("写入数据库...")
    CHUNK = 500
    inserted = 0
    for i in range(0, len(all_records), CHUNK):
        chunk = all_records[i:i + CHUNK]
        sql = text("""
            INSERT IGNORE INTO road_speed_records
                (roadsect_id, record_date, period, go_time, go_count, go_len,
                 avg_speed, is_peak, is_workday, peak_type)
            VALUES
                (:roadsect_id, :record_date, :period, :go_time, :go_count, :go_len,
                 :avg_speed, :is_peak, :is_workday, :peak_type)
        """)
        result = db.execute(sql, chunk)
        inserted += result.rowcount
    db.commit()
    print(f"实际写入: {inserted} 条")

    # 6. 最后看一下每天的数据量分布情况，确认样本质量
    rows = db.execute(text(
        "SELECT record_date, COUNT(*) c FROM road_speed_records "
        "GROUP BY record_date ORDER BY record_date"
    )).fetchall()
    print(f"\n日期分布 ({len(rows)} 天):")
    for r in rows:
        print(f"  {r[0]}: {r[1]:>5} 条")

    total = db.execute(text("SELECT COUNT(*) FROM road_speed_records")).scalar()
    print(f"\n最终总计: {total} 条")
    db.close()


if __name__ == "__main__":
    main()
