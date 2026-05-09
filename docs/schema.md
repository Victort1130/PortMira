# PortMira Portfolio Data Schema

Version: 0.1.0  
File: `data/portfolio.json` / `data/sample_portfolio.json`

---

## Top-Level Structure

```json
{
  "meta": { ... },
  "assets": [ ... ],
  "liabilities": [ ... ]
}
```

| 欄位 | 型別 | 說明 |
|---|---|---|
| `meta` | object | 檔案版本、基礎貨幣、最後更新日期 |
| `assets` | array | 所有資產項目清單 |
| `liabilities` | array | 所有負債項目清單 |

---

## meta 欄位

| 欄位 | 型別 | 說明 |
|---|---|---|
| `version` | string | Schema 版本號，例如 `"0.1.0"` |
| `base_currency` | string | 顯示用基礎貨幣，預設 `"TWD"` |
| `last_updated` | string | 最後更新日期，格式 `YYYY-MM-DD` |

---

## assets 欄位

每一筆資產為一個 object，包含以下欄位：

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `id` | string | ✅ | 唯一識別碼，例如 `"asset_001"` |
| `category` | string | ✅ | 資產類別（見下方允許值） |
| `name` | string | ✅ | 顯示名稱，例如 `"Apple Inc."` |
| `ticker` | string or null | — | 行情代碼；cash 類型設為 `null` |
| `quantity` | number | ✅ | 持有數量；cash 類型此欄位為金額 |
| `cost_per_unit` | number | ✅ | 每單位成本；cash 類型固定為 `1` |
| `currency` | string | ✅ | 貨幣代碼，例如 `"USD"`、`"TWD"` |
| `note` | string | — | 備註，可留空字串 `""` |

---

## liabilities 欄位

每一筆負債為一個 object，包含以下欄位：

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `id` | string | ✅ | 唯一識別碼，例如 `"liab_001"` |
| `category` | string | ✅ | 負債類別（見下方允許值） |
| `name` | string | ✅ | 顯示名稱，例如 `"信用卡帳單"` |
| `amount` | number | ✅ | 負債金額（正數） |
| `currency` | string | ✅ | 貨幣代碼 |
| `annual_rate` | number | — | 年利率，小數表示。例如 14.99% → `0.1499`；若無利率可設 `0` |
| `note` | string | — | 備註 |

---

## 允許的 asset category 值

| 值 | 說明 |
|---|---|
| `stock` | 美股或其他外國股票，使用 yfinance ticker |
| `stock_tw` | 台股，ticker 格式為 `2330.TW` 或 `6669.TWO` |
| `etf` | ETF，使用 yfinance ticker |
| `crypto` | 加密貨幣，ticker 使用 CoinGecko id |
| `cash` | 現金部位 |
| `other` | 債券、基金、大宗商品、手動定價資產等 |

---

## 允許的 liability category 值

| 值 | 說明 |
|---|---|
| `credit_card` | 信用卡債 |
| `loan` | 個人貸款、學貸等 |
| `margin_loan` | 融資借貸 |
| `other_liability` | 其他負債 |

---

## Ticker 規則

### 美股 / ETF
- 直接使用交易所 ticker，例如 `AAPL`、`VOO`、`TSLA`
- yfinance 可直接查詢

### 台股
- 上市股票：`{股票代號}.TW`，例如 `2330.TW`
- 上櫃股票：`{股票代號}.TWO`，例如 `6669.TWO`
- yfinance 支援度不穩定，需測試後確認

### 加密貨幣
- 使用 **CoinGecko id**，不使用縮寫代號
- ✅ 正確：`"bitcoin"`、`"ethereum"`、`"solana"`
- ❌ 錯誤：`"BTC"`、`"ETH"`、`"SOL"`
- CoinGecko id 查詢：https://api.coingecko.com/api/v3/coins/list

### 現金
- `ticker` 欄位設為 `null`
- `quantity` = 現金金額
- `cost_per_unit` = `1`

### other 類別（手動定價）
- `ticker` 可設為 `null`
- 若無自動抓價，系統將使用 `cost_per_unit` 作為當前市值估計
- 未來版本可新增 `manual_price` 欄位覆蓋

---

## 計算邏輯摘要（供 calculations.py 參考）

```
市值 (market_value)    = quantity × current_price
成本 (cost_basis)      = quantity × cost_per_unit
未實現損益 (unrealized_pl) = market_value - cost_basis
未實現損益% (unrealized_pl_pct) = unrealized_pl / cost_basis × 100

總資產 = sum(所有 asset 的 market_value，統一換算為 base_currency)
總負債 = sum(所有 liability 的 amount，統一換算為 base_currency)
淨值   = 總資產 - 總負債
```