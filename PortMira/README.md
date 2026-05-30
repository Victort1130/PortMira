# PortMira

PortMira 是一款原生 macOS 投資組合追蹤應用程式，以 SwiftUI 打造，支援股票、ETF、加密貨幣、大宗商品、現金等多資產類別，整合即時報價、自動再平衡建議、情境壓力測試、歷史回測、預算管理與財經新聞，讓使用者在一個 app 內掌握完整的個人財務狀況。

---

## 功能列表

### 總覽（Dashboard）
- 即時顯示淨資產、總資產、總負債與年化報酬率（CAGR）
- 資產大類佔比環形圖（股票 / ETF / 加密貨幣 / 大宗商品 / 現金）
- 個別資產配置環形圖（市值前 97% 個別顯示，其餘合併為「其他」）
- 大宗商品行情 Widget（黃金 GC=F、WTI 原油 CL=F、白銀 SI=F、天然氣 NG=F）
- 幣別切換（TWD / USD），即時重新換算所有市值

### 持倉明細（Holdings）
- 可排序的資產明細表格：資產名稱、代號、數量、現價、市值、總成本、未實現損益、損益%、日變動%
- 選擇性顯示 CAGR 欄位（年化報酬率）
- 負債明細表格（信用卡、貸款、融資等）
- 組合統計面板（Sharpe-like 統計資訊）
- RSI（14 期）與 MACD（12-26-9）技術指標即時計算，含中文解讀標籤
- 點擊資產可開啟 K 線圖（含 SMA 20 / SMA 50 均線疊加、成交量子圖）

### 再平衡（Rebalance）
- 依設定的目標比例（Target %）計算各資產偏差
- 可調容忍帶（0–15%），自動標示買入 / 賣出 / 持有建議
- 顯示調整金額與調整股數／單位
- 目前配置 vs 目標配置並排柱狀圖

### 情境分析（Scenario Analysis）
- 透過滑桿設定各資產大類漲跌幅（-100%～+100%）與外幣匯率變動
- 內建四大歷史重大事件 Presets：
  - 2008 金融海嘯
  - 2020 COVID 崩盤
  - 2022 升息熊市
  - 2000 科技泡沫
- 每個歷史事件附帶期間說明與避險建議
- 即時計算情境後淨資產、各資產影響金額與影響百分比
- 情境可儲存 / 載入 / 刪除（存入 portfolio.json）

### 編輯組合（Edit Portfolio）
- 新增、編輯、刪除資產（支援 US Stock、TW Stock、ETF、Crypto、Commodity、Cash、Other）
- 每筆資產可設定：名稱、代號、類別、數量、成本均價、幣別、買入日期、目標比例、目標最小 / 最大比例、備注
- 新增、編輯、刪除負債（信用卡、貸款、融資貸款等），可設定年利率

### 預算追蹤（Budget）
- 按類別（餐飲、交通、訂閱服務、娛樂、投資支出、醫療、購物、其他）設定月 / 雙週 / 週預算
- 可設定預算類別、金額、幣別、週期、警示閾值（0–100%）
- 進度條即時顯示使用比率，超過閾值顯示橘色警示 banner
- 支出記錄新增、編輯、刪除，按年 / 月折疊顯示歷史記錄

### 回測工具（Backtest）
- 選擇任意日期範圍，對組合中含代號的資產執行歷史回測
- 指標：總報酬率、年化報酬率（CAGR）、最大回撤（Max Drawdown）
- 支援基準指數對比：SPY（S&P 500）、QQQ（NASDAQ 100）、0050.TW（台股50）
- 折線圖呈現組合 vs 基準指數走勢
- 各資產個別報酬率排名列表

### 財經新聞（News）
- 自動抓取持倉 ticker 與預設 ticker（SPY、QQQ、BTC-USD、GC=F、0050.TW）的相關新聞
- 去重排序（最新優先），顯示來源與相對發布時間（X 分鐘前 / X 小時前 / X 天前）
- 點擊標題以預設瀏覽器開啟原文連結

---

## 技術棧

| 層級 | 技術 |
|------|------|
| UI 框架 | SwiftUI（NavigationSplitView、HSplitView、Table、Charts） |
| 語言 | Swift 5.0 |
| 狀態管理 | `@Observable`（iOS 17+ / macOS 14+ Observation 框架） |
| 圖表 | Swift Charts（環形圖、柱狀圖、折線圖、K 線圖 RectangleMark + RuleMark） |
| 並發 | Swift Concurrency（`async/await`、`actor`、`withTaskGroup`） |
| 報價來源 | Yahoo Finance API（`query1/query2.finance.yahoo.com`） |
| 匯率來源 | ExchangeRate-API（`api.exchangerate-api.com/v4/latest`） |
| 技術指標 | 自實作 RSI（Wilder 平滑法）、MACD（EMA 12-26-9） |
| 本地儲存 | JSON 檔案持久化至 `Application Support/PortMira/` |
| Bundle ID | `com.github.victort1130.PortMira` |

---

## 專案結構

```
PortMira/
├── PortMira.xcodeproj/          # Xcode 專案設定
└── PortMira/                    # 主要原始碼
    ├── PortMiraApp.swift         # App 進入點，注入 PortfolioStore / BudgetStore
    ├── ContentView.swift         # NavigationSplitView 側欄，定義 AppSection 路由
    │
    ├── Models/
    │   ├── Portfolio.swift       # Asset、Liability、Scenario、Portfolio 資料模型與 enum
    │   ├── EnrichedAsset.swift   # 即時報價後的富化資產、RebalanceAction、ScenarioResult
    │   └── Budget.swift          # Expense、Budget、BudgetStatus、BudgetPeriod 模型
    │
    ├── Services/
    │   ├── PortfolioStore.swift  # @Observable 全域狀態，持久化與價格刷新協調
    │   ├── BudgetStore.swift     # @Observable 預算 / 支出狀態管理
    │   ├── PriceService.swift    # Yahoo Finance 即時報價 + ExchangeRate-API 匯率
    │   ├── CalculationsEngine.swift # 資產富化、淨值計算、再平衡、情境分析、CAGR
    │   ├── BacktestEngine.swift  # actor，歷史 OHLCV 抓取與回測指標計算
    │   ├── TechnicalIndicatorService.swift # actor，RSI / MACD 計算
    │   └── NewsService.swift     # actor，Yahoo Finance 財經新聞聚合去重
    │
    ├── Data/
    │   └── HistoricalEvents.swift # 內建四大歷史事件 Presets 資料
    │
    ├── Views/
    │   ├── Dashboard/
    │   │   └── DashboardView.swift     # 總覽、圓餅圖、大宗商品行情 Widget
    │   ├── Holdings/
    │   │   ├── HoldingsView.swift      # 持倉明細表格、技術指標面板
    │   │   ├── CandlestickView.swift   # K 線圖（OHLCV + SMA + 成交量）
    │   │   └── PortfolioStatsView.swift # 組合統計面板
    │   ├── Rebalance/
    │   │   └── RebalanceView.swift     # 再平衡建議表格與配置柱狀圖
    │   ├── Scenario/
    │   │   └── ScenarioView.swift      # 情境分析控制面板與結果顯示
    │   ├── Edit/
    │   │   ├── EditPortfolioView.swift # 資產 / 負債列表管理
    │   │   ├── AssetFormView.swift     # 資產新增 / 編輯表單
    │   │   └── LiabilityFormView.swift # 負債新增 / 編輯表單
    │   ├── Budget/
    │   │   ├── BudgetView.swift        # 預算總覽、進度條、支出明細
    │   │   ├── BudgetSettingsView.swift # 預算設定表單
    │   │   └── ExpenseFormView.swift   # 支出新增 / 編輯表單
    │   ├── Backtest/
    │   │   └── BacktestView.swift      # 回測設定、折線圖、各資產報酬排名
    │   └── News/
    │       └── NewsView.swift          # 財經新聞列表
    │
    └── Assets.xcassets/              # App 圖示與 Accent Color
```

---

## 執行方式

### 系統需求

| 項目 | 版本 |
|------|------|
| Xcode | 16.0 以上（需支援 Swift Concurrency + Swift Charts） |
| macOS（開發機） | macOS 15 Sequoia 以上 |
| macOS（部署目標） | 26.5（project.pbxproj `MACOSX_DEPLOYMENT_TARGET`） |
| Swift | 5.0 |

### 步驟

1. 複製或下載本 repo
2. 以 Xcode 開啟 `PortMira.xcodeproj`
3. 在 Signing & Capabilities 設定開發者帳號（Development Team）
4. 選擇 macOS scheme，按 ⌘R 執行
5. 首次啟動後，前往「編輯組合」新增資產，再按 Refresh 按鈕抓取即時報價

> 注意：報價與匯率功能需要網路連線。Yahoo Finance 與 ExchangeRate-API 皆為免費且無需 API Key。

---

## 資料說明

### portfolio.json

路徑：`~/Library/Application Support/PortMira/portfolio.json`

應用程式啟動時自動讀取，每次新增 / 修改 / 刪除資產後自動寫入（atomic write）。

格式概覽：

```json
{
  "meta": {
    "last_updated": "2026-05-30",
    "version": "0.2.0"
  },
  "assets": [
    {
      "id": "uuid",
      "name": "Apple Inc.",
      "category": "stock",
      "ticker": "AAPL",
      "quantity": 10,
      "cost_per_unit": 170.5,
      "currency": "USD",
      "purchase_date": "2023-01-15",
      "target_pct": 20.0,
      "target_min_pct": 15.0,
      "target_max_pct": 25.0,
      "note": "核心持股"
    }
  ],
  "liabilities": [
    {
      "id": "uuid",
      "name": "房貸",
      "category": "loan",
      "amount": 3000000,
      "currency": "TWD",
      "annual_rate": 0.0185,
      "note": ""
    }
  ],
  "scenarios": [
    {
      "id": "sc_abc123",
      "name": "升息情境",
      "created_at": "2026-05-30",
      "shocks": {
        "categories": { "stock": -0.15, "crypto": -0.30 },
        "fx": { "USD": 0.05 }
      }
    }
  ]
}
```

支援的 `category` 值：`stock`、`stock_tw`、`etf`、`crypto`、`commodity`、`cash`、`other`

支援的 `currency` 值：`TWD`、`USD`、`EUR`、`JPY`、`GBP`

### budget_data.json

路徑：`~/Library/Application Support/PortMira/budget_data.json`

儲存預算設定與支出記錄，由 BudgetStore 管理讀寫，格式為 `{ "budgets": [...], "expenses": [...] }`。

---

## Screenshots

<!-- Screenshots -->
