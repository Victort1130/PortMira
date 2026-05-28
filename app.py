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

ASSET_CATEGORIES = ["stock", "stock_tw", "etf", "crypto", "cash", "other"]
LIAB_CATEGORIES  = ["credit_card", "loan", "margin_loan", "other_liability"]
CURRENCIES       = ["TWD", "USD", "EUR", "JPY", "GBP"]

_MARKET_CATS = ["stock", "stock_tw", "etf", "crypto"]
_MANUAL_CATS = ["cash", "other"]
_MARKET_COLS = ["name", "category", "ticker", "quantity", "cost_per_unit",
                "currency", "purchase_date", "target_pct", "note"]
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
tab_dashboard, tab_edit, tab_holdings, tab_rebalance, tab_scenario = st.tabs([
    "📊 總覽", "✏️ 編輯組合", "📋 持倉明細", "⚖️ 再平衡", "🔮 情境分析",
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
    st.caption("Stocks · ETFs · Crypto — prices fetched automatically.")

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
            "target_pct":    st.column_config.NumberColumn("Target %", min_value=0, max_value=100,
                                                            help="再平衡目標比例（0–100）"),
            "note":          st.column_config.TextColumn("Note"),
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

        manual_rows   = edited_manual[edited_manual["name"].notna() & (edited_manual["name"] != "")]
        missing_names = len(edited_manual) - len(manual_rows)
        if missing_names > 0 and not edited_manual.dropna(how="all").empty:
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
            rebalance_df = calc_rebalance(enriched_df)
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

            st.caption("資產類別漲跌幅")
            shock_stock    = st.slider("股票 Stock",      -100, 100, int(loaded_cat.get("stock",    0)*100), step=1, format="%d%%") / 100
            shock_stock_tw = st.slider("台股 TW Stock",   -100, 100, int(loaded_cat.get("stock_tw", 0)*100), step=1, format="%d%%") / 100
            shock_etf      = st.slider("ETF",             -100, 100, int(loaded_cat.get("etf",      0)*100), step=1, format="%d%%") / 100
            shock_crypto   = st.slider("加密貨幣 Crypto", -100, 100, int(loaded_cat.get("crypto",   0)*100), step=1, format="%d%%") / 100
            shock_other    = st.slider("其他 Other",      -100, 100, int(loaded_cat.get("other",    0)*100), step=1, format="%d%%") / 100

            st.caption("匯率變動（正 = 外幣升值）")
            fx_usd = st.slider("USD", -30, 30, int(loaded_fx.get("USD", 0)*100), step=1, format="%d%%") / 100
            fx_eur = st.slider("EUR", -30, 30, int(loaded_fx.get("EUR", 0)*100), step=1, format="%d%%") / 100
            fx_jpy = st.slider("JPY", -30, 30, int(loaded_fx.get("JPY", 0)*100), step=1, format="%d%%") / 100

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
                                "etf": shock_etf, "crypto": shock_crypto, "other": shock_other,
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
                "etf": shock_etf, "crypto": shock_crypto, "other": shock_other,
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
