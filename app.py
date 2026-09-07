"""
Stock Correlation Engine
Checks whether correlations between stock returns are statistically
significant, or just noise that happens to look like a pattern.
"""

import itertools
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf
from scipy.stats import pearsonr

industry_tickers = {
    "US Tech": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META",
        "NVDA", "TSLA", "ORCL", "ADBE", "CRM",
    ],
    "US Finance": [
        "JPM", "BAC", "WFC", "GS", "MS",
        "C", "AXP", "BLK", "SCHW", "USB",
    ],
    "US Healthcare": [
        "JNJ", "UNH", "PFE", "MRK", "ABBV",
        "LLY", "TMO", "ABT", "BMY", "CVS",
    ],
    "Indian IT": [
        "TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS",
        "LTIM.NS", "MPHASIS.NS", "PERSISTENT.NS", "COFORGE.NS", "LTTS.NS",
    ],
    "Indian Banking": [
        "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS",
        "INDUSINDBK.NS", "BANKBARODA.NS", "PNB.NS", "IDFCFIRSTB.NS", "FEDERALBNK.NS",
    ],
    "Indian Energy & Manufacturing": [
        "RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "TATAMOTORS.NS",
        "TATASTEEL.NS", "LT.NS", "BHEL.NS", "ADANIENT.NS", "COALINDIA.NS",
    ],
}
SIGNIFICANCE_LEVEL = 0.05

st.set_page_config(page_title="Stock Correlation Engine", layout="wide")

st.title("Stock Correlation Engine")
st.markdown(
    "Two stocks can look correlated purely by chance, especially over a short "
    "window of data. This tool calculates the correlation between every pair "
    "of stocks in your list **and** runs a significance test (p-value) on each "
    "one, so you can tell a real relationship apart from coincidence."
)

with st.sidebar:
    st.header("Settings")

    selected_industries = st.multiselect(
        "Choose industries",
        options=list(industry_tickers.keys()),
        default=["Indian IT", "US Tech"],
    )

    industry_pool = []
    for industry in selected_industries:
        for t in industry_tickers[industry]:
            if t not in industry_pool:
                industry_pool.append(t)

    all_tickers_pool = sorted({t for tks in industry_tickers.values() for t in tks})

    tickers = st.multiselect(
        "Tickers (edit if needed)",
        options=all_tickers_pool,
        default=industry_pool,
        help="Pre-filled from your chosen industries. Add or remove individual "
        "tickers freely — any ticker from any industry is available here.",
    )

    today = date.today()
    start_date = st.date_input("Start date", value=today - timedelta(days=730))
    end_date = st.date_input("End date", value=today)
    run = st.button("Run analysis", type="primary")


@st.cache_data(show_spinner=False)
def download_prices(tickers, start, end):
    data = yf.download(tickers, start=start, end=end, progress=False)["Close"]
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])
    return data


def compute_correlations(returns):
    results = []
    for stock1, stock2 in itertools.combinations(returns.columns, 2):
        corr, p_value = pearsonr(returns[stock1], returns[stock2])
        results.append({
            "Stock 1": stock1,
            "Stock 2": stock2,
            "Correlation": round(corr, 3),
            "P-Value": round(p_value, 4),
            "Significant?": "Yes" if p_value < SIGNIFICANCE_LEVEL else "No",
        })
    df = pd.DataFrame(results)
    return df.sort_values("Correlation", ascending=False).reset_index(drop=True)


SIG_YES_LABEL = "✓ Likely real"
SIG_NO_LABEL = "✗ Could be chance"

SIG_GREEN = "#2ecc71"
SIG_GREEN_LINE = "#12703a"
NOT_SIG_GRAY = "#95a5a6"
NOT_SIG_RED_LINE = "#e74c3c"


def significance_label(raw_value):
    """Map the raw 'Yes'/'No' significance flag to a plain-English display label."""
    return SIG_YES_LABEL if raw_value == "Yes" else SIG_NO_LABEL


def correlation_strength(corr):
    magnitude = abs(corr)
    if magnitude < 0.2:
        return "very weak"
    if magnitude < 0.4:
        return "weak"
    if magnitude < 0.6:
        return "moderate"
    return "strong"


def join_phrases(phrases):
    """Join phrases as 'a', 'a and b', or 'a, b and c'."""
    if not phrases:
        return ""
    if len(phrases) == 1:
        return phrases[0]
    return ", ".join(phrases[:-1]) + " and " + phrases[-1]


def describe_selection(analysed_tickers):
    """One sentence describing what was selected, based on the tickers actually analysed."""
    counts = {}
    for ticker in analysed_tickers:
        industry = industry_of(ticker)
        counts[industry] = counts.get(industry, 0) + 1

    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    phrases = [
        f"**{n} {industry}** stock{'s' if n != 1 else ''}" for industry, n in ordered
    ]

    if len(ordered) == 1:
        scope = "within that group"
    elif len(ordered) == 2:
        scope = "within each group and across both"
    else:
        scope = "within each group and across all of them"

    return (
        f"You selected {join_phrases(phrases)}. We're comparing every stock against "
        f"every other one, {scope}, to see which pairs move together and which don't."
    )


def describe_span(trading_days):
    """Express a trading-day count as an approximate human-readable span."""
    years = trading_days / 250
    if years < 1:
        months = max(1, round(years * 12))
        return f"roughly {months} month{'s' if months != 1 else ''}"
    if round(years, 1) == 1.0:
        return "roughly 1 year"
    return f"roughly {years:.1f} years"


def style_significance(row):
    is_significant = row["Significant?"] in ("Yes", SIG_YES_LABEL)
    color = "background-color: #1a4d2e" if is_significant else "background-color: #4d1a1a"
    return [color] * len(row)


PAIR_TABLE_COLUMNS = ["Stock 1", "Stock 2", "Correlation", "P-Value", "Significant?"]

PAIR_COLUMN_CONFIG = {
    "Correlation": st.column_config.ProgressColumn(
        "Correlation",
        help="How much two stocks move together, from -1 (opposite) to 1 (identical movement).",
        format="%.3f",
        min_value=0.0,
        max_value=1.0,
    ),
    "P-Value": st.column_config.NumberColumn(
        "P-Value",
        help="Probability this result is due to random chance. Below 0.05 means the "
        "relationship is likely real.",
        format="%.4f",
    ),
    "Significant?": st.column_config.TextColumn(
        "Significant?",
        help="Whether the correlation passes the 0.05 threshold for being considered "
        "real rather than coincidence (statistically significant, p < 0.05).",
    ),
}


def industry_of(ticker):
    for industry, tks in industry_tickers.items():
        if ticker in tks:
            return industry
    return "Other"


def add_relationship_column(results_df):
    rel_df = results_df.copy()
    rel_df["Industry 1"] = rel_df["Stock 1"].map(industry_of)
    rel_df["Industry 2"] = rel_df["Stock 2"].map(industry_of)
    rel_df["Relationship"] = rel_df.apply(
        lambda r: f"Within {r['Industry 1']}"
        if r["Industry 1"] == r["Industry 2"]
        else " vs ".join(sorted([r["Industry 1"], r["Industry 2"]])),
        axis=1,
    )
    return rel_df


def build_relationship_summary(results_df):
    rel_df = add_relationship_column(results_df)
    summary = (
        rel_df.groupby("Relationship")
        .agg(
            Pairs=("Correlation", "count"),
            **{"Avg Correlation": ("Correlation", "mean")},
            **{"% Significant": ("Significant?", lambda s: (s == "Yes").mean() * 100)},
        )
        .reset_index()
        .sort_values("Avg Correlation", ascending=False)
    )
    return summary


def country_of(industry):
    if industry.startswith("US"):
        return "US"
    if industry.startswith("Indian"):
        return "India"
    return "Other"


def generate_inference_text(summary):
    within = summary[summary["Relationship"].str.startswith("Within")]
    across = summary[~summary["Relationship"].str.startswith("Within")]

    lines = []
    for _, row in within.iterrows():
        industry = row["Relationship"].replace("Within ", "")
        lines.append(
            f"- **Within {industry}**: {int(row['Pairs'])} pair(s), average "
            f"correlation **{row['Avg Correlation']:.2f}**, "
            f"**{row['% Significant']:.0f}%** statistically significant."
        )
    for _, row in across.iterrows():
        lines.append(
            f"- **{row['Relationship']}** (cross-industry): {int(row['Pairs'])} pair(s), "
            f"average correlation **{row['Avg Correlation']:.2f}**, "
            f"**{row['% Significant']:.0f}%** statistically significant."
        )

    verdict = ""
    if not within.empty and not across.empty:
        avg_within = within["Avg Correlation"].mean()
        avg_across = across["Avg Correlation"].mean()
        crosses_country = any(
            country_of(a) != country_of(b)
            for rel in across["Relationship"]
            for a, b in [rel.split(" vs ")]
        )
        scope = "country/industry" if crosses_country else "industry"
        if avg_within > avg_across + 0.05:
            verdict = (
                f"**Why:** within-industry pairs correlate more strongly than "
                f"cross-{scope} pairs here. Stocks in the same industry and "
                "country tend to share local drivers — currency, interest rates, "
                "sector-specific news, the same trading calendar — while "
                f"cross-{scope} pairs are exposed to different macro conditions, "
                "so any observed co-movement is more likely to be coincidence. "
                "That also tracks with the lower significance rate on the "
                "cross-industry pairs above."
            )
        elif avg_across > avg_within + 0.05:
            verdict = (
                f"**Why:** cross-{scope} correlations came out *higher* than "
                "within-industry ones here — somewhat unusual. This can happen "
                "when a shared global factor (overall market sentiment, US rate "
                "moves affecting capital flows worldwide) dominates over "
                "sector-specific drivers during this date range. Treat this "
                "with extra caution and lean on the p-values, not just the "
                "correlation numbers, before concluding anything."
            )
        else:
            verdict = (
                "**Why:** within-industry and cross-industry correlations came "
                "out similar here — no strong industry or country effect showing "
                "up for this particular date range and ticker selection."
            )
    elif not within.empty:
        verdict = (
            "**Why:** only one industry group is present, so there's nothing to "
            "compare it against — this just shows how tightly that industry's "
            "stocks move together."
        )

    return "\n".join(lines) + ("\n\n" + verdict if verdict else "")


if run:
    if len(tickers) < 2:
        st.error("Enter at least two tickers.")
        st.stop()
    if start_date >= end_date:
        st.error("Start date must be before end date.")
        st.stop()

    with st.spinner(f"Downloading price history for {len(tickers)} tickers..."):
        try:
            prices = download_prices(tickers, start_date, end_date)
        except Exception as e:
            st.error(f"Failed to download data: {e}")
            st.stop()

    missing = [t for t in tickers if t not in prices.columns or prices[t].isna().all()]
    if missing:
        st.warning(f"No data returned for: {', '.join(missing)}. Dropping from analysis.")
    prices = prices.dropna(axis=1, how="all")

    if prices.shape[1] < 2:
        st.error("Not enough valid tickers with data to compare.")
        st.stop()

    returns = prices.pct_change(fill_method=None).dropna()

    if returns.shape[0] < 3:
        st.error("Not enough overlapping trading days in this date range to compute correlations.")
        st.stop()

    st.session_state["results_df"] = compute_correlations(returns)
    st.session_state["returns"] = returns

if "results_df" in st.session_state:
    results_df = st.session_state["results_df"]
    returns = st.session_state["returns"]

    trading_days = returns.shape[0]

    st.markdown(describe_selection(returns.columns))

    with st.expander("How this works", expanded=False):
        st.caption(
            f"We compared **{len(results_df)}** different stock pairs, using about "
            f"**{trading_days}** days of trading history for each one "
            f"({describe_span(trading_days)}). A pair only counts as reliable if "
            "there's a very low chance the pattern happened by random luck."
        )
        st.markdown(
            "We look at both the direction and size of each day's price move for both "
            "stocks — do they tend to go up and down together, and by similar amounts, "
            "not just occasionally match by chance? This is checked across all "
            f"{trading_days} days and summarized into one score from -1 to 1. You can "
            "see this visually in the scatter plot below: tightly clustered dots along "
            "a rising line mean a high score (strong relationship), a scattered cloud "
            "with no pattern means a low score (little to no relationship)."
        )

    st.subheader("Correlation & significance for every pair")

    grouped_df = add_relationship_column(results_df)
    avg_by_group = (
        grouped_df.groupby("Relationship")["Correlation"].mean().sort_values(ascending=False)
    )
    within_groups = [g for g in avg_by_group.index if g.startswith("Within ")]
    cross_groups = [g for g in avg_by_group.index if not g.startswith("Within ")]

    for i, group in enumerate(within_groups + cross_groups):
        group_df = grouped_df[grouped_df["Relationship"] == group]
        group_sig = (group_df["Significant?"] == "Yes").sum()
        with st.expander(
            f"{group} — {len(group_df)} pairs, {group_sig} significant",
            expanded=(i == 0),
        ):
            display_df = group_df[PAIR_TABLE_COLUMNS].copy()
            display_df["Significant?"] = display_df["Significant?"].map(significance_label)
            st.dataframe(
                display_df.style.apply(
                    style_significance, axis=1, subset=["Significant?"]
                ),
                column_config=PAIR_COLUMN_CONFIG,
                width="stretch",
                hide_index=True,
            )

    n_significant = (results_df["Significant?"] == "Yes").sum()
    st.caption(
        f"**{n_significant}** of those **{len(results_df)}** comparisons showed a "
        "pattern that's likely real, not just chance. The rest could easily be "
        "coincidence. One caveat: when testing this many pairs at once, a few will "
        "look 'real' purely by luck, even if they aren't."
    )

    st.subheader("Inspect a pair")
    st.caption("Pick any two stocks in the analysis — related or not — to compare directly.")
    all_stocks = list(returns.columns)

    col_a, col_b = st.columns(2)
    with col_a:
        stock_a = st.selectbox("Stock A", all_stocks, index=0)
    with col_b:
        stock_b = st.selectbox("Stock B", all_stocks, index=1 if len(all_stocks) > 1 else 0)

    if stock_a == stock_b:
        st.info("Pick two different stocks to compare.")
    else:
        pair_match = results_df[
            ((results_df["Stock 1"] == stock_a) & (results_df["Stock 2"] == stock_b))
            | ((results_df["Stock 1"] == stock_b) & (results_df["Stock 2"] == stock_a))
        ]
        pair_row = pair_match.iloc[0]
        corr_value = pair_row["Correlation"]
        p_value = pair_row["P-Value"]
        is_significant = pair_row["Significant?"] == "Yes"

        m1, m2, m3 = st.columns(3)
        m1.metric("Correlation", f"{corr_value:.3f}")
        m2.metric("P-Value", f"{p_value:.4f}")
        m3.metric("Statistically significant?", significance_label(pair_row["Significant?"]))

        point_color = SIG_GREEN if is_significant else NOT_SIG_GRAY
        line_color = SIG_GREEN_LINE if is_significant else NOT_SIG_RED_LINE

        scatter_fig = px.scatter(
            returns,
            x=stock_a,
            y=stock_b,
            trendline="ols",
            title=f"Daily returns: {stock_a} vs {stock_b}",
            labels={
                stock_a: f"{stock_a} daily return",
                stock_b: f"{stock_b} daily return",
            },
            color_discrete_sequence=[point_color],
            trendline_color_override=line_color,
        )
        scatter_fig.update_xaxes(tickformat=".1%")
        scatter_fig.update_yaxes(tickformat=".1%")
        st.plotly_chart(scatter_fig, use_container_width=True)
        st.caption(
            "Dot and line color reflect whether this relationship is statistically "
            "reliable (green/blue = likely real, gray/red = could be chance)."
        )

        strength = correlation_strength(corr_value)
        if is_significant:
            verdict = (
                "and this **is** statistically significant, meaning this pattern "
                "is likely real."
            )
        else:
            verdict = (
                "and this **is not** statistically significant, meaning this could "
                "easily be random chance."
            )
        st.markdown(
            f"**{stock_a}** and **{stock_b}** show **{strength}** correlation "
            f"(**{corr_value:.2f}**), {verdict}"
        )

    st.subheader("Inference")
    relationship_summary = build_relationship_summary(results_df)
    st.dataframe(
        relationship_summary.style.format({
            "Avg Correlation": "{:.2f}",
            "% Significant": "{:.0f}%",
        }),
        width="stretch",
    )
    st.markdown(generate_inference_text(relationship_summary))

    csv = results_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download results as CSV", csv, "correlation_results.csv", "text/csv")
else:
    st.info("Set your tickers and date range in the sidebar, then click **Run analysis**.")
