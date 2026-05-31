# PortMira 📊

> A local-first portfolio tracker — no cloud, no account, just your data.
> 本地優先的投資組合追蹤工具：資料只存在你自己的電腦,不需註冊、不上雲。

PortMira 幫助散戶投資人把分散在多平台的資產(台股、美股、ETF、加密貨幣、大宗商品、現金)
整合到一個畫面,並提供即時報價、再平衡建議、情境壓力測試、回測、預算記帳與市場新聞。

---

## 🏛 雙架構設計 Dual Architecture

PortMira 刻意做成**兩個平台、兩套原生實作**,但**共用同一份資料模型與功能設計**。
兩端都直接讀寫同一份本地 JSON(`portfolio.json` 等),所以可以互相替換、互不依賴雲端。

| 面向 | ① Python · Streamlit(Web 版) | ② Swift · SwiftUI(macOS 原生版) |
|------|------------------------------|----------------------------------|
| **定位** | 快速開發的原型,跨平台、瀏覽器即開即用 | 原生效能、離線可用、深度系統整合體驗 |
| **技術棧** | Python · pandas · plotly · yfinance | Swift · SwiftUI · Swift Charts |
| **狀態管理** | Streamlit `session_state` + 快取 | `@Observable` 資料驅動更新 |
| **併發** | 同步 + `@st.cache_data` | `actor` isolation 確保執行緒安全 |
| **進入點** | `app.py` | `PortMira/PortMira.xcodeproj` |
| **共用核心** | 相同的 `portfolio.json` 資料格式、相同的計算邏輯(各自以該語言實作) | 同左 |

> 簡言之:**一份資料模型 × 一套功能 → 兩種原生前端**。Web 版負責快速迭代與跨平台,
> macOS 版負責原生體驗;兩者讀同一份本地資料,不互相鎖定。

---

## ✨ 功能 Features

- **總覽 Dashboard** — 淨資產、總資產/負債、CAGR、個別資產與大類資產配置圓餅圖、大宗商品即時行情
- **持倉明細 Holdings** — 即時報價、未實現損益、日變動、年化報酬;每列可快速 🗑️ 刪除
  - 組合統計:融資維持率、每月利息、夏普比率、組合 β、最大回撤、加權平均成本比
  - 技術線圖:K 線 · SMA · 布林通道 · RSI · 成交量
  - 技術指標:RSI / MACD
- **編輯組合 Edit** — 以表格新增/編輯/刪除市場型資產、手動資產與負債
- **再平衡 Rebalance** — 依目標比例與容忍帶,計算買入/賣出/持有建議
- **情境分析 Scenario** — 套用歷史重大事件或自訂漲跌/匯率衝擊,預覽淨值影響並提供避險建議
- **預算追蹤 Budget** — 記帳、信用卡/簽帳卡管理、預算與超支警示
- **回測工具 Backtest** — 以歷史價格回測組合表現,對比 SPY / QQQ / 0050.TW
- **市場資訊 News** — Fed / Yahoo Finance / CNBC / Guardian RSS + 個股新聞,含關鍵字情緒標記

---

## 🚀 快速開始 Quick Start(Python / Streamlit 版)

```bash
# 1. 安裝相依套件
pip install -r requirements.txt

# 2. 啟動 App
streamlit run app.py
```

瀏覽器會自動開啟 `http://localhost:8501`。所有資料寫入專案內的 `data/` 資料夾。

### macOS 原生版

用 Xcode 開啟 `PortMira/PortMira.xcodeproj`,選擇 macOS target 後執行(⌘R)。

---

## 🗂 專案結構 Project Structure

```
PortMira/
├── app.py                     # Streamlit 主程式(8 個分頁)
├── requirements.txt
├── src/
│   ├── models.py              # 資料模型與類別常數
│   ├── storage.py             # 本地 JSON 讀寫
│   ├── price_fetcher.py       # yfinance / CoinGecko / 匯率
│   ├── calculations.py        # 估值、淨值、再平衡、情境、融資、利息
│   ├── technical_indicators.py# RSI / MACD / 布林 / 夏普 / β
│   ├── backtest.py            # 歷史回測引擎(已含匯率換算)
│   ├── budget_calc.py         # 預算/記帳邏輯
│   ├── charts.py              # plotly 圖表
│   ├── historical_events.py   # 情境分析用歷史事件
│   └── news_fetcher.py        # RSS / 個股新聞 + 情緒標記
├── data/                      # 本地資料(portfolio/expenses/budgets/cards .json)
└── PortMira/                  # Swift / SwiftUI macOS 原生版
    └── PortMira.xcodeproj
```

## 💾 資料檔 Data Files

所有資料皆為本地 JSON,存於 `data/`:`portfolio.json`(資產/負債/情境)、
`expenses.json`、`budgets.json`、`cards.json`。

## 🔢 資料來源 Data Sources

yfinance(股票/ETF/加密貨幣/大宗商品)、CoinGecko(加密貨幣備援)、
exchangerate-api.com(匯率)、各大財經 RSS(新聞)。報價與指標僅供參考,不構成投資建議。

---

*PortMira — 程式設計期末專案*
