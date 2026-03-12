# 台股分析系統

基於 [FinMind API](https://finmindtrade.com/) 的台股 EPS、本益比與推估股價分析系統。

## 功能特色

- **每日自動更新**：GitHub Actions 於每日台灣時間 14:00 自動撈取資料
- **選擇日期查詢**：可選擇歷史日期查看當日分析結果
- **完整欄位計算**：包含 EPS、月營收、本益比、推估股價、報酬風險等 24 個欄位
- **顏色標示**：依報酬比例以綠/黃/紅色標示投資機會
- **CSV 匯出**：一鍵匯出所有資料為 CSV 檔案
- **產業篩選**：可依產業別篩選股票
- **即時搜尋**：支援代號或名稱關鍵字搜尋

## 欄位說明

| 欄位名稱 | 說明 |
|---------|------|
| 代號 | 股票代號 |
| 名稱 | 股票名稱 |
| 產業別 | 所屬產業分類 |
| 前一年 EPS | 前一年度全年 EPS（四季加總） |
| 前一年營收(億) | 前一年度全年總營收（億元） |
| 轉換EPS=1(億) | 前一年營收 / 前一年 EPS，代表每 1 元 EPS 對應的營收規模 |
| 本年累積營收換算EPS | 本年度累積營收 / 轉換係數 |
| 推估本年度營收(億) | 去年全年營收 × (今年累積營收 / 去年同期營收) |
| 推估本年度EPS | 推估本年度營收 / 轉換係數 |
| 平均前2年本益比 | 過去兩年每日本益比的平均值 |
| 前2年本益比高低差 | 前2年最高本益比 - 最低本益比 |
| 前2年最低本益比 | 過去兩年本益比的最低值 |
| 前2年最高本益比 | 過去兩年本益比的最高值 |
| 推估股價最低值 | 推估本年度EPS × 前2年最低本益比 |
| 推估股價最高值 | 推估本年度EPS × 前2年最高本益比 |
| 推估股價平均值 | 推估本年度EPS × 平均前2年本益比 |
| 今日股價 | 當日（或最近交易日）收盤價 |
| 報酬 | 推估股價平均值 / 今日股價（>1 表示低估） |
| 風險 | 推估股價最低值 / 今日股價 |
| 加成 | 推估股價最高值 / 今日股價 |
| 前兩年往後6月最高漲幅% | 從兩年前當日起，往後6個月內的最高漲幅 |
| 前兩年往後6月達最高天數 | 達到上述最高點所需的天數 |
| 前一年往後6月最高漲幅% | 從一年前當日起，往後6個月內的最高漲幅 |
| 前一年往後6月達最高天數 | 達到上述最高點所需的天數 |

## 顏色說明

| 顏色 | 條件 | 意義 |
|-----|------|------|
| 🟢 綠色 | 報酬 > 1.1 | 今日股價低於平均推估股價 10% 以上，可能低估 |
| 🟡 黃色 | 報酬 0.9 ~ 1.1 | 今日股價接近平均推估股價 |
| 🔴 紅色 | 報酬 < 0.9 | 今日股價高於平均推估股價 10% 以上，可能高估 |

## 部署到 GitHub

### 步驟一：Fork 或建立 Repository

1. 將此專案上傳至您的 GitHub Repository
2. Repository 名稱建議使用 `taiwan-stock-analyzer`

### 步驟二：設定 Secrets

在 GitHub Repository 的 **Settings → Secrets and variables → Actions** 中新增：

| Secret 名稱 | 值 |
|------------|-----|
| `FINMIND_USER` | `Botung` |
| `FINMIND_PASS` | `a2334567` |

### 步驟三：啟用 GitHub Pages

1. 進入 **Settings → Pages**
2. Source 選擇 **GitHub Actions**
3. 儲存設定

### 步驟四：啟用 GitHub Actions

1. 進入 **Actions** 頁籤
2. 如有提示，點擊「I understand my workflows, go ahead and enable them」
3. 手動執行一次 **台股資料每日更新** 工作流程以生成初始資料

### 步驟五：訪問網頁

部署完成後，可透過以下網址訪問：
```
https://{您的GitHub帳號}.github.io/{Repository名稱}/
```

## 本地開發

```bash
# 安裝相依套件
pip install -r requirements.txt

# 執行資料撈取（使用今日日期）
python scripts/fetch_data.py

# 指定日期
TARGET_DATE=2024-12-31 python scripts/fetch_data.py

# 啟動本地伺服器
cd docs && python -m http.server 8080
# 訪問 http://localhost:8080
```

## 資料來源

本系統使用以下 FinMind API 資料集：

| 資料集 | 說明 |
|-------|------|
| `TaiwanStockInfo` | 台股清單（代號、名稱、產業別） |
| `TaiwanStockFinancialStatements` | 財務報表（EPS） |
| `TaiwanStockMonthRevenue` | 月營收 |
| `TaiwanStockPER` | 本益比（PER）歷史資料 |
| `TaiwanStockPrice` | 每日股價 |

## 注意事項

- 本系統僅供參考，**不構成任何投資建議**
- FinMind 免費帳號每小時 API 呼叫上限為 600 次，全市場約 1,800 檔股票，每檔需 4 次 API 呼叫，建議使用 Backer 以上帳號
- 資料更新時間依 FinMind 資料更新時程而定
- EPS 資料為季報加總，可能與年報略有差異

## 授權

MIT License
