#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速測試腳本：只處理 5 檔股票，用於驗證系統功能
"""
import os, sys, json, time, requests, pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# 設定
os.environ.setdefault("TARGET_DATE", datetime.now().strftime("%Y-%m-%d"))
os.environ.setdefault("OUTPUT_DIR", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "docs", "data"))
os.environ["API_DELAY"] = "0.3"

# 引入主模組
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_data as fd

def main():
    target_date_str = os.environ.get("TARGET_DATE")
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    out_dir = os.environ.get("OUTPUT_DIR")

    print(f"[測試] 資料日期: {target_date_str}")
    token = fd.get_token()
    if not token:
        print("[錯誤] 登入失敗")
        return

    # 取得台股清單（去重）
    df_info = fd.fetch_finmind("TaiwanStockInfo", "2020-01-01", token=token)
    df_info = df_info[df_info["type"].isin(["twse", "tpex"])]
    df_info = df_info.drop_duplicates(subset=["stock_id"], keep="first")

    # 只取指定 5 檔
    test_ids = ["2330", "2317", "2454", "2308", "2881"]
    df_test = df_info[df_info["stock_id"].isin(test_ids)].reset_index(drop=True)

    results = []
    for _, row in df_test.iterrows():
        sid   = row["stock_id"]
        sname = row["stock_name"]
        ind   = row.get("industry_category", "")
        print(f"處理 {sid} {sname}...")
        r = fd.process_stock(sid, sname, ind, target_date, token)
        results.append(r)
        print(f"  EPS={r['前一年_EPS']}, 推估EPS={r['推估本年度EPS']}, "
              f"股價={r['今日股價']}, 報酬={r['報酬']}")

    # 儲存
    os.makedirs(out_dir, exist_ok=True)
    df_out = pd.DataFrame(results)
    df_out.to_csv(os.path.join(out_dir, f"stock_data_{target_date_str}.csv"),
                  index=False, encoding="utf-8-sig")
    df_out.to_json(os.path.join(out_dir, f"stock_data_{target_date_str}.json"),
                   orient="records", force_ascii=False)
    df_out.to_csv(os.path.join(out_dir, "stock_data_latest.csv"),
                  index=False, encoding="utf-8-sig")
    df_out.to_json(os.path.join(out_dir, "stock_data_latest.json"),
                   orient="records", force_ascii=False)

    # 更新日期清單
    dates_file = os.path.join(out_dir, "available_dates.json")
    dates = []
    if os.path.exists(dates_file):
        with open(dates_file, "r") as f:
            dates = json.load(f)
    if target_date_str not in dates:
        dates.append(target_date_str)
    dates.sort(reverse=True)
    with open(dates_file, "w") as f:
        json.dump(dates, f)

    print(f"\n[完成] {len(results)} 檔股票，資料已儲存至 {out_dir}")

if __name__ == "__main__":
    main()
