import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

CATEGORY_LABELS = {
    "stock": "US Stock",
    "stock_tw": "TW Stock",
    "etf": "ETF",
    "crypto": "Crypto",
    "cash": "Cash",
    "other": "Other",
}


def allocation_pie(
    enriched_df: pd.DataFrame, base_currency: str = "TWD"
) -> tuple[go.Figure, list]:
    """Pie chart of portfolio allocation by individual asset.

    Label is ticker (if available) or name. Slices below 3% or beyond rank 10
    are merged into '其他 Others'.
    Returns (fig, summary) where summary is a list of dicts:
      { label, pct, is_others }  — or { label, pct, n, is_others } for the Others slice.
    """
    df = enriched_df.copy()

    # FIX 3: ensure market_value is numeric before any aggregation
    df["market_value"] = pd.to_numeric(df["market_value"], errors="coerce").fillna(0)

    # display_label: ticker → name → "Unknown" (never NaN, so groupby never drops a row)
    def _label(r):
        t = r.get("ticker")
        if pd.notna(t) and str(t).strip() != "":
            return str(t).strip()
        n = r.get("name")
        if pd.notna(n) and str(n).strip() != "":
            return str(n).strip()
        return "Unknown"

    df["display_label"] = df.apply(_label, axis=1)

    # total from ALL rows — matches the dashboard metric (must not be derived from groupby,
    # which would silently drop NaN-labelled rows under the old code)
    total_value = df["market_value"].sum()
    if total_value == 0:
        return go.Figure(), []

    by_asset = (
        df.groupby("display_label")["market_value"]
        .sum()
        .reset_index()
        .rename(columns={"display_label": "Category", "market_value": "Value"})
    )

    by_asset["pct"] = by_asset["Value"] / total_value * 100
    by_asset = by_asset.sort_values("Value", ascending=False).reset_index(drop=True)

    visible_mask = (by_asset["pct"] >= 3.0) & (by_asset.index < 10)
    visible = by_asset[visible_mask].copy()
    others = by_asset[~visible_mask].copy()

    if not others.empty:
        others_row = pd.DataFrame([{
            "Category": "其他 Others",
            "Value": others["Value"].sum(),
            "pct": others["pct"].sum(),
        }])
        plot_df = pd.concat([visible[["Category", "Value", "pct"]], others_row], ignore_index=True)
    else:
        plot_df = visible[["Category", "Value", "pct"]].reset_index(drop=True)

    fig = px.pie(
        plot_df,
        names="Category",
        values="Value",
        title="Asset Allocation",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(showlegend=True, margin=dict(t=50, b=0, l=0, r=0))

    summary = [
        {"label": row["Category"], "pct": row["pct"], "is_others": False}
        for _, row in visible.iterrows()
    ]
    if not others.empty:
        summary.append({
            "label": "其他 Others",
            "pct": others["pct"].sum(),
            "n": len(others),
            "is_others": True,
        })

    return fig, summary


def simplified_category_pie(
    enriched_df: pd.DataFrame, base_currency: str = "TWD"
) -> go.Figure:
    """Pie chart grouping assets into 4 broad categories."""
    GROUPS = {
        "股票 Stock": ["stock", "stock_tw", "etf"],
        "加密貨幣 Crypto": ["crypto"],
        "現金 Cash": ["cash"],
        "其他 Other": ["other"],
    }
    rows = [
        {"Category": label, "Value": enriched_df[enriched_df["category"].isin(cats)]["market_value"].sum()}
        for label, cats in GROUPS.items()
    ]
    plot_df = pd.DataFrame([r for r in rows if r["Value"] > 0])
    if plot_df.empty:
        return go.Figure()

    fig = px.pie(
        plot_df,
        names="Category",
        values="Value",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(showlegend=True, margin=dict(t=50, b=0, l=0, r=0))
    return fig
