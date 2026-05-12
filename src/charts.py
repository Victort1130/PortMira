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
    """Pie chart of portfolio allocation by asset category.

    Slices below 3% or beyond rank 10 are merged into '其他 Others'.
    Returns (fig, summary) where summary is a list of dicts:
      { label, pct, is_others }  — or { label, pct, n, is_others } for the Others slice.
    """
    by_cat = (
        enriched_df.groupby("category")["market_value"]
        .sum()
        .reset_index()
        .rename(columns={"category": "Category", "market_value": "Value"})
    )
    by_cat["Category"] = by_cat["Category"].map(lambda c: CATEGORY_LABELS.get(c, c))
    total = by_cat["Value"].sum()
    if total == 0:
        return go.Figure(), []

    by_cat["pct"] = by_cat["Value"] / total * 100
    by_cat = by_cat.sort_values("Value", ascending=False).reset_index(drop=True)

    visible_mask = (by_cat["pct"] >= 3.0) & (by_cat.index < 10)
    visible = by_cat[visible_mask].copy()
    others = by_cat[~visible_mask].copy()

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


def net_worth_bar(
    total_assets: float,
    total_liabilities: float,
    net_worth: float,
    base_currency: str = "TWD",
) -> go.Figure:
    """Bar chart comparing total assets, total liabilities, and net worth."""
    fig = go.Figure(
        go.Bar(
            x=["Total Assets", "Total Liabilities", "Net Worth"],
            y=[total_assets, total_liabilities, net_worth],
            marker_color=["#2ecc71", "#e74c3c", "#3498db"],
            text=[f"{v:,.0f}" for v in [total_assets, total_liabilities, net_worth]],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=f"Net Worth Overview ({base_currency})",
        yaxis_title=base_currency,
        margin=dict(t=50, b=0, l=0, r=0),
    )
    return fig
