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
    get_alerts,
    calc_margin_ratio,
    calc_monthly_interest,
)
from src.charts import allocation_pie, net_worth_bar

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
    alert_threshold = st.select_slider(
        "Price Alert Threshold",
        options=[1, 3, 5, 10],
        value=3,
        format_func=lambda x: f"{x}%",
    )

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

# Load raw portfolio (fast) for edit tab and calculators
portfolio = load_portfolio()
assets_df = get_assets_df(portfolio)
raw_liabilities_df = get_liabilities_df(portfolio)
fx_rates = build_fx_rates(assets_df, raw_liabilities_df, display_currency)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_dashboard, tab_edit = st.tabs(["📊 Dashboard", "✏️ Edit Portfolio"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Dashboard
# ══════════════════════════════════════════════════════════════════════════════
with tab_dashboard:

    if enriched_df is None:
        st.warning("No assets found. Go to **Edit Portfolio** to add your holdings.")
        st.stop()

    # Net worth summary
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Assets", f"{display_currency} {total_assets:,.0f}")
    col2.metric("Total Liabilities", f"{display_currency} {total_liabilities:,.0f}")
    col3.metric("Net Worth", f"{display_currency} {net_worth:,.0f}")

    # Charts
    st.markdown("---")
    pie_fig, pie_summary = allocation_pie(enriched_df, display_currency)
    pie_col, summary_col = st.columns([1.2, 1])
    with pie_col:
        st.plotly_chart(pie_fig, use_container_width=True)
    with summary_col:
        st.markdown("**資產配置說明**")
        for item in pie_summary:
            if item.get("is_others"):
                st.markdown(f"● 其他 Others: {item['pct']:.1f}% ({item['n']} 項合併)")
            else:
                st.markdown(f"● {item['label']}: {item['pct']:.1f}%")
        for item in pie_summary:
            if not item.get("is_others") and item["pct"] > 50:
                st.warning(f"⚠️ {item['label']} 佔比超過 50%，集中度偏高")
    st.plotly_chart(
        net_worth_bar(total_assets, total_liabilities, net_worth, display_currency),
        use_container_width=True,
    )

    # Price alerts
    alerts_df = get_alerts(enriched_df, alert_threshold)
    if not alerts_df.empty:
        st.markdown("---")
        st.subheader(f"⚠️ Price Alerts  (>{alert_threshold}% daily move)")
        for _, row in alerts_df.iterrows():
            direction = "▲" if row["daily_change_pct"] > 0 else "▼"
            color = "green" if row["daily_change_pct"] > 0 else "red"
            st.markdown(
                f"**{row['name']}** &nbsp; :{color}[{direction} {abs(row['daily_change_pct']):.2f}%]"
                f" &nbsp; {display_currency} {row['market_value']:,.0f}"
            )

    # Asset table
    st.markdown("---")
    st.subheader("Assets")
    display_cols = [
        "name", "category", "ticker", "quantity", "currency",
        "current_price", "daily_change_pct", "market_value", "cost_basis",
        "unrealized_pl", "unrealized_pl_pct",
    ]
    available_cols = [c for c in display_cols if c in enriched_df.columns]
    st.dataframe(
        enriched_df[available_cols],
        column_config={
            "name": st.column_config.TextColumn("Name"),
            "category": st.column_config.TextColumn("Category"),
            "ticker": st.column_config.TextColumn("Ticker"),
            "quantity": st.column_config.NumberColumn("Qty", format="%.4g"),
            "currency": st.column_config.TextColumn("CCY"),
            "current_price": st.column_config.NumberColumn("Price", format="%.2f"),
            "daily_change_pct": st.column_config.NumberColumn("Day %", format="%.2f"),
            "market_value": st.column_config.NumberColumn(f"Mkt Value ({display_currency})", format="%.0f"),
            "cost_basis": st.column_config.NumberColumn(f"Cost Basis ({display_currency})", format="%.0f"),
            "unrealized_pl": st.column_config.NumberColumn(f"Unreal. P/L ({display_currency})", format="%.0f"),
            "unrealized_pl_pct": st.column_config.NumberColumn("P/L %", format="%.2f"),
        },
        use_container_width=True,
        hide_index=True,
    )

    # Liabilities table
    if liabilities_df is not None and not liabilities_df.empty:
        st.markdown("---")
        st.subheader("Liabilities")
        st.dataframe(
            liabilities_df,
            column_config={
                "amount": st.column_config.NumberColumn("Amount", format="%.0f"),
                "annual_rate": st.column_config.NumberColumn("Annual Rate", format="%.2%%"),
            },
            use_container_width=True,
            hide_index=True,
        )

    # Calculators
    st.markdown("---")
    st.subheader("🔢 Calculators")
    calc_col1, calc_col2 = st.columns(2)

    with calc_col1:
        with st.expander("融資維持率 Margin Maintenance Ratio", expanded=True):
            total_mv, margin_loan, ratio = calc_margin_ratio(enriched_df, liabilities_df, fx_rates)
            if margin_loan == 0:
                st.info("No margin loans found in liabilities.")
            else:
                ratio_color = "normal" if ratio >= 130 else "inverse"
                st.metric(
                    "Maintenance Ratio",
                    f"{ratio:.1f}%",
                    delta=f"{ratio - 130:.1f}% vs 130% threshold",
                    delta_color=ratio_color,
                )
                st.caption(f"Total Portfolio: {display_currency} {total_mv:,.0f}")
                st.caption(f"Margin Loan: {display_currency} {margin_loan:,.0f}")
                if ratio < 130:
                    st.error("⚠️ Below 130% — margin call risk.")
                elif ratio < 150:
                    st.warning("Approaching threshold. Monitor closely.")
                else:
                    st.success("Healthy margin ratio.")

    with calc_col2:
        with st.expander("每月利息 Monthly Interest", expanded=True):
            interest_df, total_interest = calc_monthly_interest(liabilities_df, fx_rates)
            if interest_df.empty:
                st.info("No liabilities found.")
            else:
                st.metric("Total Monthly Interest", f"{display_currency} {total_interest:,.0f}")
                st.dataframe(
                    interest_df,
                    column_config={
                        "name": st.column_config.TextColumn("Name"),
                        "category": st.column_config.TextColumn("Type"),
                        "amount_base": st.column_config.NumberColumn(
                            f"Balance ({display_currency})", format="%.0f"
                        ),
                        "annual_rate": st.column_config.NumberColumn("Rate", format="%.2%%"),
                        "monthly_interest": st.column_config.NumberColumn(
                            f"Monthly ({display_currency})", format="%.0f"
                        ),
                    },
                    use_container_width=True,
                    hide_index=True,
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

    st.markdown("---")

    # ── Save ──────────────────────────────────────────────────────────────────
    if st.button("💾 Save Portfolio", type="primary"):
        asset_records = []

        for _, row in edited_market.dropna(subset=["name"]).iterrows():
            rec = row.where(pd.notna(row), other=None).to_dict()
            rec["id"] = f"asset_{len(asset_records)+1:03d}"
            asset_records.append(rec)

        for _, row in edited_manual.dropna(subset=["name"]).iterrows():
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
