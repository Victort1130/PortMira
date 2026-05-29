import uuid
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

from src.storage import (
    load_portfolio, get_assets_df, get_liabilities_df, save_portfolio,
    get_scenarios, save_scenario, delete_scenario,
)
from src.calculations import (
    build_prices, build_prev_closes, build_fx_rates,
    enrich_assets, calc_net_worth,
    calc_portfolio_cagr, add_cagr_column,
    calc_rebalance, apply_scenario,
)
from src.charts import allocation_pie, simplified_category_pie

st.set_page_config(page_title="PortMira", page_icon="📊", layout="wide")

def fmt(value: float, currency: str) -> str:
    """Compact number format that always fits inside a metric card."""
    if currency == "TWD":
        if abs(value) >= 1_0000_0000:
            return f"{value/1_0000_0000:.2f} 億"
        if abs(value) >= 1_0000:
            return f"{value/1_0000:.1f} 萬"
        return f"{value:,.0f}"
    else:
        if abs(value) >= 1_000_000:
            return f"{value/1_000_000:.2f} M"
        if abs(value) >= 1_000:
            return f"{value/1_000:.1f} K"
        return f"{value:,.0f}"

# ── Global styles ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }

/* ── Sidebar ── */
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(180deg, #1e1b4b 0%, #312e81 100%);
    padding-top: 2rem;
}
[data-testid="stSidebar"] h1 { color: #fff !important; font-weight: 800; font-size: 1.5rem; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span { color: rgba(255,255,255,0.85) !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15) !important; margin: 1rem 0 !important; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    color: #fff !important;
    border-radius: 8px;
    font-weight: 600;
    transition: background 0.2s;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.22) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] > label { color: rgba(255,255,255,0.6) !important; font-size: 0.75rem; }

/* ── Main area ── */
.main .block-container { padding-top: 1.5rem; }

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
    transition: box-shadow 0.2s;
}
[data-testid="metric-container"]:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.09); }
[data-testid="stMetricLabel"]  { font-size: 0.78rem !important; font-weight: 600 !important; color: #64748b !important; text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricValue"]  { font-size: 1.75rem !important; font-weight: 800 !important; color: #0f172a !important; line-height: 1.2; }
[data-testid="stMetricDelta"]  { font-size: 0.82rem !important; font-weight: 600 !important; }
[data-testid="stMetricDelta"] svg { display: none; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { gap: 2px; border-bottom: 2px solid #e2e8f0; }
.stTabs [data-baseweb="tab"] {
    padding: 0.6rem 1.1rem;
    border-radius: 8px 8px 0 0;
    font-weight: 600;
    font-size: 0.88rem;
    color: #64748b;
    background: transparent;
}
.stTabs [aria-selected="true"] { color: #4f46e5 !important; background: #eef2ff !important; }

/* ── Section headings ── */
h2, h3 { color: #0f172a !important; font-weight: 700 !important; }
.stSubheader { margin-top: 0.5rem; }

/* ── Divider ── */
hr { border-color: #e2e8f0 !important; margin: 1.25rem 0 !important; }

/* ── Dataframe ── */
.stDataFrame { border-radius: 12px; overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,0.05); }

/* ── Buttons ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.5rem !important;
    box-shadow: 0 2px 8px rgba(79,70,229,0.3) !important;
}
.stButton > button[kind="primary"]:hover { opacity: 0.92 !important; }

/* ── Hero card ── */
.hero-card {
    background: linear-gradient(135deg, #4338ca 0%, #6d28d9 100%);
    border-radius: 20px;
    padding: 1.75rem 2.25rem;
    color: #fff;
    box-shadow: 0 8px 32px rgba(79,70,229,0.22);
    margin-bottom: 0.25rem;
}
.hero-label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.75; font-weight: 600; }
.hero-value { font-size: 2.6rem; font-weight: 900; line-height: 1.1; margin: 0.3rem 0; }
.hero-sub   { font-size: 0.82rem; opacity: 0.65; }
.hero-delta { font-size: 0.88rem; margin-top: 0.5rem; font-weight: 600; }
.hero-delta.pos { color: #6ee7b7; }
.hero-delta.neg { color: #fca5a5; }

/* ── Chart card ── */
.chart-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 1.25rem 1.25rem 0.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.chart-title { font-size: 0.8rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 0.25rem; }
</style>
""", unsafe_allow_html=True)

ASSET_CATEGORIES = ["stock", "stock_tw", "etf", "crypto", "commodity", "cash", "other"]
LIAB_CATEGORIES  = ["credit_card", "loan", "margin_loan", "other_liability"]
CURRENCIES       = ["TWD", "USD", "EUR", "JPY", "GBP"]

_MARKET_CATS = ["stock", "stock_tw", "etf", "crypto", "commodity"]
_MANUAL_CATS = ["cash", "other"]
_MARKET_COLS = ["name", "category", "ticker", "quantity", "cost_per_unit",
                "currency", "purchase_date", "target_pct", "target_min_pct", "target_max_pct", "note"]
_MANUAL_COLS = ["name", "category", "quantity", "cost_per_unit",
                "currency", "purchase_date", "target_pct", "note"]
_LIAB_COLS   = ["name", "category", "amount", "currency", "annual_rate", "note"]

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("PortMira")
    st.caption("Local-first portfolio tracker")
    st.markdown("---")
    display_currency = st.radio("Display Currency", ["TWD", "USD"], horizontal=True)
    st.markdown("---")
    if st.button("🔄 Refresh Prices", use_container_width=True):
        st.cache_data.clear()
        st.session_state.pop("commodity_prices", None)
        st.rerun()
    st.markdown("---")
    st.caption("v0.2.0 · local-first")

# ── Cached price fetching ──────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_and_enrich(base_currency: str):
    portfolio      = load_portfolio()
    assets_df      = get_assets_df(portfolio)
    liabilities_df = get_liabilities_df(portfolio)

    if assets_df.empty:
        return None, None, None, None, None, {}

    prices      = build_prices(assets_df)
    prev_closes = build_prev_closes(assets_df)
    fx_rates    = build_fx_rates(assets_df, liabilities_df, base_currency)
    enriched_df = enrich_assets(assets_df, prices, fx_rates, base_currency, prev_closes)
    enriched_df = add_cagr_column(enriched_df)
    total_assets, total_liabilities, net_worth = calc_net_worth(
        enriched_df, liabilities_df, fx_rates
    )
    return enriched_df, liabilities_df, total_assets, total_liabilities, net_worth, fx_rates


with st.spinner("Fetching latest prices…"):
    enriched_df, liabilities_df, total_assets, total_liabilities, net_worth, fx_rates = (
        load_and_enrich(display_currency)
    )

portfolio          = load_portfolio()
raw_liabilities_df = get_liabilities_df(portfolio)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_dashboard, tab_edit, tab_holdings, tab_rebalance, tab_scenario, tab_budget, tab_backtest, tab_news = st.tabs([
    "📊 總覽", "✏️ 編輯組合", "📋 持倉明細", "⚖️ 再平衡", "🔮 情境分析", "💰 預算追蹤", "📈 回測工具", "📰 市場資訊",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Dashboard
# ══════════════════════════════════════════════════════════════════════════════
with tab_dashboard:

    if enriched_df is None or enriched_df.empty:
        st.info("📂 尚未有資產資料。請前往「✏️ 編輯組合」頁面新增您的資產。")
    else:
        portfolio_cagr = calc_portfolio_cagr(enriched_df)

        # ── Hero: Net Worth ───────────────────────────────────────────────────
        st.markdown(f"""
<div class="hero-card">
    <div class="hero-label">💼 淨資產 Net Worth</div>
    <div class="hero-value">{display_currency} {fmt(net_worth, display_currency)}</div>
    <div class="hero-sub">資產 {fmt(total_assets, display_currency)} &nbsp;−&nbsp; 負債 {fmt(total_liabilities, display_currency)} &nbsp;({display_currency})</div>
</div>
""", unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # ── Metric row ────────────────────────────────────────────────────────
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "📈 總資產",
                f"{display_currency} {fmt(total_assets, display_currency)}",
            )
        with col2:
            st.metric(
                "📉 總負債",
                f"{display_currency} {fmt(total_liabilities, display_currency)}",
            )
        with col3:
            if portfolio_cagr is not None:
                cagr_pct = portfolio_cagr * 100
                st.metric(
                    "📅 年化報酬率 CAGR",
                    f"{cagr_pct:+.2f}%",
                    delta="since earliest purchase",
                    delta_color="off",
                )
            else:
                st.metric(
                    "📅 年化報酬率 CAGR", "—",
                    help="請為資產設定 Purchase Date 以計算年化報酬率",
                )
        with col4:
            n_assets = len(enriched_df)
            st.metric("🗂 持有資產", f"{n_assets} 項")

        st.divider()

        # ── Charts ────────────────────────────────────────────────────────────
        pie_left, pie_right = st.columns(2)

        with pie_left:
            st.markdown('<div class="chart-card"><div class="chart-title">個別資產配置</div>', unsafe_allow_html=True)
            pie_fig, pie_summary = allocation_pie(enriched_df, display_currency)
            st.plotly_chart(pie_fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

        with pie_right:
            st.markdown('<div class="chart-card"><div class="chart-title">資產大類佔比</div>', unsafe_allow_html=True)
            st.plotly_chart(
                simplified_category_pie(enriched_df, display_currency),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            st.markdown('</div>', unsafe_allow_html=True)

        st.divider()

        # ── Commodity Market Prices ───────────────────────────────────────────
        st.markdown("### 🏅 大宗商品行情")
        st.caption("主要大宗商品即時報價（USD）")

        _MARKET_COMMODITIES = {
            "GC=F": "黃金",
            "CL=F": "WTI原油",
            "SI=F": "白銀",
            "NG=F": "天然氣",
        }

        if "commodity_prices" not in st.session_state:
            import yfinance as _yf_comm
            try:
                _comm_raw = _yf_comm.download(
                    list(_MARKET_COMMODITIES.keys()),
                    period="2d",
                    auto_adjust=True,
                    progress=False,
                )
                st.session_state["commodity_prices"] = _comm_raw
            except Exception:
                st.session_state["commodity_prices"] = None

        _comm_data = st.session_state.get("commodity_prices")
        _comm_cols = st.columns(4)
        for _ci, (_sym, _cname) in enumerate(_MARKET_COMMODITIES.items()):
            with _comm_cols[_ci]:
                try:
                    if _comm_data is not None and not _comm_data.empty and "Close" in _comm_data.columns:
                        _close_col = _comm_data["Close"]
                        if hasattr(_close_col, "columns") and _sym in _close_col.columns:
                            _series = _close_col[_sym].dropna()
                        elif not hasattr(_close_col, "columns"):
                            # Single ticker fallback
                            _series = _close_col.dropna()
                        else:
                            _series = pd.Series(dtype=float)
                        if len(_series) >= 2:
                            _cur_price = float(_series.iloc[-1])
                            _prev_price = float(_series.iloc[-2])
                            _delta_pct = (_cur_price - _prev_price) / _prev_price * 100
                            st.metric(
                                label=f"{_cname} ({_sym})",
                                value=f"${_cur_price:,.2f}",
                                delta=f"{_delta_pct:+.2f}%",
                            )
                        elif len(_series) == 1:
                            st.metric(
                                label=f"{_cname} ({_sym})",
                                value=f"${float(_series.iloc[-1]):,.2f}",
                            )
                        else:
                            st.metric(label=f"{_cname} ({_sym})", value="—")
                    else:
                        st.metric(label=f"{_cname} ({_sym})", value="—")
                except Exception:
                    st.metric(label=f"{_cname} ({_sym})", value="—")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Edit Portfolio
# ══════════════════════════════════════════════════════════════════════════════
with tab_edit:

    def _prep_df(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=cols)
        for c in cols:
            if c not in df.columns:
                df = df.copy()
                df[c] = None
        return df[[c for c in cols if c in df.columns]].copy()

    if "edit_market_df" not in st.session_state:
        _raw        = load_portfolio()
        _raw_assets = get_assets_df(_raw)
        _raw_liabs  = get_liabilities_df(_raw)

        if not _raw_assets.empty:
            _market = _raw_assets[_raw_assets["category"].isin(_MARKET_CATS)]
            _manual = _raw_assets[_raw_assets["category"].isin(_MANUAL_CATS)]
        else:
            _market = pd.DataFrame(columns=_MARKET_COLS)
            _manual = pd.DataFrame(columns=_MANUAL_COLS)

        st.session_state["edit_market_df"] = _prep_df(_market, _MARKET_COLS)
        st.session_state["edit_manual_df"] = _prep_df(_manual, _MANUAL_COLS)
        st.session_state["edit_liab_df"]   = (
            _raw_liabs[[c for c in _LIAB_COLS if c in _raw_liabs.columns]].copy()
            if _raw_liabs is not None and not _raw_liabs.empty
            else pd.DataFrame(columns=_LIAB_COLS)
        )

    st.subheader("市場型資產  Market Assets")
    st.caption("Stocks · ETFs · Crypto · Commodities — prices fetched automatically via yfinance.")
    with st.expander("📖 Ticker 格式參考", expanded=False):
        st.markdown(
            "| 類型 | 範例 |\n"
            "|------|------|\n"
            "| 台股 | `2330.TW`、`0050.TW` |\n"
            "| 美股 / ETF | `AAPL`、`SPY`、`QQQ` |\n"
            "| 加密貨幣 | `BTC-USD`、`ETH-USD`、`SOL-USD`、`BNB-USD` |\n"
            "| 黃金 / 原油 | `GC=F`、`CL=F`、`SI=F`、`NG=F` |\n"
        )

    edited_market = st.data_editor(
        st.session_state["edit_market_df"],
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="market_assets_editor",
        column_config={
            "name":          st.column_config.TextColumn("Name", required=True),
            "category":      st.column_config.SelectboxColumn("Category", options=_MARKET_CATS, required=True),
            "ticker":        st.column_config.TextColumn("Ticker", required=True),
            "quantity":      st.column_config.NumberColumn("Quantity", min_value=0, step=1e-8, format="%.8g"),
            "cost_per_unit": st.column_config.NumberColumn("Cost / Unit", min_value=0, step=1e-8, format="%.8g"),
            "currency":      st.column_config.SelectboxColumn("Currency", options=CURRENCIES, required=True),
            "purchase_date": st.column_config.DateColumn("Purchase Date", format="YYYY-MM-DD"),
            "target_pct":     st.column_config.NumberColumn("Target %", min_value=0, max_value=100,
                                                             help="再平衡目標比例（0–100）"),
            "target_min_pct": st.column_config.NumberColumn("Min %", min_value=0, max_value=100,
                                                             help="允許的最低佔比，空白則用全局容忍帶"),
            "target_max_pct": st.column_config.NumberColumn("Max %", min_value=0, max_value=100,
                                                             help="允許的最高佔比，空白則用全局容忍帶"),
            "note":           st.column_config.TextColumn("Note"),
        },
    )
    if st.button("＋ 新增市場資產行", key="add_market_row"):
        st.session_state["edit_market_df"] = pd.concat(
            [edited_market, pd.DataFrame([{col: None for col in _MARKET_COLS}])],
            ignore_index=True,
        )
        st.rerun()

    st.markdown("---")

    st.subheader("手動資產  Manual Assets")
    st.caption("Cash · Other — enter value manually.")

    edited_manual = st.data_editor(
        st.session_state["edit_manual_df"],
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="manual_assets_editor",
        column_config={
            "name":          st.column_config.TextColumn("Name", required=True),
            "category":      st.column_config.SelectboxColumn("Category", options=_MANUAL_CATS, required=True),
            "quantity":      st.column_config.NumberColumn("Quantity / Amount", min_value=0, step=1e-8, format="%.8g"),
            "cost_per_unit": st.column_config.NumberColumn("Cost / Unit", min_value=0, step=1e-8, format="%.8g"),
            "currency":      st.column_config.SelectboxColumn("Currency", options=CURRENCIES, required=True),
            "purchase_date": st.column_config.DateColumn("Purchase Date", format="YYYY-MM-DD"),
            "target_pct":    st.column_config.NumberColumn("Target %", min_value=0, max_value=100),
            "note":          st.column_config.TextColumn("Note"),
        },
    )
    if st.button("＋ 新增手動資產行", key="add_manual_row"):
        st.session_state["edit_manual_df"] = pd.concat(
            [edited_manual, pd.DataFrame([{col: None for col in _MANUAL_COLS}])],
            ignore_index=True,
        )
        st.rerun()

    st.markdown("---")

    st.subheader("負債  Liabilities")

    edited_liabilities = st.data_editor(
        st.session_state["edit_liab_df"],
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="liab_editor",
        column_config={
            "name":        st.column_config.TextColumn("Name", required=True),
            "category":    st.column_config.SelectboxColumn("Category", options=LIAB_CATEGORIES),
            "amount":      st.column_config.NumberColumn("Amount", min_value=0),
            "currency":    st.column_config.SelectboxColumn("Currency", options=CURRENCIES),
            "annual_rate": st.column_config.NumberColumn("Annual Rate (e.g. 0.05 = 5%)",
                                                          min_value=0.0, max_value=1.0),
            "note":        st.column_config.TextColumn("Note"),
        },
    )
    if st.button("＋ 新增負債行", key="add_liab_row"):
        st.session_state["edit_liab_df"] = pd.concat(
            [edited_liabilities, pd.DataFrame([{col: None for col in _LIAB_COLS}])],
            ignore_index=True,
        )
        st.rerun()

    st.markdown("---")

    col_save, _ = st.columns([1, 3])
    with col_save:
        save_clicked = st.button("💾 Save Portfolio", type="primary", use_container_width=True)

    if save_clicked:
        asset_records = []

        for _, row in edited_market.iterrows():
            name   = row.get("name")
            ticker = row.get("ticker")
            if pd.isna(name) or name == "":
                if pd.isna(ticker) or ticker == "":
                    continue
                row = row.copy()
                row["name"] = ticker
            rec = row.where(pd.notna(row), other=None).to_dict()
            if not rec.get("cost_per_unit"):
                rec["cost_per_unit"] = 0
            if rec.get("purchase_date") and not isinstance(rec["purchase_date"], str):
                rec["purchase_date"] = str(rec["purchase_date"])
            rec["id"] = f"asset_{len(asset_records)+1:03d}"
            asset_records.append(rec)

        manual_rows = edited_manual[edited_manual["name"].notna() & (edited_manual["name"] != "")]
        # Only flag rows that have some meaningful data but are missing a name
        _meaningful_manual = edited_manual.dropna(subset=["name", "quantity", "cost_per_unit"], how="all")
        _missing_names = _meaningful_manual["name"].isna().sum() + (
            (_meaningful_manual["name"] == "").sum()
            if _meaningful_manual["name"].dtype == object else 0
        )
        if _missing_names > 0:
            st.warning("手動資產的「名稱」為必填欄位，請補齊後再儲存。")
            st.stop()

        for _, row in manual_rows.iterrows():
            row = row.copy()
            if row.get("category") == "cash" and (
                pd.isna(row.get("cost_per_unit")) or row.get("cost_per_unit") == 0
            ):
                row["cost_per_unit"] = 1.0
            rec = row.where(pd.notna(row), other=None).to_dict()
            if rec.get("purchase_date") and not isinstance(rec["purchase_date"], str):
                rec["purchase_date"] = str(rec["purchase_date"])
            rec["id"]     = f"asset_{len(asset_records)+1:03d}"
            rec["ticker"] = None
            asset_records.append(rec)

        liab_records = []
        for _, row in edited_liabilities.dropna(subset=["name"]).iterrows():
            rec = row.where(pd.notna(row), other=None).to_dict()
            rec["id"] = f"liab_{len(liab_records)+1:03d}"
            liab_records.append(rec)

        portfolio["assets"]               = asset_records
        portfolio["liabilities"]          = liab_records
        portfolio["meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")

        save_portfolio(portfolio)
        for k in ["edit_market_df", "edit_manual_df", "edit_liab_df"]:
            del st.session_state[k]
        st.cache_data.clear()

        st.success("✅ Portfolio saved! Switch to Dashboard to see updated data.")
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — 持倉明細
# ══════════════════════════════════════════════════════════════════════════════
with tab_holdings:

    if enriched_df is None or enriched_df.empty:
        st.info("📂 尚未有資產資料。請前往「✏️ 編輯組合」新增資產。")
    else:
        show_cagr = st.toggle("顯示年化報酬率 CAGR", value=False)

        _display_cols = [
            "name", "ticker", "category", "quantity",
            "current_price", "cost_per_unit",
            "market_value", "cost_basis",
            "unrealized_pl", "unrealized_pl_pct",
            "daily_change_pct",
        ]
        if show_cagr and "cagr" in enriched_df.columns:
            _display_cols.append("cagr")

        _available  = [c for c in _display_cols if c in enriched_df.columns]
        _display_df = enriched_df[_available].copy()

        for _col in ["market_value", "cost_basis", "unrealized_pl", "unrealized_pl_pct",
                     "current_price", "cost_per_unit", "daily_change_pct"]:
            if _col in _display_df.columns:
                _display_df[_col] = pd.to_numeric(_display_df[_col], errors="coerce")

        for _col in ["market_value", "cost_basis", "unrealized_pl", "current_price", "cost_per_unit"]:
            if _col in _display_df.columns:
                _display_df[_col] = _display_df[_col].apply(
                    lambda x: f"{x:,.1f}" if pd.notna(x) else ""
                )

        col_config = {
            "name":              st.column_config.TextColumn("資產名稱"),
            "ticker":            st.column_config.TextColumn("代號"),
            "category":          st.column_config.TextColumn("類別"),
            "quantity":          st.column_config.NumberColumn("數量", format="%.4g"),
            "current_price":     st.column_config.TextColumn("現價"),
            "cost_per_unit":     st.column_config.TextColumn("成本/單位"),
            "market_value":      st.column_config.TextColumn(f"市值 ({display_currency})"),
            "cost_basis":        st.column_config.TextColumn(f"總成本 ({display_currency})"),
            "unrealized_pl":     st.column_config.TextColumn(f"未實現損益 ({display_currency})"),
            "unrealized_pl_pct": st.column_config.NumberColumn("損益%",  format="%+.2f%%"),
            "daily_change_pct":  st.column_config.NumberColumn("日變動%", format="%+.2f%%"),
        }
        if show_cagr and "cagr" in _display_df.columns:
            _display_df["cagr"] = pd.to_numeric(_display_df["cagr"], errors="coerce") * 100
            col_config["cagr"]  = st.column_config.NumberColumn("年化報酬 CAGR", format="%+.2f%%")

        st.dataframe(
            _display_df, column_config=col_config,
            use_container_width=True, hide_index=True,
        )

        st.divider()

        # ── Technical Indicators ─────────────────────────────────────────────
        with st.expander("📈 技術指標（RSI / MACD）", expanded=False):
            st.caption("數值僅供參考，不構成買賣建議。RSI 基於 14 日，MACD 基於 12/26/9 EMA。")

            if st.button("載入技術指標", key="load_indicators"):
                from src.technical_indicators import fetch_indicators_batch
                with st.spinner("計算中..."):
                    _assets = portfolio.get("assets", [])
                    st.session_state["tech_indicators"] = fetch_indicators_batch(_assets)

            _indicators = st.session_state.get("tech_indicators", {})
            if _indicators:
                _ind_rows = []
                for a in portfolio.get("assets", []):
                    ind = _indicators.get(a["id"])
                    if ind:
                        _ind_rows.append({
                            "名稱": a["name"],
                            "RSI (14)": f"{ind['rsi']}" if ind["rsi"] is not None else "—",
                            "RSI 狀態": ind["rsi_ctx"] or "—",
                            "MACD": f"{ind['macd']:.4f}" if ind["macd"] is not None else "—",
                            "MACD 狀態": ind["macd_ctx"] or "—",
                        })
                if _ind_rows:
                    st.dataframe(pd.DataFrame(_ind_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("持倉中沒有可計算技術指標的資產（需要股票、ETF 或加密貨幣代碼）")

        if raw_liabilities_df is not None and not raw_liabilities_df.empty:
            st.divider()
            st.subheader("負債明細")
            st.dataframe(raw_liabilities_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — 再平衡引擎
# ══════════════════════════════════════════════════════════════════════════════
with tab_rebalance:

    if enriched_df is None or enriched_df.empty:
        st.info("📂 尚未有資產資料。請先新增資產並 Refresh。")
    else:
        has_targets = (
            "target_pct" in enriched_df.columns
            and pd.to_numeric(enriched_df["target_pct"], errors="coerce").notna().any()
        )

        if not has_targets:
            st.info(
                "尚未設定目標比例。\n\n"
                "請前往「✏️ 編輯組合」，在各資產的 **Target %** 欄位填入目標配置百分比。"
            )
        else:
            _tolerance = st.slider(
                "容忍帶 Tolerance", min_value=0, max_value=15, value=5, step=1,
                format="±%d%%",
                help="目前佔比在目標 ± 此值內時顯示「持有 Hold」，不需操作",
                key="rebalance_tolerance",
            )
            rebalance_df = calc_rebalance(enriched_df, tolerance_pct=float(_tolerance))
            total_value  = float(enriched_df["market_value"].sum())
            total_target = float(
                pd.to_numeric(enriched_df["target_pct"], errors="coerce").fillna(0).sum()
            )
            n_actions = (
                len(rebalance_df[rebalance_df["action"] != "持有 Hold"])
                if not rebalance_df.empty else 0
            )

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("組合總市值", f"{display_currency} {fmt(total_value, display_currency)}")
            with c2:
                diff = 100 - total_target
                st.metric(
                    "目標比例合計",
                    f"{total_target:.1f}%",
                    delta="✓ 合計 100%" if abs(diff) < 0.1 else f"差 {diff:+.1f}%",
                    delta_color="normal" if abs(diff) < 0.1 else "inverse",
                )
            with c3:
                st.metric("需要操作", f"{n_actions} 筆", help="需要買入或賣出的資產數")

            st.divider()

            if not rebalance_df.empty:
                st.subheader("操作建議")
                st.caption("按調整幅度排序，優先處理偏差最大的資產。")

                _rb = rebalance_df.copy()
                _rb["current_pct"] = _rb["current_pct"].apply(lambda x: f"{x:.1f}%")
                _rb["target_pct"]  = _rb["target_pct"].apply(lambda x: f"{x:.1f}%")
                _rb["delta_value"] = _rb["delta_value"].apply(
                    lambda x: f"{x:+,.0f} {display_currency}"
                )
                _rb["delta_units"] = _rb["delta_units"].apply(
                    lambda x: f"{x:+.4g}" if pd.notna(x) else "—"
                )
                _rb["market_value"] = _rb["market_value"].apply(lambda x: f"{x:,.0f}")

                st.dataframe(
                    _rb,
                    column_config={
                        "name":         st.column_config.TextColumn("資產名稱"),
                        "ticker":       st.column_config.TextColumn("代號"),
                        "category":     st.column_config.TextColumn("類別"),
                        "market_value": st.column_config.TextColumn(f"現值 ({display_currency})"),
                        "current_pct":  st.column_config.TextColumn("目前佔比"),
                        "target_pct":   st.column_config.TextColumn("目標佔比"),
                        "target_range": st.column_config.TextColumn("允許範圍"),
                        "delta_value":  st.column_config.TextColumn("調整金額"),
                        "delta_units":  st.column_config.TextColumn("調整數量"),
                        "action":       st.column_config.TextColumn("操作"),
                    },
                    use_container_width=True,
                    hide_index=True,
                )

                st.divider()
                st.subheader("目前 vs 目標配置")

                fig_rb = go.Figure(data=[
                    go.Bar(
                        name="目前配置",
                        x=rebalance_df["name"].tolist(),
                        y=rebalance_df["current_pct"].tolist(),
                        marker_color="#cbd5e1",
                        marker_line_color="#94a3b8",
                        marker_line_width=1,
                    ),
                    go.Bar(
                        name="目標配置",
                        x=rebalance_df["name"].tolist(),
                        y=rebalance_df["target_pct"].tolist(),
                        marker_color="#4f46e5",
                        marker_line_color="#4338ca",
                        marker_line_width=1,
                    ),
                ])
                fig_rb.update_layout(
                    barmode="group",
                    yaxis_title="佔比 (%)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter, system-ui, sans-serif", color="#374151"),
                    legend=dict(orientation="h", y=1.08, x=0, bgcolor="rgba(0,0,0,0)"),
                    margin=dict(t=10, b=40, l=40, r=20),
                    yaxis=dict(gridcolor="#f1f5f9", zeroline=False),
                    xaxis=dict(tickfont=dict(size=11)),
                    bargap=0.25,
                    bargroupgap=0.08,
                )
                st.plotly_chart(fig_rb, use_container_width=True, config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — 情境分析
# ══════════════════════════════════════════════════════════════════════════════
with tab_scenario:

    if enriched_df is None or enriched_df.empty:
        st.info("📂 尚未有資產資料。請先新增資產並 Refresh。")
    else:
        portfolio_sc = load_portfolio()
        scenarios    = get_scenarios(portfolio_sc)

        ctrl_col, result_col = st.columns([1, 1.6])

        with ctrl_col:
            from src.historical_events import HISTORICAL_EVENTS

            st.subheader("📚 歷史重大事件")
            _event_options = {v["name"]: k for k, v in HISTORICAL_EVENTS.items()}
            _selected_event_name = st.selectbox("選擇歷史重大事件", list(_event_options.keys()), key="selected_historical_event")
            _selected_event_key  = _event_options[_selected_event_name]
            _event = HISTORICAL_EVENTS[_selected_event_key]

            # Only apply preset values when the selection CHANGES (not on every rerun)
            if _selected_event_key != st.session_state.get("_applied_event_key", "__unset__"):
                if _selected_event_key:
                    for _cat, _shock in _event["shocks"]["categories"].items():
                        _sk = f"shock_{_cat}"
                        if _sk in ["shock_stock", "shock_stock_tw", "shock_etf", "shock_crypto", "shock_commodity", "shock_other"]:
                            st.session_state[_sk] = int(round(_shock * 100))
                    for _cur, _shock in _event["shocks"]["fx"].items():
                        _fk = f"fx_{_cur}"
                        if _fk in ["fx_USD", "fx_EUR", "fx_JPY"]:
                            st.session_state[_fk] = int(round(_shock * 100))
                st.session_state["_applied_event_key"] = _selected_event_key

            if _selected_event_key:
                st.caption(f"📅 {_event['period']} — {_event['description']}")
                with st.expander("💡 避險建議", expanded=True):
                    for _tip in _event["hedging"]:
                        st.markdown(f"• {_tip}")

            st.divider()

            st.subheader("設定情境變數")

            loaded_cat: dict  = {}
            loaded_fx:  dict  = {}
            selected_id: str | None = None

            if scenarios:
                sc_options    = ["（新情境）"] + [s["name"] for s in scenarios]
                selected_name = st.selectbox("載入已儲存情境", sc_options)
                if selected_name != "（新情境）":
                    loaded_sc   = next(s for s in scenarios if s["name"] == selected_name)
                    selected_id = loaded_sc["id"]
                    loaded_cat  = loaded_sc.get("shocks", {}).get("categories", {})
                    loaded_fx   = loaded_sc.get("shocks", {}).get("fx", {})
                    # Write to session_state when scenario changes so keyed sliders update
                    if selected_name != st.session_state.get("_applied_scenario_name", "__unset__"):
                        st.session_state["shock_stock"]     = int(round(loaded_cat.get("stock",     0) * 100))
                        st.session_state["shock_stock_tw"]  = int(round(loaded_cat.get("stock_tw",  0) * 100))
                        st.session_state["shock_etf"]       = int(round(loaded_cat.get("etf",       0) * 100))
                        st.session_state["shock_crypto"]    = int(round(loaded_cat.get("crypto",    0) * 100))
                        st.session_state["shock_commodity"] = int(round(loaded_cat.get("commodity", 0) * 100))
                        st.session_state["shock_other"]     = int(round(loaded_cat.get("other",     0) * 100))
                        st.session_state["fx_USD"]          = int(round(loaded_fx.get("USD", 0) * 100))
                        st.session_state["fx_EUR"]          = int(round(loaded_fx.get("EUR", 0) * 100))
                        st.session_state["fx_JPY"]          = int(round(loaded_fx.get("JPY", 0) * 100))
                        st.session_state["_applied_scenario_name"] = selected_name
                        # Mark the current event as already applied so the preset
                        # block won't overwrite the just-loaded scenario on next rerun
                        st.session_state["_applied_event_key"] = _selected_event_key

            st.caption("資產類別漲跌幅")
            shock_stock     = st.slider("股票 Stock",           -100, 100, int(loaded_cat.get("stock",     0)*100), step=1, format="%d%%", key="shock_stock")     / 100
            shock_stock_tw  = st.slider("台股 TW Stock",        -100, 100, int(loaded_cat.get("stock_tw",  0)*100), step=1, format="%d%%", key="shock_stock_tw")  / 100
            shock_etf       = st.slider("ETF",                  -100, 100, int(loaded_cat.get("etf",       0)*100), step=1, format="%d%%", key="shock_etf")       / 100
            shock_crypto    = st.slider("加密貨幣 Crypto",      -100, 100, int(loaded_cat.get("crypto",    0)*100), step=1, format="%d%%", key="shock_crypto")    / 100
            shock_commodity = st.slider("大宗商品 Commodity",   -100, 100, int(loaded_cat.get("commodity", 0)*100), step=1, format="%d%%", key="shock_commodity") / 100
            shock_other     = st.slider("其他 Other",           -100, 100, int(loaded_cat.get("other",     0)*100), step=1, format="%d%%", key="shock_other")     / 100

            st.caption("匯率變動（正 = 外幣升值）")
            fx_usd = st.slider("USD", -30, 30, int(loaded_fx.get("USD", 0)*100), step=1, format="%d%%", key="fx_USD") / 100
            fx_eur = st.slider("EUR", -30, 30, int(loaded_fx.get("EUR", 0)*100), step=1, format="%d%%", key="fx_EUR") / 100
            fx_jpy = st.slider("JPY", -30, 30, int(loaded_fx.get("JPY", 0)*100), step=1, format="%d%%", key="fx_JPY") / 100

            st.markdown("---")
            sc_name_input = st.text_input("情境名稱", placeholder="例：熊市、升息循環")
            save_c, del_c = st.columns(2)
            with save_c:
                if st.button("💾 儲存", type="primary", disabled=not sc_name_input, use_container_width=True):
                    new_sc = {
                        "id":         f"sc_{uuid.uuid4().hex[:8]}",
                        "name":       sc_name_input,
                        "created_at": date.today().isoformat(),
                        "shocks": {
                            "categories": {
                                "stock": shock_stock, "stock_tw": shock_stock_tw,
                                "etf": shock_etf, "crypto": shock_crypto,
                                "commodity": shock_commodity, "other": shock_other,
                            },
                            "fx": {"USD": fx_usd, "EUR": fx_eur, "JPY": fx_jpy},
                        },
                    }
                    save_scenario(portfolio_sc, new_sc)
                    st.success(f"「{sc_name_input}」已儲存")
                    st.rerun()
            with del_c:
                if selected_id and st.button("🗑️ 刪除", use_container_width=True):
                    delete_scenario(portfolio_sc, selected_id)
                    st.rerun()

        with result_col:
            category_shocks = {
                "stock": shock_stock, "stock_tw": shock_stock_tw,
                "etf": shock_etf, "crypto": shock_crypto,
                "commodity": shock_commodity, "other": shock_other,
            }
            fx_shock_map = {"USD": fx_usd, "EUR": fx_eur, "JPY": fx_jpy}

            scenario_df, s_assets, s_liab, s_networth = apply_scenario(
                enriched_df, liabilities_df, fx_rates,
                category_shocks, fx_shock_map,
            )

            st.subheader("模擬結果")

            nw_delta   = s_networth - net_worth
            mv_delta   = s_assets   - total_assets
            pct_chg    = nw_delta / abs(net_worth) * 100 if net_worth else 0

            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric(
                    "情境淨資產",
                    f"{display_currency} {fmt(s_networth, display_currency)}",
                    delta=f"{fmt(nw_delta, display_currency)} ({'+' if nw_delta >= 0 else ''}{nw_delta/abs(net_worth)*100:.1f}%)" if net_worth else None,
                    delta_color="normal",
                )
            with m2:
                st.metric(
                    "情境總資產",
                    f"{display_currency} {fmt(s_assets, display_currency)}",
                    delta=f"{fmt(mv_delta, display_currency)}",
                    delta_color="normal",
                )
            with m3:
                st.metric(
                    "淨資產變動幅度",
                    f"{pct_chg:+.2f}%",
                    delta_color="off",
                )

            st.divider()
            st.caption("各資產情境影響")

            _impact = scenario_df[["name", "ticker", "category", "market_value", "scenario_value"]].copy()
            _impact["impact"]     = _impact["scenario_value"] - _impact["market_value"]
            _impact["impact_pct"] = (
                _impact["impact"]
                / _impact["market_value"].replace(0, float("nan"))
                * 100
            )
            for _c in ["market_value", "scenario_value", "impact"]:
                _impact[_c] = _impact[_c].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "—")

            st.dataframe(
                _impact,
                column_config={
                    "name":           st.column_config.TextColumn("資產名稱"),
                    "ticker":         st.column_config.TextColumn("代號"),
                    "category":       st.column_config.TextColumn("類別"),
                    "market_value":   st.column_config.TextColumn(f"現值 ({display_currency})"),
                    "scenario_value": st.column_config.TextColumn(f"情境市值 ({display_currency})"),
                    "impact":         st.column_config.TextColumn(f"影響 ({display_currency})"),
                    "impact_pct":     st.column_config.NumberColumn("影響%", format="%+.1f%%"),
                },
                use_container_width=True,
                hide_index=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — 預算追蹤
# ══════════════════════════════════════════════════════════════════════════════
with tab_budget:
    from src.storage import load_expenses, save_expenses, load_budgets, save_budgets
    from src.budget_calc import calc_budget_status, get_budget_alerts, generate_expense_id, generate_budget_id
    from src.models import EXPENSE_CATEGORIES, BUDGET_PERIODS
    import datetime as _dt

    if "expenses" not in st.session_state:
        st.session_state.expenses = load_expenses()
    if "budgets" not in st.session_state:
        st.session_state.budgets = load_budgets()

    _expenses = st.session_state.expenses
    _budgets  = st.session_state.budgets
    _fx_rates_bgt = fx_rates if fx_rates else {}
    _base_cur_bgt = display_currency

    _statuses = calc_budget_status(_expenses, _budgets, _base_cur_bgt, _fx_rates_bgt) if _budgets else []
    _alerts   = get_budget_alerts(_statuses)

    if _alerts:
        _alert_names = "、".join(s["category"] for s in _alerts)
        st.warning(f"⚠️ 預算警示：{_alert_names} 已超過設定閾值，請注意支出！")

    _col_main, _col_form = st.columns([2, 1])

    with _col_main:
        st.subheader("📊 預算概覽")
        if not _budgets:
            st.info("尚未設定預算，請在右側「設定預算」新增")
        else:
            for _s in _statuses:
                _pct  = min(_s["pct_used"], 1.0)
                _color = "🟢" if _s["pct_used"] < 0.6 else ("🟡" if _s["pct_used"] < 0.85 else "🔴")
                st.markdown(f"**{_color} {_s['category']}**（{_s['period']}）")
                st.progress(_pct)
                st.caption(
                    f"已花 {_s['spent_amount']:,.0f} / 預算 {_s['budget_amount']:,.0f} {_base_cur_bgt}"
                    f"（{_s['pct_used']*100:.1f}%）"
                )

        st.divider()
        st.subheader("📋 支出明細")
        _cat_filter    = st.selectbox("篩選類別", ["全部"] + EXPENSE_CATEGORIES, key="expense_cat_filter")
        _filtered_exp  = [e for e in _expenses if _cat_filter == "全部" or e["category"] == _cat_filter]
        _filtered_sort = sorted(_filtered_exp, key=lambda x: x["date"], reverse=True)[:30]

        if _filtered_sort:
            for _e in _filtered_sort:
                _ecol1, _ecol2, _ecol3 = st.columns([4, 1, 1])
                with _ecol1:
                    _note_txt = f" — {_e['note']}" if _e.get("note") else ""
                    st.caption(f"**{_e['date']}** {_e['category']} {_e['amount']:,.0f} {_e['currency']}{_note_txt}")
                with _ecol2:
                    if st.button("✏️", key=f"edit_exp_{_e['id']}", help="編輯"):
                        st.session_state["_editing_expense_id"] = _e["id"]
                        st.rerun()
                with _ecol3:
                    if st.button("🗑️", key=f"del_exp_{_e['id']}", help="刪除"):
                        st.session_state.expenses = [x for x in _expenses if x["id"] != _e["id"]]
                        save_expenses(st.session_state.expenses)
                        st.session_state.pop("_editing_expense_id", None)
                        st.rerun()
        else:
            st.info("尚無支出記錄")

        # Edit form (shown when an expense is selected for editing)
        _editing_id = st.session_state.get("_editing_expense_id")
        _editing_exp = next((e for e in _expenses if e["id"] == _editing_id), None) if _editing_id else None
        if _editing_exp:
            st.divider()
            st.markdown(f"**✏️ 編輯支出**（{_editing_exp['date']} {_editing_exp['category']}）")
            with st.form("edit_expense_form"):
                _edit_date = st.date_input("日期", value=_dt.date.fromisoformat(_editing_exp["date"]), key="edit_exp_date")
                _edit_cat  = st.selectbox("類別", EXPENSE_CATEGORIES,
                                          index=EXPENSE_CATEGORIES.index(_editing_exp["category"])
                                          if _editing_exp["category"] in EXPENSE_CATEGORIES else 0,
                                          key="edit_exp_cat")
                _edit_amt  = st.number_input("金額", min_value=0.01, value=float(_editing_exp["amount"]), step=1.0, key="edit_exp_amt")
                _edit_cur  = st.selectbox("幣別", ["TWD", "USD", "EUR", "JPY", "GBP"],
                                          index=["TWD", "USD", "EUR", "JPY", "GBP"].index(_editing_exp["currency"])
                                          if _editing_exp["currency"] in ["TWD", "USD", "EUR", "JPY", "GBP"] else 0,
                                          key="edit_exp_cur")
                _edit_note = st.text_input("備註", value=_editing_exp.get("note", ""), key="edit_exp_note")
                _ec1, _ec2 = st.columns(2)
                with _ec1:
                    if st.form_submit_button("💾 儲存修改"):
                        _updated = {**_editing_exp,
                                    "date": _edit_date.isoformat(),
                                    "category": _edit_cat,
                                    "amount": _edit_amt,
                                    "currency": _edit_cur,
                                    "note": _edit_note}
                        st.session_state.expenses = [_updated if e["id"] == _editing_id else e for e in _expenses]
                        save_expenses(st.session_state.expenses)
                        st.session_state.pop("_editing_expense_id", None)
                        st.rerun()
                with _ec2:
                    if st.form_submit_button("取消"):
                        st.session_state.pop("_editing_expense_id", None)
                        st.rerun()

    with _col_form:
        st.subheader("➕ 新增支出")
        with st.form("add_expense_form", clear_on_submit=True):
            _exp_date     = st.date_input("日期", value=_dt.date.today(), key="exp_date")
            _exp_cat      = st.selectbox("類別", EXPENSE_CATEGORIES, key="exp_cat")
            _exp_amount   = st.number_input("金額", min_value=0.01, value=100.0, step=1.0, key="exp_amount")
            _exp_currency = st.selectbox("幣別", ["TWD", "USD", "EUR", "JPY", "GBP"], key="exp_currency")
            _exp_note     = st.text_input("備註（選填）", key="exp_note")
            if st.form_submit_button("新增支出"):
                _new_exp = {
                    "id":       generate_expense_id(),
                    "date":     _exp_date.isoformat(),
                    "category": _exp_cat,
                    "amount":   _exp_amount,
                    "currency": _exp_currency,
                    "note":     _exp_note,
                }
                st.session_state.expenses.append(_new_exp)
                save_expenses(st.session_state.expenses)
                st.success("已新增支出！")
                st.rerun()

        st.divider()
        with st.expander("⚙️ 設定預算", expanded=len(_budgets) == 0):
            if _budgets:
                st.markdown("**現有預算**")
                for _b in _budgets:
                    _cb, _cdel = st.columns([3, 1])
                    with _cb:
                        st.caption(
                            f"{_b['category']} | {_b['amount']:,.0f} {_b['currency']} / {_b['period']}"
                            f" | 警示 {_b.get('alert_threshold', 0.6)*100:.0f}%"
                        )
                    with _cdel:
                        if st.button("✕", key=f"del_bgt_{_b['id']}"):
                            st.session_state.budgets = [x for x in _budgets if x["id"] != _b["id"]]
                            save_budgets(st.session_state.budgets)
                            st.rerun()

            st.markdown("**新增預算**")
            with st.form("add_budget_form", clear_on_submit=True):
                _bgt_cat       = st.selectbox("類別", ["總計"] + EXPENSE_CATEGORIES, key="bgt_cat")
                _bgt_amount    = st.number_input("金額", min_value=1.0, value=10000.0, step=100.0, key="bgt_amount")
                _bgt_currency  = st.selectbox("幣別", ["TWD", "USD", "EUR", "JPY", "GBP"], key="bgt_currency")
                _bgt_period    = st.selectbox("週期", BUDGET_PERIODS, key="bgt_period")
                _bgt_threshold_int = st.slider(
                    "警示閾值", 0, 100, 60, 5, format="%d%%",
                    key="bgt_threshold",
                    help="支出佔預算比例達此值時顯示警示",
                )
                if st.form_submit_button("儲存預算"):
                    _new_bgt = {
                        "id":              generate_budget_id(),
                        "category":        _bgt_cat,
                        "amount":          _bgt_amount,
                        "currency":        _bgt_currency,
                        "period":          _bgt_period,
                        "alert_threshold": _bgt_threshold_int / 100,
                    }
                    st.session_state.budgets.append(_new_bgt)
                    save_budgets(st.session_state.budgets)
                    st.success("預算已儲存！")
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — 回測工具
# ══════════════════════════════════════════════════════════════════════════════
with tab_backtest:
    from src.backtest import run_backtest
    import datetime as _dt2

    st.subheader("📈 投資組合回測")
    st.info("ℹ️ 僅含有代碼的資產（股票、ETF、加密貨幣）會納入計算，現金與其他類別略過")

    _bt_ctrl, _bt_result = st.columns([1, 2])

    with _bt_ctrl:
        _default_start = _dt2.date.today().replace(year=_dt2.date.today().year - 3)
        _bt_start = st.date_input("開始日期", value=_default_start, key="bt_start_date")
        _bt_end   = st.date_input("結束日期",  value=_dt2.date.today(), key="bt_end_date")
        _bt_bm_label = st.selectbox(
            "基準指數",
            ["SPY（S&P 500）", "QQQ（NASDAQ 100）", "0050.TW（台股50）", "不設基準"],
            key="bt_benchmark",
        )
        _benchmark_map = {
            "SPY（S&P 500）":  "SPY",
            "QQQ（NASDAQ 100）": "QQQ",
            "0050.TW（台股50）": "0050.TW",
            "不設基準": None,
        }
        _bt_bm = _benchmark_map[_bt_bm_label]

        if st.button("▶ 執行回測", key="run_backtest_btn", use_container_width=True):
            _bt_portfolio = load_portfolio()
            _bt_assets    = _bt_portfolio.get("assets", [])
            with st.spinner("正在下載歷史資料..."):
                _bt_result_data = run_backtest(
                    _bt_assets,
                    _bt_start.isoformat(),
                    _bt_end.isoformat(),
                    base_currency=display_currency,
                    benchmark=_bt_bm,
                )
            st.session_state["backtest_result"] = _bt_result_data

    with _bt_result:
        _bt_res = st.session_state.get("backtest_result")
        if _bt_res is None:
            st.markdown("← 設定日期範圍後點擊「執行回測」")
        elif "error" in _bt_res:
            st.error(_bt_res["error"])
        else:
            _m1, _m2, _m3 = st.columns(3)
            _m1.metric("總報酬率",         f"{_bt_res['total_return']*100:.1f}%")
            _m2.metric("年化報酬率 (CAGR)", f"{_bt_res['cagr']*100:.1f}%")
            _m3.metric("最大回撤",          f"-{_bt_res['max_drawdown']*100:.1f}%")

            if _bt_res.get("skipped"):
                st.caption(f"略過資產：{', '.join(_bt_res['skipped'])}")

            _bt_dates = _bt_res["dates"]
            _bt_pv    = _bt_res["portfolio_values"]
            _bt_fig   = go.Figure()
            _bt_fig.add_trace(go.Scatter(
                x=_bt_dates, y=_bt_pv, mode="lines", name="我的投資組合",
                line=dict(color="#6C63FF", width=2),
            ))
            if _bt_res.get("benchmark_values"):
                _bt_fig.add_trace(go.Scatter(
                    x=_bt_dates, y=_bt_res["benchmark_values"], mode="lines",
                    name=_bt_res.get("benchmark", "基準"),
                    line=dict(color="#FF6B6B", width=1.5, dash="dash"),
                ))
            _bt_fig.update_layout(
                xaxis_title="日期",
                yaxis_title=f"價值（{display_currency}）",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=30, b=0),
                height=350,
            )
            st.plotly_chart(_bt_fig, use_container_width=True)

            if _bt_res.get("asset_returns"):
                _df_ar = pd.DataFrame(_bt_res["asset_returns"])
                _df_ar["return"] = _df_ar["return"].map(lambda x: f"{x*100:.1f}%")
                _df_ar.columns = ["資產名稱", "代碼", "區間報酬率"]
                st.dataframe(_df_ar, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 — 市場資訊
# ══════════════════════════════════════════════════════════════════════════════
with tab_news:
    from src.news_fetcher import fetch_macro_news, fetch_market_news, fetch_stock_news

    st.subheader("📰 市場資訊")
    st.caption("新聞來源：Fed RSS、Yahoo Finance、CNBC、Guardian。情緒標記由關鍵字自動分析，僅供參考。")

    # Refresh button
    _news_col1, _news_col2 = st.columns([4, 1])
    with _news_col2:
        if st.button("🔄 重新整理", key="refresh_news"):
            for k in ["news_macro", "news_market", "news_stocks"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    # Load news (cached in session_state)
    if "news_macro" not in st.session_state:
        with st.spinner("載入總體經濟新聞..."):
            st.session_state["news_macro"] = fetch_macro_news(limit=8)

    if "news_market" not in st.session_state:
        with st.spinner("載入市場新聞..."):
            st.session_state["news_market"] = fetch_market_news(limit=10)

    # Get portfolio tickers for stock news
    _news_tickers = [
        a.get("ticker") for a in portfolio.get("assets", [])
        if a.get("category") in ("stock", "stock_tw", "etf") and a.get("ticker")
    ]
    if "news_stocks" not in st.session_state and _news_tickers:
        with st.spinner("載入個股新聞..."):
            st.session_state["news_stocks"] = fetch_stock_news(_news_tickers)

    # Three sub-tabs
    _ntab1, _ntab2, _ntab3 = st.tabs(["🏛️ 總體經濟", "📊 主要市場", "📈 持倉個股"])

    def _render_news_list(items: list):
        if not items:
            st.info("暫無新聞資料")
            return
        for item in items:
            col_s, col_t = st.columns([0.05, 0.95])
            with col_s:
                st.markdown(item.get("sentiment", "⚪"))
            with col_t:
                src = f" · {item['source']}" if item.get("source") else ""
                pub = f" · {item['published'][:10]}" if item.get("published") else ""
                st.markdown(f"[{item['title']}]({item['link']}){src}{pub}")

    with _ntab1:
        st.caption("央行政策、財政政策、總體經濟數據")
        _render_news_list(st.session_state.get("news_macro", []))

    with _ntab2:
        st.caption("主要指數與市場動態")
        _render_news_list(st.session_state.get("news_market", []))

    with _ntab3:
        if _news_tickers:
            st.caption(f"追蹤：{', '.join(_news_tickers[:6])}")
            _stock_news = st.session_state.get("news_stocks", [])
            if _stock_news:
                from collections import defaultdict
                _by_ticker = defaultdict(list)
                for item in _stock_news:
                    _by_ticker[item.get("ticker", "其他")].append(item)
                for _t, _items in _by_ticker.items():
                    with st.expander(f"**{_t}**（{len(_items)} 則）", expanded=True):
                        _render_news_list(_items)
            else:
                st.info("暫無個股新聞")
        else:
            st.info("持倉中沒有股票或 ETF，無個股新聞")
