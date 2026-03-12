/* ===================================================
   台股分析系統 - 前端應用邏輯
   =================================================== */

// ---- 設定 ----
const DATA_BASE_URL = "./data/";
const GITHUB_OWNER = "botungchang-cmd"; // 請改為您的 GitHub 帳號
const GITHUB_REPO = "taiwan-stock-analyzer"; // 請改為您的 Repository 名稱
const GITHUB_ACTIONS_URL = `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/daily_fetch.yml`;

let stockTable = null;
let currentData = [];

// ---- 工具函式 ----
function formatNum(val, decimals = 2) {
  if (val === null || val === undefined || isNaN(val)) return "-";
  return Number(val).toFixed(decimals);
}

function formatRevenue(val) {
  // 轉換為億元
  if (val === null || val === undefined || isNaN(val) || val === 0) return "-";
  return (val / 1e8).toFixed(2);
}

function formatPct(val) {
  if (val === null || val === undefined || isNaN(val)) return "-";
  const n = Number(val);
  const cls = n > 0 ? "num-positive" : n < 0 ? "num-negative" : "num-neutral";
  return `<span class="${cls}">${n.toFixed(2)}%</span>`;
}

function formatRatio(val) {
  if (val === null || val === undefined || isNaN(val) || val === 0) return "-";
  const n = Number(val);
  const cls = n > 1.1 ? "num-positive" : n < 0.9 ? "num-negative" : "num-neutral";
  return `<span class="${cls}">${n.toFixed(2)}</span>`;
}

function getRowClass(row) {
  const ratio = row["報酬"];
  if (!ratio || ratio === 0) return "";
  if (ratio > 1.1) return "row-good";
  if (ratio < 0.9) return "row-bad";
  return "row-warn";
}

function showLoading(show) {
  const el = document.getElementById("loadingIndicator");
  if (show) el.classList.remove("hidden");
  else el.classList.add("hidden");
}

function showError(msg) {
  const el = document.getElementById("errorMsg");
  el.textContent = msg;
  el.classList.remove("hidden");
}

function hideError() {
  document.getElementById("errorMsg").classList.add("hidden");
}

function setStatus(msg) {
  document.getElementById("statusMsg").textContent = msg;
}

// ---- 日期處理 ----
function getTodayStr() {
  const d = new Date();
  return d.toISOString().split("T")[0];
}

function initDatePicker() {
  const dp = document.getElementById("datePicker");
  dp.value = getTodayStr();
  dp.max = getTodayStr();
}

// ---- 資料載入 ----
async function loadAvailableDates() {
  try {
    const resp = await fetch(`${DATA_BASE_URL}available_dates.json?t=${Date.now()}`);
    if (resp.ok) {
      return await resp.json();
    }
  } catch (e) {
    console.warn("Cannot load available_dates.json:", e);
  }
  return [];
}

async function loadStockData(dateStr) {
  showLoading(true);
  hideError();
  document.getElementById("tableWrapper").classList.add("hidden");

  let url = `${DATA_BASE_URL}stock_data_${dateStr}.json?t=${Date.now()}`;

  try {
    let resp = await fetch(url);
    if (!resp.ok) {
      // 嘗試載入最新資料
      url = `${DATA_BASE_URL}stock_data_latest.json?t=${Date.now()}`;
      resp = await fetch(url);
      if (!resp.ok) {
        throw new Error(`找不到 ${dateStr} 的資料，且最新資料也無法載入。`);
      }
      setStatus(`⚠️ 找不到 ${dateStr} 的資料，已載入最新可用資料。`);
    } else {
      setStatus(`✅ 已載入 ${dateStr} 的資料`);
    }

    const data = await resp.json();
    currentData = data;
    renderTable(data, dateStr);
  } catch (e) {
    showError(`資料載入失敗：${e.message}\n\n請確認 GitHub Actions 是否已執行資料更新。`);
    setStatus("❌ 載入失敗");
  } finally {
    showLoading(false);
  }
}

// ---- 產業篩選 ----
function populateIndustryFilter(data) {
  const select = document.getElementById("industryFilter");
  const industries = [...new Set(data.map(d => d["產業別"]).filter(Boolean))].sort();
  select.innerHTML = '<option value="">全部產業</option>';
  industries.forEach(ind => {
    const opt = document.createElement("option");
    opt.value = ind;
    opt.textContent = ind;
    select.appendChild(opt);
  });
}

// ---- 表格渲染 ----
function renderTable(data, dateStr) {
  populateIndustryFilter(data);

  // 更新資訊標籤
  document.getElementById("dataDateLabel").textContent = `📅 資料日期：${dateStr}`;
  document.getElementById("stockCountLabel").textContent = `📊 共 ${data.length} 檔股票`;
  document.getElementById("lastUpdate").textContent = new Date().toLocaleString("zh-TW");

  // 清除舊表格
  if (stockTable) {
    stockTable.destroy();
    stockTable = null;
    document.getElementById("tableBody").innerHTML = "";
  }

  // 填充表格
  const tbody = document.getElementById("tableBody");
  tbody.innerHTML = "";

  data.forEach(row => {
    const tr = document.createElement("tr");
    tr.className = getRowClass(row);

    const cells = [
      row["代號"] || "-",
      row["名稱"] || "-",
      row["產業別"] || "-",
      formatNum(row["前一年_EPS"]),
      formatRevenue(row["前一年營收_e"]),
      formatRevenue(row["轉換數據EPS_1"]),
      formatNum(row["本年度累積營收換算EPS"]),
      formatRevenue(row["推估本年度營收"]),
      formatNum(row["推估本年度EPS"]),
      formatNum(row["平均前2年本益比"]),
      formatNum(row["前2年本益比最高最低差"]),
      formatNum(row["前2年最低本益比"]),
      formatNum(row["前2年最高本益比"]),
      formatNum(row["用本年度推估EPS換算股價最低值"]),
      formatNum(row["用本年度推估EPS換算股價最高值"]),
      formatNum(row["用本年度推估EPS換算股價平均值"]),
      formatNum(row["今日股價"]),
      formatRatio(row["報酬"]),
      formatRatio(row["風險"]),
      formatRatio(row["加成"]),
      formatPct(row["前兩年往後6月最高漲幅_%"]),
      row["前兩年往後6月達最高花費天數"] || "-",
      formatPct(row["前一年往後6月最高漲幅_%"]),
      row["前一年往後6月達最高花費天數"] || "-"
    ];

    cells.forEach(cell => {
      const td = document.createElement("td");
      td.innerHTML = cell;
      tr.appendChild(td);
    });

    tbody.appendChild(tr);
  });

  // 初始化 DataTables
  stockTable = $("#stockTable").DataTable({
    pageLength: 50,
    lengthMenu: [25, 50, 100, 200, -1],
    scrollX: true,
    fixedHeader: true,
    language: {
      url: "https://cdn.datatables.net/plug-ins/1.13.7/i18n/zh-HANT.json"
    },
    dom: 'Blfrtip',
    buttons: [
      {
        extend: 'csvHtml5',
        text: '📥 匯出 CSV',
        filename: `台股分析_${dateStr}`,
        charset: 'utf-8',
        bom: true,
        exportOptions: {
          columns: ':visible',
          format: {
            body: function(data, row, column, node) {
              // 移除 HTML 標籤
              return data.replace(/<[^>]*>/g, '');
            }
          }
        }
      }
    ],
    columnDefs: [
      { targets: [3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23], className: "dt-right" }
    ],
    order: [[17, "desc"]] // 預設依報酬降冪排列
  });

  document.getElementById("tableWrapper").classList.remove("hidden");
}

// ---- 搜尋功能 ----
function initSearch() {
  document.getElementById("searchInput").addEventListener("input", function() {
    if (stockTable) {
      stockTable.search(this.value).draw();
    }
  });
}

// ---- 產業篩選功能 ----
function initIndustryFilter() {
  document.getElementById("industryFilter").addEventListener("change", function() {
    if (stockTable) {
      stockTable.column(2).search(this.value).draw();
    }
  });
}

// ---- CSV 匯出（備用按鈕） ----
function exportCSV() {
  if (!currentData || currentData.length === 0) {
    alert("請先載入資料");
    return;
  }

  const dateStr = document.getElementById("datePicker").value;
  const headers = Object.keys(currentData[0]);
  const rows = currentData.map(row =>
    headers.map(h => {
      const v = row[h];
      if (typeof v === "string" && v.includes(",")) return `"${v}"`;
      return v !== null && v !== undefined ? v : "";
    }).join(",")
  );

  const csvContent = "\uFEFF" + [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `台股分析_${dateStr}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ---- 手動更新資料 ----
function openGitHubActions() {
  setStatus("⏳ 正在開啟 GitHub Actions 頁面...");
  setTimeout(() => {
    window.open(GITHUB_ACTIONS_URL, '_blank');
    setStatus("✅ 已開啟 GitHub Actions。請點擊『Run workflow』按鈕手動觸發資料更新。");
  }, 500);
}

// ---- 事件綁定 ----
function bindEvents() {
  document.getElementById("loadBtn").addEventListener("click", () => {
    const dateStr = document.getElementById("datePicker").value;
    if (!dateStr) {
      alert("請選擇日期");
      return;
    }
    loadStockData(dateStr);
  });

  document.getElementById("refreshBtn").addEventListener("click", () => {
    const dateStr = document.getElementById("datePicker").value;
    if (dateStr) loadStockData(dateStr);
  });

  document.getElementById("exportCsvBtn").addEventListener("click", exportCSV);

  document.getElementById("fetchDataBtn").addEventListener("click", openGitHubActions);

  // Enter 鍵觸發載入
  document.getElementById("datePicker").addEventListener("keydown", (e) => {
    if (e.key === "Enter") document.getElementById("loadBtn").click();
  });
}

// ---- 初始化 ----
async function init() {
  initDatePicker();
  bindEvents();
  initSearch();
  initIndustryFilter();

  // 嘗試載入可用日期清單
  const dates = await loadAvailableDates();
  if (dates.length > 0) {
    // 設定日期選擇器為最新可用日期
    const latestDate = dates[0];
    document.getElementById("datePicker").value = latestDate;
    await loadStockData(latestDate);
  } else {
    // 嘗試載入最新資料
    await loadStockData(getTodayStr());
  }
}

// ---- 啟動 ----
document.addEventListener("DOMContentLoaded", init);
