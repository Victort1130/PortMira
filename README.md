# PortMira

**PortMira — A local-first portfolio mirror.**

PortMira 是一款本地優先的個人投資組合追蹤工具，支援股票、ETF、加密貨幣、大宗商品、現金等多資產類別，整合即時報價、自動再平衡建議、情境壓力測試、歷史回測、預算管理與財經新聞。所有資料僅存於本機，無需帳號，不上傳任何資料。

---

## 雙平台架構

PortMira 同時提供兩個前端，共享相同的 JSON 資料格式與核心邏輯：

| 平台 | 技術 | 路徑 | 啟動方式 |
|------|------|------|---------|
| **Web（Python）** | Streamlit + Plotly | `app.py` / `src/` | `streamlit run app.py` |
| **macOS 原生** | SwiftUI + Swift Charts | `PortMira/` | Xcode 開啟 `PortMira.xcodeproj` |

```
PortMira/                        ← git repo 根目錄
├── app.py                       ← Streamlit Web app 入口
├── src/                         ← Python 核心邏輯
│   ├── calculations.py          ← 資產計算、淨資產、CAGR
│   ├── price_fetcher.py         ← Yahoo Finance / CoinGecko 報價
│   ├── technical_indicators.py  ← RSI、MACD
│   ├── backtest.py              ← 歷史回測引擎
│   ├── budget_calc.py           ← 預算計算
│   ├── news_fetcher.py          ← 財經新聞抓取
│   ├── charts.py                ← Plotly 圖表
│   ├── historical_events.py     ← 歷史情境 Presets
│   ├── models.py                ← 資料模型
│   └── storage.py               ← JSON 讀寫
├── data/
│   └── portfolio.json           ← 共用資料格式
├── requirements.txt
└── PortMira/                    ← macOS SwiftUI app
    ├── PortMira.xcodeproj
    └── PortMira/
        ├── Models/              ← Portfolio、Asset、Budget
        ├── Services/            ← PortfolioStore、PriceService、TechnicalIndicatorService 等
        └── Views/               ← Dashboard、Holdings、Rebalance、Scenario、News 等
```

---

## 功能

| 功能 | Web (Streamlit) | macOS (SwiftUI) |
|------|:-:|:-:|
| 總覽 Dashboard（淨資產、配置圓餅圖） | ✅ | ✅ |
| 持倉明細（可排序表格、損益、日變動）| ✅ | ✅ |
| K 線圖（3 個月 OHLCV + SMA 20/50）  | — | ✅ |
| 技術指標（RSI 14、MACD 12-26-9）    | ✅ | ✅ |
| 再平衡建議（目標比例 + 容忍帶）      | ✅ | ✅ |
| 情境分析（壓力測試 + 歷史事件 Preset）| ✅ | ✅ |
| 編輯組合（資產 + 負債 CRUD）         | ✅ | ✅ |
| 預算追蹤（類別預算 + 支出記錄）       | ✅ | ✅ |
| 歷史回測（CAGR、Max Drawdown、基準指數對比）| ✅ | ✅ |
| 財經新聞（Yahoo Finance 即時新聞）   | ✅ | ✅ |
| 幣別切換（TWD / USD）               | ✅ | ✅ |

---

## 技術棧

### Web — Python / Streamlit

| 用途 | 套件 |
|------|------|
| UI | Streamlit |
| 資料處理 | Pandas |
| 圖表 | Plotly |
| 股票 / ETF 報價 | yfinance（Yahoo Finance） |
| 加密貨幣報價 | CoinGecko API |
| 匯率 | ExchangeRate-API |
| 資料儲存 | 本機 JSON |

### macOS — Swift / SwiftUI

| 用途 | 技術 |
|------|------|
| UI 框架 | SwiftUI（macOS 15+） |
| 狀態管理 | `@Observable` + `@MainActor` |
| 圖表 | Swift Charts |
| 並發 | Swift Concurrency（actor、TaskGroup） |
| 報價 / K 線 | Yahoo Finance v8 API |
| 技術指標 | 自實作 RSI / MACD |
| 資料儲存 | 本機 JSON（Application Support sandbox） |

---

## 執行方式

### Web（Python）

```bash
pip install -r requirements.txt
streamlit run app.py
```

瀏覽器開啟 `http://localhost:8501`

### macOS App

- **需求：** macOS 15+、Xcode 16+
- 開啟 `PortMira/PortMira.xcodeproj`
- 選擇 destination 為 **My Mac**
- `Cmd + R` 執行

---

## 資料格式

兩個平台共用 `portfolio.json`，結構如下：

```json
{
  "assets": [
    {
      "id": "uuid",
      "name": "Apple Inc.",
      "category": "stock",
      "ticker": "AAPL",
      "quantity": 10,
      "cost_per_unit": 150.0,
      "currency": "USD",
      "purchase_date": "2023-01-15",
      "target_pct": 20.0
    }
  ],
  "liabilities": [],
  "scenarios": [],
  "meta": { "last_updated": "2025-05-30", "version": "0.2.0" }
}
```

資產類別（`category`）：`stock` / `stock_tw` / `etf` / `crypto` / `commodity` / `cash` / `other`

---

## 隱私

所有資料僅存於本機。無帳號、無雲端同步、不傳送任何資料至外部伺服器。報價資料來自公開 API（Yahoo Finance、CoinGecko），僅用於即時顯示，不儲存。

---

<!-- Screenshots -->

---

## Team

大學 Python 程式設計期末專案 — 4 人小組。
