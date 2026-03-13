#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台股分析系統 - 資料撈取與計算腳本
使用 FinMind API 撈取台股資料，計算 EPS、本益比、推估股價等欄位
每日 14:00 由 GitHub Actions 自動執行

特色：
- 支援斷點續傳（中途中斷可從上次進度繼續）
- 自動重試機制
- 進度顯示
"""

import os
import sys
import json
import time
import requests
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ===================== 設定 =====================
API_URL   = "https://api.finmindtrade.com/api/v4/data"
LOGIN_URL = "https://api.finmindtrade.com/api/v4/login"
USER_ID   = os.environ.get("FINMIND_USER", "Botung")
PASSWORD  = os.environ.get("FINMIND_PASS", "a2334567")

# 輸出目錄（GitHub Pages 使用 docs/data）
OUT_DIR = os.environ.get(
    "OUTPUT_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "data")
)

# API 請求間隔（秒）
API_DELAY = float(os.environ.get("API_DELAY", "0.5"))

# ===================== FinMind API =====================
_token_cache = None

def get_token() -> str | None:
    """登入 FinMind 取得 API Token"""
    global _token_cache
    if _token_cache:
        return _token_cache
    try:
        resp = requests.post(
            LOGIN_URL,
            data={"user_id": USER_ID, "password": PASSWORD},
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            if "token" in data:
                _token_cache = data["token"]
                print(f"[FinMind] 登入成功")
                return _token_cache
        print(f"[FinMind] 登入失敗: {resp.text}")
    except Exception as e:
        print(f"[FinMind] 登入例外: {e}")
    return None


def fetch_finmind(dataset: str, start_date: str, end_date: str = None,
                  data_id: str = None, token: str = None) -> pd.DataFrame:
    """呼叫 FinMind API 取得資料集"""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    params = {"dataset": dataset, "start_date": start_date}
    if end_date:
        params["end_date"] = end_date
    if data_id:
        params["data_id"] = data_id

    for attempt in range(3):
        try:
            resp = requests.get(API_URL, headers=headers, params=params, timeout=60)
            if resp.status_code == 200:
                res = resp.json()
                if res.get("msg") == "success":
                    return pd.DataFrame(res.get("data", []))
                else:
                    print(f"  [API] {dataset} 回傳: {res.get('msg')}")
                    return pd.DataFrame()
            elif resp.status_code == 402:
                print(f"[FinMind] API 用量超出上限，等待 60 秒後重試...")
                time.sleep(60)
                continue
            else:
                print(f"  [API] HTTP {resp.status_code} for {dataset}/{data_id}")
                return pd.DataFrame()
        except requests.exceptions.Timeout:
            print(f"  [API] 逾時 (嘗試 {attempt+1}/3)")
            time.sleep(3)
        except Exception as e:
            print(f"  [API] 例外 (嘗試 {attempt+1}/3): {e}")
            time.sleep(2)
    return pd.DataFrame()


# ===================== 計算邏輯 =====================
def process_stock(stock_id: str, stock_name: str, industry: str,
                  target_date: datetime, token: str) -> dict:
    """計算單一股票的所有分析欄位"""

    year_now   = target_date.year
    year_prev  = year_now - 1
    year_prev2 = year_now - 2
    target_str = target_date.strftime("%Y-%m-%d")
    start_2y   = (target_date - relativedelta(years=2)).strftime("%Y-%m-%d")

    result = {
        "代號": stock_id,
        "名稱": stock_name,
        "產業別": industry,
        "前一年_EPS": 0.0,
        "前一年營收_e": 0.0,
        "轉換數據EPS_1": 0.0,
        "本年度累積營收換算EPS": 0.0,
        "推估本年度營收": 0.0,
        "推估本年度EPS": 0.0,
        "平均前2年本益比": 0.0,
        "前2年本益比最高最低差": 0.0,
        "前2年最低本益比": 0.0,
        "前2年最高本益比": 0.0,
        "用本年度推估EPS換算股價最低值": 0.0,
        "用本年度推估EPS換算股價最高值": 0.0,
        "用本年度推估EPS換算股價平均值": 0.0,
        "今日股價": 0.0,
        "報酬": 0.0,
        "風險": 0.0,
        "加成": 0.0,
        "前兩年往後6月最高漲幅_%": 0.0,
        "前兩年往後6月達最高花費天數": 0,
        "前一年往後6月最高漲幅_%": 0.0,
        "前一年往後6月達最高花費天數": 0
    }

    # ---- 1. EPS (TaiwanStockFinancialStatements) ----
    df_fs = fetch_finmind(
        "TaiwanStockFinancialStatements",
        f"{year_prev2}-01-01", target_str,
        data_id=stock_id, token=token
    )
    time.sleep(API_DELAY)

    if not df_fs.empty:
        df_eps = df_fs[df_fs["type"] == "EPS"].copy()
        if not df_eps.empty:
            df_eps["date"] = pd.to_datetime(df_eps["date"])
            eps_prev = df_eps[df_eps["date"].dt.year == year_prev]["value"].sum()
            result["前一年_EPS"] = round(float(eps_prev), 2)

    # ---- 2. 月營收 (TaiwanStockMonthRevenue) ----
    df_rev = fetch_finmind(
        "TaiwanStockMonthRevenue",
        f"{year_prev}-01-01", target_str,
        data_id=stock_id, token=token
    )
    time.sleep(API_DELAY)

    if not df_rev.empty:
        df_rev["date"] = pd.to_datetime(df_rev["date"])

        # 前一年全年總營收
        rev_prev_total = df_rev[df_rev["date"].dt.year == year_prev]["revenue"].sum()
        result["前一年營收_e"] = float(rev_prev_total)

        # 轉換係數
        if result["前一年_EPS"] > 0 and rev_prev_total > 0:
            result["轉換數據EPS_1"] = float(rev_prev_total / result["前一年_EPS"])

        # 本年度累積營收
        df_now = df_rev[df_rev["date"].dt.year == year_now].copy()
        if not df_now.empty:
            months_now = df_now["revenue_month"].tolist()
            rev_now_acc = df_now["revenue"].sum()

            # 去年同期營收
            df_prev_same = df_rev[
                (df_rev["date"].dt.year == year_prev) &
                (df_rev["revenue_month"].isin(months_now))
            ]
            rev_prev_same = df_prev_same["revenue"].sum()

            if rev_prev_same > 0:
                ratio = rev_now_acc / rev_prev_same
                est_rev = rev_prev_total * ratio
                result["推估本年度營收"] = float(est_rev)

                if result["轉換數據EPS_1"] > 0:
                    result["本年度累積營收換算EPS"] = round(
                        rev_now_acc / result["轉換數據EPS_1"], 2)
                    result["推估本年度EPS"] = round(
                        est_rev / result["轉換數據EPS_1"], 2)

    # ---- 3. 本益比 (TaiwanStockPER) ----
    df_per = fetch_finmind(
        "TaiwanStockPER", start_2y, target_str,
        data_id=stock_id, token=token
    )
    time.sleep(API_DELAY)

    if not df_per.empty:
        per_vals = pd.to_numeric(df_per["PER"], errors="coerce").dropna()
        per_vals = per_vals[per_vals > 0]
        if not per_vals.empty:
            per_max = float(per_vals.max())
            per_min = float(per_vals.min())
            per_avg = float(per_vals.mean())
            result["前2年最高本益比"] = round(per_max, 2)
            result["前2年最低本益比"] = round(per_min, 2)
            result["平均前2年本益比"] = round(per_avg, 2)
            result["前2年本益比最高最低差"] = round(per_max - per_min, 2)

            est_eps = result["推估本年度EPS"]
            if est_eps > 0:
                result["用本年度推估EPS換算股價最低值"] = round(est_eps * per_min, 2)
                result["用本年度推估EPS換算股價最高值"] = round(est_eps * per_max, 2)
                result["用本年度推估EPS換算股價平均值"] = round(est_eps * per_avg, 2)

    # ---- 4. 股價 (TaiwanStockPrice) ----
    df_price = fetch_finmind(
        "TaiwanStockPrice", start_2y, target_str,
        data_id=stock_id, token=token
    )
    time.sleep(API_DELAY)

    if not df_price.empty:
        df_price["date"] = pd.to_datetime(df_price["date"])
        df_price = df_price.sort_values("date")

        # 今日（或最近交易日）收盤價
        latest_close = float(df_price.iloc[-1]["close"])
        result["今日股價"] = latest_close

        # 報酬、風險、加成
        avg_est  = result["用本年度推估EPS換算股價平均值"]
        low_est  = result["用本年度推估EPS換算股價最低值"]
        high_est = result["用本年度推估EPS換算股價最高值"]

        if latest_close > 0:
            if avg_est > 0:
                result["報酬"] = round(avg_est / latest_close, 2)
            if low_est > 0:
                result["風險"] = round(low_est / latest_close, 2)
            if high_est > 0:
                result["加成"] = round(high_est / latest_close, 2)

        # ---- 前兩年往後 6 個月最高漲幅 ----
        date_2y = target_date - relativedelta(years=2)
        df_after_2y = df_price[df_price["date"] >= date_2y]
        if not df_after_2y.empty:
            base_row_2y   = df_after_2y.iloc[0]
            base_price_2y = float(base_row_2y["close"])
            base_date_2y  = base_row_2y["date"]
            end_date_2y   = base_date_2y + relativedelta(months=6)

            df_window_2y = df_price[
                (df_price["date"] >= base_date_2y) &
                (df_price["date"] <= end_date_2y)
            ]
            if not df_window_2y.empty and base_price_2y > 0:
                max_row_2y   = df_window_2y.loc[df_window_2y["close"].idxmax()]
                max_price_2y = float(max_row_2y["close"])
                max_date_2y  = max_row_2y["date"]
                result["前兩年往後6月最高漲幅_%"] = round(
                    (max_price_2y - base_price_2y) / base_price_2y * 100, 2)
                result["前兩年往後6月達最高花費天數"] = int(
                    (max_date_2y - base_date_2y).days)

        # ---- 前一年往後 6 個月最高漲幅 ----
        date_1y = target_date - relativedelta(years=1)
        df_after_1y = df_price[df_price["date"] >= date_1y]
        if not df_after_1y.empty:
            base_row_1y   = df_after_1y.iloc[0]
            base_price_1y = float(base_row_1y["close"])
            base_date_1y  = base_row_1y["date"]
            end_date_1y   = base_date_1y + relativedelta(months=6)

            df_window_1y = df_price[
                (df_price["date"] >= base_date_1y) &
                (df_price["date"] <= end_date_1y)
            ]
            if not df_window_1y.empty and base_price_1y > 0:
                max_row_1y   = df_window_1y.loc[df_window_1y["close"].idxmax()]
                max_price_1y = float(max_row_1y["close"])
                max_date_1y  = max_row_1y["date"]
                result["前一年往後6月最高漲幅_%"] = round(
                    (max_price_1y - base_price_1y) / base_price_1y * 100, 2)
                result["前一年往後6月達最高花費天數"] = int(
                    (max_date_1y - base_date_1y).days)

    return result


# ===================== 主程式 =====================
def main():
    target_date_str = os.environ.get(
        "TARGET_DATE", datetime.now().strftime("%Y-%m-%d"))
    
    # 相容 YYYY-MM-DD 和 YYYYMMDD 格式
    try:
        if "-" in target_date_str:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        else:
            target_date = datetime.strptime(target_date_str, "%Y%m%d")
            # 統一轉回 YYYY-MM-DD 格式供後續檔名使用
            target_date_str = target_date.strftime("%Y-%m-%d")
    except ValueError:
        print(f"Error: Invalid date format {target_date_str}. Use YYYY-MM-DD or YYYYMMDD.")
        sys.exit(1)

    print(f"[開始] 資料日期: {target_date_str}")
    print(f"[設定] 輸出目錄: {OUT_DIR}")
    print(f"[設定] API 延遲: {API_DELAY} 秒")

    # 登入取得 Token
    token = get_token()
    if not token:
        print("[錯誤] 無法取得 API Token，程式結束")
        sys.exit(1)

    # 取得台股清單
    print("[步驟 1] 取得台股清單...")
    df_info = fetch_finmind("TaiwanStockInfo", "2020-01-01", token=token)
    if df_info.empty:
        print("[錯誤] 無法取得台股清單，程式結束")
        sys.exit(1)

    # 只保留上市 (twse) 與上櫃 (tpex)，去重
    df_info = df_info[df_info["type"].isin(["twse", "tpex"])]
    df_info = df_info.drop_duplicates(subset=["stock_id"], keep="first")
    df_info = df_info.reset_index(drop=True)
    total = len(df_info)
    print(f"[步驟 1] 共 {total} 檔股票待處理")

    # 斷點續傳：讀取已完成的進度
    os.makedirs(OUT_DIR, exist_ok=True)
    progress_file = os.path.join(OUT_DIR, f"progress_{target_date_str}.json")
    results = []
    processed_ids = set()

    if os.path.exists(progress_file):
        with open(progress_file, "r", encoding="utf-8") as f:
            saved = json.load(f)
            results = saved.get("results", [])
            processed_ids = set(r["代號"] for r in results)
            print(f"[續傳] 已完成 {len(processed_ids)} 檔，從上次進度繼續...")

    # 逐一處理股票
    start_time = time.time()
    for idx, row in df_info.iterrows():
        stock_id   = row["stock_id"]
        stock_name = row["stock_name"]
        industry   = row.get("industry_category", "")

        if stock_id in processed_ids:
            continue  # 已處理，跳過

        remaining = total - len(processed_ids) - (idx - len(processed_ids))
        elapsed   = time.time() - start_time
        per_stock = elapsed / max(len(results) - len(processed_ids) + 1, 1) if results else 0
        eta_sec   = per_stock * remaining if per_stock > 0 else 0
        eta_str   = f"{int(eta_sec//60)}m{int(eta_sec%60)}s" if eta_sec > 0 else "計算中"

        print(f"[{idx+1}/{total}] {stock_id} {stock_name} (剩餘 {remaining} 檔, ETA: {eta_str})")

        try:
            stock_data = process_stock(
                stock_id, stock_name, industry, target_date, token)
            results.append(stock_data)
        except Exception as e:
            print(f"  [警告] {stock_id} 處理失敗: {e}")
            results.append({
                "代號": stock_id, "名稱": stock_name, "產業別": industry,
                "前一年_EPS": 0.0, "前一年營收_e": 0.0, "轉換數據EPS_1": 0.0,
                "本年度累積營收換算EPS": 0.0, "推估本年度營收": 0.0,
                "推估本年度EPS": 0.0, "平均前2年本益比": 0.0,
                "前2年本益比最高最低差": 0.0, "前2年最低本益比": 0.0,
                "前2年最高本益比": 0.0, "用本年度推估EPS換算股價最低值": 0.0,
                "用本年度推估EPS換算股價最高值": 0.0, "用本年度推估EPS換算股價平均值": 0.0,
                "今日股價": 0.0, "報酬": 0.0, "風險": 0.0, "加成": 0.0,
                "前兩年往後6月最高漲幅_%": 0.0, "前兩年往後6月達最高花費天數": 0,
                "前一年往後6月最高漲幅_%": 0.0, "前一年往後6月達最高花費天數": 0
            })

        # 每 50 檔儲存一次進度
        if len(results) % 50 == 0:
            with open(progress_file, "w", encoding="utf-8") as f:
                json.dump({"results": results, "updated": datetime.now().isoformat()},
                          f, ensure_ascii=False)
            print(f"  [進度] 已儲存 {len(results)} 筆進度")

    # ---- 儲存最終結果 ----
    df_out = pd.DataFrame(results)

    csv_path  = os.path.join(OUT_DIR, f"stock_data_{target_date_str}.csv")
    json_path = os.path.join(OUT_DIR, f"stock_data_{target_date_str}.json")
    df_out.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df_out.to_json(json_path, orient="records", force_ascii=False)

    # 最新資料
    df_out.to_csv(os.path.join(OUT_DIR, "stock_data_latest.csv"),
                  index=False, encoding="utf-8-sig")
    df_out.to_json(os.path.join(OUT_DIR, "stock_data_latest.json"),
                   orient="records", force_ascii=False)

    # 更新可用日期清單
    dates_file = os.path.join(OUT_DIR, "available_dates.json")
    dates = []
    if os.path.exists(dates_file):
        with open(dates_file, "r", encoding="utf-8") as f:
            dates = json.load(f)
    if target_date_str not in dates:
        dates.append(target_date_str)
    dates.sort(reverse=True)
    with open(dates_file, "w", encoding="utf-8") as f:
        json.dump(dates, f, ensure_ascii=False)

    # 清除進度檔
    if os.path.exists(progress_file):
        os.remove(progress_file)

    elapsed_total = time.time() - start_time
    print(f"\n[完成] 共處理 {len(results)} 檔股票")
    print(f"[完成] 耗時 {int(elapsed_total//60)} 分 {int(elapsed_total%60)} 秒")
    print(f"[完成] CSV:  {csv_path}")
    print(f"[完成] JSON: {json_path}")


if __name__ == "__main__":
    main()
