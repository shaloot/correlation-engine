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


def style_significance(row):
    color = "background-color: #1a4d2e" if row["Significant?"] == "Yes" else "background-color: #4d1a1a"
    return [color] * len(row)


def industry_of(ticker):
    for industry, tks in industry_tickers.items():
        if ticker in tks:
            return industry
    return "Other"


def build_relationship_summary(results_df):
    rel_df = results_df.copy()
    rel_df["Industry 1"] = rel_df["Stock 1"].map(industry_of)
    rel_df["Industry 2"] = rel_df["Stock 2"].map(industry_of)
    rel_df["Relationship"] = rel_df.apply(
        lambda r: f"Within {r['Industry 1']}"
        if r["Industry 1"] == r["Industry 2"]
        else " vs ".join(sorted([r["Industry 1"], r["Industry 2"]])),
        axis=1,
    )
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

    st.subheader("Correlation & significance for every pair")
    st.caption(
        f"{len(results_df)} pairs from {returns.shape[0]} trading days. "
        f"'Significant?' uses the standard p < {SIGNIFICANCE_LEVEL} cutoff — "
        "below that, the correlation is unlikely to be pure chance."
    )
    st.dataframe(
        results_df.style.apply(style_significance, axis=1),
        use_container_width=True,
    )

    n_significant = (results_df["Significant?"] == "Yes").sum()
    st.caption(
        f"{n_significant} of {len(results_df)} pairs are statistically significant. "
        "Note: at a 0.05 threshold, some 'significant' results are expected by "
        "chance alone when testing many pairs at once."
    )

    st.subheader("Inspect a pair")
    top_pairs = results_df.head(15).copy()
    top_pairs["Pair"] = top_pairs["Stock 1"] + " vs " + top_pairs["Stock 2"]
    selected_pair = st.selectbox(
        "Choose one of the top 15 correlated pairs to see its daily returns",
        top_pairs["Pair"],
    )
    pair_row = top_pairs[top_pairs["Pair"] == selected_pair].iloc[0]
    s1, s2 = pair_row["Stock 1"], pair_row["Stock 2"]

    scatter_fig = px.scatter(
        returns,
        x=s1,
        y=s2,
        trendline="ols",
        title=f"Daily returns: {s1} vs {s2}",
        labels={s1: f"{s1} daily return", s2: f"{s2} daily return"},
    )
    scatter_fig.update_xaxes(tickformat=".1%")
    scatter_fig.update_yaxes(tickformat=".1%")
    st.plotly_chart(scatter_fig, use_container_width=True)

    st.subheader("Inference")
    relationship_summary = build_relationship_summary(results_df)
    st.dataframe(
        relationship_summary.style.format({
            "Avg Correlation": "{:.2f}",
            "% Significant": "{:.0f}%",
        }),
        use_container_width=True,
    )
    st.markdown(generate_inference_text(relationship_summary))

    csv = results_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download results as CSV", csv, "correlation_results.csv", "text/csv")
else:
    st.info("Set your tickers and date range in the sidebar, then click **Run analysis**.")
