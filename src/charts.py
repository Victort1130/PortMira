import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

CATEGORY_LABELS = {
    "stock":     "US Stock",
    "stock_tw":  "TW Stock",
    "etf":       "ETF",
    "crypto":    "Crypto",
    "commodity": "Commodity",
    "cash":      "Cash",
    "other":     "Other",
}

_PALETTE = [
    "#4f46e5", "#7c3aed", "#06b6d4", "#10b981",
    "#f59e0b", "#ef4444", "#ec4899", "#6366f1",
    "#14b8a6", "#84cc16",
]

_LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", color="#374151"),
    margin=dict(t=8, b=8, l=8, r=8),
    legend=dict(
        orientation="v",
        x=1.02, y=0.5,
        font=dict(size=12),
        bgcolor="rgba(0,0,0,0)",
    ),
)


def allocation_pie(enriched_df: pd.DataFrame, base_currency: str = "TWD") -> tuple[go.Figure, list]:
    df = enriched_df.copy()
    df["market_value"] = pd.to_numeric(df["market_value"], errors="coerce").fillna(0)

    def _label(r):
        t = r.get("ticker")
        if pd.notna(t) and str(t).strip():
            return str(t).strip()
        n = r.get("name")
        if pd.notna(n) and str(n).strip():
            return str(n).strip()
        return "Unknown"

    df["display_label"] = df.apply(_label, axis=1)
    total_value = df["market_value"].sum()
    if total_value == 0:
        return go.Figure(), []

    by_asset = (
        df.groupby("display_label")["market_value"]
        .sum().reset_index()
        .rename(columns={"display_label": "label", "market_value": "value"})
        .sort_values("value", ascending=False).reset_index(drop=True)
    )
    by_asset["pct"] = by_asset["value"] / total_value * 100

    visible_mask = (by_asset["pct"] >= 3.0) & (by_asset.index < 10)
    visible = by_asset[visible_mask].copy()
    others  = by_asset[~visible_mask].copy()

    if not others.empty:
        others_row = pd.DataFrame([{
            "label": "其他 Others",
            "value": others["value"].sum(),
            "pct":   others["pct"].sum(),
        }])
        plot_df = pd.concat([visible, others_row], ignore_index=True)
    else:
        plot_df = visible.reset_index(drop=True)

    fig = go.Figure(go.Pie(
        labels=plot_df["label"],
        values=plot_df["value"],
        hole=0.55,
        marker=dict(
            colors=[_PALETTE[i % len(_PALETTE)] for i in range(len(plot_df))],
            line=dict(color="#ffffff", width=2),
        ),
        textposition="inside",
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} " + base_currency +
                      "<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(**_LAYOUT_BASE, showlegend=True, height=280)

    summary = [
        {"label": row["label"], "pct": row["pct"], "is_others": False}
        for _, row in visible.iterrows()
    ]
    if not others.empty:
        summary.append({
            "label": "其他 Others",
            "pct":   others["pct"].sum(),
            "n":     len(others),
            "is_others": True,
        })
    return fig, summary


def simplified_category_pie(enriched_df: pd.DataFrame, base_currency: str = "TWD") -> go.Figure:
    GROUPS = {
        "股票 Stock":       ["stock", "stock_tw", "etf"],
        "加密貨幣 Crypto":  ["crypto"],
        "大宗商品 Commodity": ["commodity"],
        "現金 Cash":        ["cash"],
        "其他 Other":       ["other"],
    }
    enriched_df = enriched_df.copy()
    enriched_df["market_value"] = pd.to_numeric(enriched_df["market_value"], errors="coerce").fillna(0)

    rows = [
        {"label": lbl, "value": enriched_df[enriched_df["category"].isin(cats)]["market_value"].sum()}
        for lbl, cats in GROUPS.items()
    ]
    plot_df = pd.DataFrame([r for r in rows if r["value"] > 0])
    if plot_df.empty:
        return go.Figure()

    colors = ["#4f46e5", "#7c3aed", "#f59e0b", "#10b981", "#94a3b8"][:len(plot_df)]

    fig = go.Figure(go.Pie(
        labels=plot_df["label"],
        values=plot_df["value"],
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
        textposition="inside",
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} " + base_currency +
                      "<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(**_LAYOUT_BASE, showlegend=True, height=280)
    return fig
