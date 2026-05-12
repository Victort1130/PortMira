import streamlit as st
import pandas as pd
from datetime import datetime

from src.storage import load_portfolio, get_assets_df, get_liabilities_df, save_portfolio
from src.calculations import (
    build_prices,
    build_prev_closes,
    build_fx_rates,
    enrich_assets,
    calc_net_worth,
)
from src.charts import allocation_pie, simplified_category_pie

st.set_page_config(page_title="PortMira", page_icon="📊", layout="wide")

ASSET_CATEGORIES = ["stock", "stock_tw", "etf", "crypto", "cash", "other"]
LIAB_CATEGORIES = ["credit_card", "loan", "margin_loan", "other_liability"]
CURRENCIES = ["TWD", "USD", "EUR", "JPY", "GBP"]

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("PortMira")
    st.markdown("---")

    display_currency = st.radio("Display Currency", ["TWD", "USD"], horizontal=True)

    st.markdown("---")
    if st.button("🔄 Refresh Prices"):
        st.cache_data.clear()
        st.rerun()


# ── Cached price fetching ──────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_and_enrich(base_currency: str):
    portfolio = load_portfolio()
    assets_df = get_assets_df(portfolio)
    liabilities_df = get_liabilities_df(portfolio)

    if assets_df.empty:
        return None, None, None, None, None

    prices = build_prices(assets_df)
    prev_closes = build_prev_closes(assets_df)
    fx_rates = build_fx_rates(assets_df, liabilities_df, base_currency)
    enriched_df = enrich_assets(assets_df, prices, fx_rates, base_currency, prev_closes)
    total_assets, total_liabilities, net_worth = calc_net_worth(
        enriched_df, liabilities_df, fx_rates
    )
    return enriched_df, liabilities_df, total_assets, total_liabilities, net_worth


st.title("📊 PortMira")
st.caption("A local-first portfolio mirror.")

with st.spinner("Fetching latest prices…"):
    enriched_df, liabilities_df, total_assets, total_liabilities, net_worth = load_and_enrich(
        display_currency
    )

# Load raw portfolio (fast) for edit tab and holdings tab
portfolio = load_portfolio()
raw_liabilities_df = get_liabilities_df(portfolio)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_dashboard, tab_edit, tab_holdings = st.tabs(["📊 總覽", "✏️ 編輯組合", "📋 持倉明細"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Dashboard
# ══════════════════════════════════════════════════════════════════════════════
with tab_dashboard:

    if enriched_df is None or enriched_df.empty:
        st.info("📂 尚未有資產資料。請前往「編輯組合」頁面新增您的資產。")
    else:
        # ── Section 1: Net Worth Row ──────────────────────────────────────────
        nw_left, nw_right = st.columns([1.5, 1])
        with nw_left:
            st.metric("💼 淨資產 Net Worth", f"{display_currency} {net_worth:,.0f}")
        with nw_right:
            st.metric("📈 總資產 Total Assets", f"{display_currency} {total_assets:,.0f}")
            st.metric("📉 總負債 Total Liabilities", f"{display_currency} {total_liabilities:,.0f}")

        st.divider()

        # ── Section 2: Two Pie Charts ─────────────────────────────────────────
        pie_left, pie_right = st.columns(2)

        with pie_left:
            st.caption("資產類別配置")
            pie_fig, pie_summary = allocation_pie(enriched_df, display_currency)
            st.plotly_chart(pie_fig, use_container_width=True)
            for item in pie_summary:
                if item.get("is_others"):
                    st.markdown(f"● 其他 Others: {item['pct']:.1f}% ({item['n']} 項合併)")
                else:
                    st.markdown(f"● {item['label']}: {item['pct']:.1f}%")

        with pie_right:
            st.caption("資產大類佔比")
            st.plotly_chart(
                simplified_category_pie(enriched_df, display_currency),
                use_container_width=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Edit Portfolio
# ══════════════════════════════════════════════════════════════════════════════
with tab_edit:

    _MARKET_CATS  = ["stock", "stock_tw", "etf", "crypto"]
    _MANUAL_CATS  = ["cash", "other"]
    _MARKET_COLS  = ["name", "category", "ticker", "quantity", "cost_per_unit", "currency", "note"]
    _MANUAL_COLS  = ["name", "category", "quantity", "cost_per_unit", "currency", "note"]
    _LIAB_COLS    = ["name", "category", "amount", "currency", "annual_rate", "note"]

    # ── 初始化 session_state ──────────────────────────────────────────────────
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

        st.session_state["edit_market_df"] = (
            _market[[c for c in _MARKET_COLS if c in _market.columns]].copy()
            if not _market.empty else pd.DataFrame(columns=_MARKET_COLS)
        )
        st.session_state["edit_manual_df"] = (
            _manual[[c for c in _MANUAL_COLS if c in _manual.columns]].copy()
            if not _manual.empty else pd.DataFrame(columns=_MANUAL_COLS)
        )
        st.session_state["edit_liab_df"] = (
            _raw_liabs[[c for c in _LIAB_COLS if c in _raw_liabs.columns]].copy()
            if _raw_liabs is not None and not _raw_liabs.empty
            else pd.DataFrame(columns=_LIAB_COLS)
        )

    # ── Section 1: 市場型資產 ─────────────────────────────────────────────────
    st.subheader("市場型資產  Market Assets")
    st.caption("Stocks, ETFs, crypto — have live tickers.")

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
            "quantity":      st.column_config.NumberColumn("Quantity", min_value=0),
            "cost_per_unit": st.column_config.NumberColumn("Cost / Unit", min_value=0),
            "currency":      st.column_config.SelectboxColumn("Currency", options=CURRENCIES, required=True),
            "note":          st.column_config.TextColumn("Note"),
        },
    )
    if st.button("➕ 新增市場資產", key="add_market_row"):
        st.session_state["edit_market_df"] = pd.concat(
            [edited_market, pd.DataFrame([{col: None for col in _MARKET_COLS}])],
            ignore_index=True,
        )
        st.rerun()

    st.markdown("---")

    # ── Section 2: 手動資產 ───────────────────────────────────────────────────
    st.subheader("手動資產  Manual Assets")
    st.caption("Cash and other holdings — no live price feed.")

    edited_manual = st.data_editor(
        st.session_state["edit_manual_df"],
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="manual_assets_editor",
        column_config={
            "name":          st.column_config.TextColumn("Name", required=True),
            "category":      st.column_config.SelectboxColumn("Category", options=_MANUAL_CATS, required=True),
            "quantity":      st.column_config.NumberColumn("Quantity / Amount", min_value=0),
            "cost_per_unit": st.column_config.NumberColumn("Cost / Unit", min_value=0),
            "currency":      st.column_config.SelectboxColumn("Currency", options=CURRENCIES, required=True),
            "note":          st.column_config.TextColumn("Note"),
        },
    )
    if st.button("➕ 新增手動資產", key="add_manual_row"):
        st.session_state["edit_manual_df"] = pd.concat(
            [edited_manual, pd.DataFrame([{col: None for col in _MANUAL_COLS}])],
            ignore_index=True,
        )
        st.rerun()

    st.markdown("---")

    # ── Section 3: 負債 ───────────────────────────────────────────────────────
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
            "annual_rate": st.column_config.NumberColumn("Annual Rate (e.g. 0.05 = 5%)", min_value=0.0, max_value=1.0),
            "note":        st.column_config.TextColumn("Note"),
        },
    )
    if st.button("➕ 新增負債", key="add_liab_row"):
        st.session_state["edit_liab_df"] = pd.concat(
            [edited_liabilities, pd.DataFrame([{col: None for col in _LIAB_COLS}])],
            ignore_index=True,
        )
        st.rerun()

    st.markdown("---")

    # ── Save ──────────────────────────────────────────────────────────────────
    if st.button("💾 Save Portfolio", type="primary"):
        asset_records = []

        for _, row in edited_market.iterrows():
            name = row.get("name")
            ticker = row.get("ticker")
            if pd.isna(name) or name == "":
                if pd.isna(ticker) or ticker == "":
                    continue
                row = row.copy()
                row["name"] = ticker
            rec = row.where(pd.notna(row), other=None).to_dict()
            if not rec.get("cost_per_unit"):
                rec["cost_per_unit"] = 0
            rec["id"] = f"asset_{len(asset_records)+1:03d}"
            asset_records.append(rec)

        # Validate manual assets: name is required
        manual_rows = edited_manual[edited_manual["name"].notna() & (edited_manual["name"] != "")]
        missing_names = len(edited_manual) - len(manual_rows)
        if missing_names > 0 and not edited_manual.dropna(how="all").empty:
            st.warning("手動資產的「名稱」為必填欄位，請補齊後再儲存。")
            st.stop()

        for _, row in manual_rows.iterrows():
            row = row.copy()
            if row.get("category") == "cash" and (pd.isna(row.get("cost_per_unit")) or row.get("cost_per_unit") == 0):
                row["cost_per_unit"] = 1.0
            rec = row.where(pd.notna(row), other=None).to_dict()
            rec["id"] = f"asset_{len(asset_records)+1:03d}"
            rec["ticker"] = None
            asset_records.append(rec)

        liab_records = []
        for _, row in edited_liabilities.dropna(subset=["name"]).iterrows():
            rec = row.where(pd.notna(row), other=None).to_dict()
            rec["id"] = f"liab_{len(liab_records)+1:03d}"
            liab_records.append(rec)

        portfolio["assets"] = asset_records
        portfolio["liabilities"] = liab_records
        portfolio["meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")

        save_portfolio(portfolio)

        del st.session_state["edit_market_df"]
        del st.session_state["edit_manual_df"]
        del st.session_state["edit_liab_df"]
        st.cache_data.clear()

        st.success("Portfolio saved! Switch to Dashboard to see updated data.")
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — 持倉明細
# ══════════════════════════════════════════════════════════════════════════════
with tab_holdings:

    if enriched_df is None or enriched_df.empty:
        st.info("尚未有資產資料。")
    else:
        # ── Section 1: 資產持倉 ───────────────────────────────────────────────
        st.subheader("資產持倉")
        _display_cols = [
            "name", "ticker", "category", "quantity",
            "current_price", "cost_per_unit",
            "market_value", "cost_basis",
            "unrealized_pl", "unrealized_pl_pct",
            "daily_change_pct",
        ]
        _available = [c for c in _display_cols if c in enriched_df.columns]
        _numeric_cols = [
            "market_value", "cost_basis", "unrealized_pl", "unrealized_pl_pct",
            "current_price", "cost_per_unit", "daily_change_pct",
        ]
        _display_df = enriched_df[_available].copy()
        _comma1_cols = ["market_value", "cost_basis", "unrealized_pl", "current_price", "cost_per_unit"]
        for _col in _numeric_cols:
            if _col in _display_df.columns:
                _display_df[_col] = pd.to_numeric(_display_df[_col], errors="coerce")
        for _col in _comma1_cols:
            if _col in _display_df.columns:
                _display_df[_col] = _display_df[_col].apply(
                    lambda x: f"{x:,.1f}" if pd.notna(x) else ""
                )

        st.dataframe(
            _display_df,
            column_config={
                "name":             st.column_config.TextColumn("資產名稱"),
                "ticker":           st.column_config.TextColumn("代號"),
                "category":         st.column_config.TextColumn("類別"),
                "quantity":         st.column_config.NumberColumn("數量", format="%.4g"),
                "current_price":    st.column_config.TextColumn("現價"),
                "cost_per_unit":    st.column_config.TextColumn("成本/單位"),
                "market_value":     st.column_config.TextColumn(f"市值 ({display_currency})"),
                "cost_basis":       st.column_config.TextColumn(f"總成本 ({display_currency})"),
                "unrealized_pl":    st.column_config.TextColumn(f"未實現損益 ({display_currency})"),
                "unrealized_pl_pct":st.column_config.NumberColumn("損益%", format="%+.2f%%"),
                "daily_change_pct": st.column_config.NumberColumn("日變動%", format="%+.2f%%"),
            },
            use_container_width=True,
            hide_index=True,
        )

        # ── Section 2: 負債明細 ───────────────────────────────────────────────
        if raw_liabilities_df is not None and not raw_liabilities_df.empty:
            st.divider()
            st.subheader("負債明細")
            st.dataframe(raw_liabilities_df, use_container_width=True, hide_index=True)
