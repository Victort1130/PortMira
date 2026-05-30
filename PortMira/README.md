# PortMira

> A native macOS portfolio tracker built with SwiftUI — real-time quotes, rebalancing, backtesting, scenario analysis, and more. No subscriptions, no third-party UI frameworks, no cloud dependency.

![Platform](https://img.shields.io/badge/platform-macOS-lightgrey?logo=apple)
![Swift](https://img.shields.io/badge/Swift-5.0-orange?logo=swift)
![Xcode](https://img.shields.io/badge/Xcode-16%2B-blue?logo=xcode)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Overview

PortMira lets you track every asset you own — stocks, ETFs, crypto, commodities, cash, and liabilities — in one place. It pulls live prices from Yahoo Finance, calculates your net worth across currencies, and gives you tools to analyse, stress-test, and rebalance your portfolio without ever leaving the app.

All data is stored locally as JSON. No account required.

---

## Features

### Dashboard
- Net worth, total assets, total liabilities, and portfolio CAGR at a glance
- Asset allocation donut charts by category and individual holding
- Commodities widget (Gold, WTI Crude, Silver, Natural Gas)
- Currency switcher — TWD / USD, applied instantly across all values

### Holdings
- Sortable table: price, market value, cost basis, unrealised P&L, daily change %, CAGR
- RSI (14) and MACD (12-26-9) calculated on demand with plain-language signals
- Candlestick chart sheet per holding: 3-month OHLCV, SMA 20/50 overlay, volume sub-chart
- Portfolio statistics panel
- Liabilities table with annual rate display

### Rebalance
- Set a target allocation % per asset with a configurable tolerance band (0–15%)
- Per-asset min/max overrides for finer control
- Auto-flags Buy / Hold / Sell with required trade amounts and units
- Side-by-side current vs target bar chart

### Scenario Analysis
- Slide each asset category between −100% and +100% shock
- FX rate shocks to see cross-currency impact
- Four built-in historical presets: 2008 GFC, 2020 COVID crash, 2022 rate hike bear market, 2000 dot-com bust — each with period notes and hedging commentary
- Save, load, and delete custom scenarios

### Backtest
- Pick any date range; backtests all holdings that have a ticker
- Metrics: total return, CAGR, max drawdown
- Compare against SPY, QQQ, or 0050.TW
- Cumulative return chart + per-asset ranking

### Budget Tracker
- Categories: dining, transport, subscriptions, entertainment, investment, healthcare, shopping, other
- Set a budget per category with a period (monthly / bi-weekly / weekly) and alert threshold
- Progress bars turn amber when you approach the threshold
- Full expense history with monthly/yearly grouping

### News
- Aggregates headlines for all tickers in your portfolio plus SPY, QQQ, BTC-USD, GC=F, 0050.TW
- De-duplicated, sorted by recency, with relative timestamps
- Opens source article in your default browser

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| UI | SwiftUI — `NavigationSplitView`, `Table`, `HSplitView` |
| Language | Swift 5.0 |
| State | `@Observable` + `@MainActor` (macOS 14+ Observation framework) |
| Concurrency | Swift Concurrency — `async/await`, `actor`, `withTaskGroup` |
| Charts | Swift Charts — donut, bar, line, candlestick (`RectangleMark` + `RuleMark`) |
| Prices | Yahoo Finance REST API — no API key required |
| FX Rates | ExchangeRate-API — no API key required |
| Indicators | Custom RSI (Wilder smoothing) and MACD (EMA 12-26-9) |
| Persistence | JSON files in `~/Library/Application Support/PortMira/` |

---

## Getting Started

### Requirements

| | Minimum |
|-|---------|
| macOS (run) | macOS 15 Sequoia |
| Xcode | 16.0 |
| Swift | 5.0 |
| Internet | Required for prices, FX rates, and news |

### Installation

```bash
git clone https://github.com/Victort1130/portmira.git
cd portmira
open PortMira/PortMira.xcodeproj
```

1. In Xcode, set the run destination to **My Mac**
2. Under **Signing & Capabilities**, set your Development Team
3. Press `⌘R` to build and run
4. Go to **Edit Portfolio** to add your holdings, then hit **Refresh** to fetch live prices

> Prices and rates are fetched from public Yahoo Finance and ExchangeRate-API endpoints — no API key or registration needed.

---

## Project Structure

```
PortMira/
├── PortMira.xcodeproj/
└── PortMira/
    ├── PortMiraApp.swift             # Entry point; injects PortfolioStore & BudgetStore
    ├── ContentView.swift             # NavigationSplitView sidebar & AppSection routing
    │
    ├── Models/
    │   ├── Portfolio.swift           # Asset, Liability, Scenario, Portfolio + enums
    │   ├── EnrichedAsset.swift       # Price-enriched asset, RebalanceAction, ScenarioResult
    │   └── Budget.swift              # Expense, Budget, BudgetStatus, BudgetPeriod
    │
    ├── Services/
    │   ├── PortfolioStore.swift      # @Observable global state; persistence & price refresh
    │   ├── BudgetStore.swift         # @Observable budget & expense state
    │   ├── PriceService.swift        # Yahoo Finance quotes + ExchangeRate-API FX
    │   ├── CalculationsEngine.swift  # Enrichment, net worth, rebalance, scenario, CAGR
    │   ├── BacktestEngine.swift      # actor — historical OHLCV fetch & backtest metrics
    │   ├── TechnicalIndicatorService.swift  # actor — RSI / MACD
    │   └── NewsService.swift         # actor — Yahoo Finance news aggregation & dedup
    │
    ├── Data/
    │   └── HistoricalEvents.swift    # Built-in historical scenario presets
    │
    └── Views/
        ├── Dashboard/DashboardView.swift
        ├── Holdings/
        │   ├── HoldingsView.swift
        │   ├── CandlestickView.swift
        │   └── PortfolioStatsView.swift
        ├── Rebalance/RebalanceView.swift
        ├── Scenario/ScenarioView.swift
        ├── Edit/
        │   ├── EditPortfolioView.swift
        │   ├── AssetFormView.swift
        │   └── LiabilityFormView.swift
        ├── Budget/
        │   ├── BudgetView.swift
        │   ├── BudgetSettingsView.swift
        │   └── ExpenseFormView.swift
        ├── Backtest/BacktestView.swift
        └── News/NewsView.swift
```

---

## Data Format

Portfolio data lives at `~/Library/Application Support/PortMira/portfolio.json` and is written atomically on every change.

```json
{
  "meta": { "last_updated": "2026-05-30", "version": "0.2.0" },
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
      "target_max_pct": 25.0
    }
  ],
  "liabilities": [
    {
      "id": "uuid",
      "name": "Mortgage",
      "category": "loan",
      "amount": 3000000,
      "currency": "TWD",
      "annual_rate": 0.0185
    }
  ],
  "scenarios": [
    {
      "id": "sc_abc123",
      "name": "Rate Hike",
      "created_at": "2026-05-30",
      "shocks": {
        "categories": { "stock": -0.15, "crypto": -0.30 },
        "fx": { "USD": 0.05 }
      }
    }
  ]
}
```

**Supported `category` values:** `stock` `stock_tw` `etf` `crypto` `commodity` `cash` `other`

**Supported `currency` values:** `TWD` `USD` `EUR` `JPY` `GBP`

Budget data is stored separately at `~/Library/Application Support/PortMira/budget_data.json`.

---

## Screenshots

<!-- Add screenshots here -->

---

## License

MIT License — see [LICENSE](LICENSE) for details.
