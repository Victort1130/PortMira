# PortMira

> A local-first portfolio tracker available as a native macOS app (SwiftUI) and a web app (Python / Streamlit) — sharing the same JSON data format and feature set.

![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Web-lightgrey?logo=apple)
![Swift](https://img.shields.io/badge/Swift-5.0-orange?logo=swift)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Architecture

PortMira ships two independent frontends that read and write the same `portfolio.json` format:

| Platform | Stack | Entry point |
|----------|-------|-------------|
| **macOS native** | SwiftUI + Swift Charts | `PortMira/PortMira.xcodeproj` |
| **Web** | Streamlit + Plotly | `app.py` |

```
PortMira/                        ← repo root
├── app.py                       ← Streamlit web app entry
├── src/                         ← Python core
│   ├── calculations.py
│   ├── price_fetcher.py
│   ├── technical_indicators.py
│   ├── backtest.py
│   ├── budget_calc.py
│   ├── news_fetcher.py
│   ├── charts.py
│   ├── historical_events.py
│   ├── models.py
│   └── storage.py
├── data/
│   └── portfolio.json           ← shared data format
├── requirements.txt
└── PortMira/                    ← macOS SwiftUI app
    ├── PortMira.xcodeproj
    └── PortMira/
        ├── Models/
        ├── Services/
        └── Views/
```

---

## Features

| Feature | Web | macOS |
|---------|:---:|:-----:|
| Dashboard — net worth, allocation donut chart | ✅ | ✅ |
| Holdings — sortable table, P&L, daily change | ✅ | ✅ |
| Candlestick chart (3-month OHLCV + SMA 20/50) | — | ✅ |
| Technical indicators — RSI 14, MACD 12-26-9 | ✅ | ✅ |
| Rebalance — target allocation + tolerance band | ✅ | ✅ |
| Scenario analysis — stress test + historical presets | ✅ | ✅ |
| Edit portfolio — asset & liability CRUD | ✅ | ✅ |
| Budget tracker — category budgets + expense log | ✅ | ✅ |
| Backtest — CAGR, max drawdown, benchmark comparison | ✅ | ✅ |
| Financial news — Yahoo Finance live feed | ✅ | ✅ |
| Currency switch — TWD / USD | ✅ | ✅ |

---

## Tech Stack

### macOS — Swift / SwiftUI

| | |
|-|-|
| UI | SwiftUI (`NavigationSplitView`, `Table`, `HSplitView`) |
| State | `@Observable` + `@MainActor` |
| Charts | Swift Charts |
| Concurrency | Swift Concurrency — `actor`, `withTaskGroup` |
| Prices & news | Yahoo Finance v8 REST API |
| Indicators | Custom RSI (Wilder) + MACD (EMA 12-26-9) |
| Storage | JSON in `~/Library/Application Support/PortMira/` |

### Web — Python / Streamlit

| | |
|-|-|
| UI | Streamlit |
| Data | Pandas |
| Charts | Plotly |
| Prices | yfinance (Yahoo Finance), CoinGecko API |
| FX rates | ExchangeRate-API |
| Storage | Local JSON |

---

## Getting Started

### macOS App

**Requirements:** macOS 15 Sequoia, Xcode 16+

```bash
git clone https://github.com/Victort1130/PortMira.git
open PortMira/PortMira.xcodeproj
```

1. Set destination to **My Mac**
2. Set your Development Team under **Signing & Capabilities**
3. Press `⌘R`

### Web App

**Requirements:** Python 3.10+

```bash
git clone https://github.com/Victort1130/PortMira.git
cd PortMira
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Data Format

Both platforms share `portfolio.json` (macOS writes to `Application Support`; the web app reads from `data/`):

```json
{
  "meta": { "last_updated": "2026-05-31", "version": "0.2.0" },
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
      "target_pct": 20.0
    }
  ],
  "liabilities": [],
  "scenarios": []
}
```

**`category`:** `stock` `stock_tw` `etf` `crypto` `commodity` `cash` `other`

**`currency`:** `TWD` `USD` `EUR` `JPY` `GBP`

---

## Privacy

All data is stored locally. No account, no cloud sync, nothing sent to external servers. Price and news data is fetched from public APIs (Yahoo Finance, CoinGecko) for display only and is never persisted remotely.

---

## Screenshots

<!-- Add screenshots here -->

---

## License

MIT License — see [LICENSE](LICENSE) for details.
