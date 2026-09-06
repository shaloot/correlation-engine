# Stock Correlation Engine

## The problem

During an internship, I was given data and asked to find patterns in it. I found what looked
like a trend, but had no way to check whether it was a real relationship or just something
that happened to look that way by chance in that particular dataset — the same way flipping
two coins 10 times can, purely by luck, land the same way 7 times and *look* correlated even
though the coins have nothing to do with each other.

This project is a tool that answers that question properly for stock prices: given a list of
stocks, does Company A's price actually tend to move with Company B's — and is that
relationship statistically real, or likely coincidence?

## What it does

1. Downloads daily closing prices for a list of stocks (via `yfinance`).
2. Converts prices into daily percentage returns, so a stock's moves are compared fairly
   regardless of its price level.
3. Calculates the Pearson correlation between every pair of stocks.
4. Runs a significance test (p-value) on each correlation — a low p-value (< 0.05) means
   the relationship is unlikely to be pure chance; a high p-value means it could easily be
   coincidence, even if the correlation number looks impressive.
5. Displays everything in an interactive Streamlit UI:
   - Pick one or more **industries** (US Tech, US Finance, US Healthcare, Indian IT,
     Indian Banking, Indian Energy & Manufacturing), then add or remove individual
     tickers as needed.
   - A sortable results table of every pair, colour-coded by significance.
   - **Inspect a pair** — pick any of the top correlated pairs and see a scatter plot of
     the two stocks' daily returns with an OLS trend line through the points.
   - An **Inference** section that groups pairs into within-industry vs cross-industry
     (and cross-country), reports average correlation and % significant for each group,
     and explains in plain English what the pattern suggests and why.

## How to run it

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

This opens the app at `http://localhost:8501`. Choose your industries and date range in
the sidebar, then click **Run analysis**.

## Deploying it

This is a Streamlit app, which needs a live Python process — so it **cannot** run on
GitHub Pages (static hosting only). To put it online for free, use
[Streamlit Community Cloud](https://share.streamlit.io): sign in with GitHub, point it at
this repo, and set the main file to `app.py`.

## Findings from a sample run

Using `TCS.NS, INFY.NS, HDFCBANK.NS, RELIANCE.NS, TATAMOTORS.NS, AAPL, MSFT, GOOGL, JPM, TSLA`
over 2023-09-04 to 2025-09-04:

- **INFY.NS and TCS.NS** — two Indian IT companies — showed a strong, statistically
  significant correlation (0.71, p < 0.0001). This is a genuine pattern: same sector, likely
  driven by shared industry and macro factors.
- **AAPL and TCS.NS**, on the other hand, showed a weak correlation (0.06) that was *not*
  statistically significant (p = 0.185) — despite being large, well-known companies, there's
  no trustworthy relationship between their daily moves, and treating that number as
  meaningful would be a mistake.

This is exactly the distinction the tool is built to surface: a correlation number alone
doesn't tell you whether a relationship is real. You need the significance test alongside it.

## Note on limitations

With many pairs tested at once (e.g. 45 pairs for 10 stocks), some correlations are expected
to look "significant" at the 0.05 threshold by chance alone, even if nothing real is going on
— this is known as the multiple comparisons problem. This tool reports the standard per-pair
p-value as a first pass; treat any single "significant" result with proportionally more
skepticism as the number of pairs you test grows.

## Tools used

- **Python** — the language.
- **yfinance** — free stock price history, no signup needed.
- **pandas** — data wrangling.
- **scipy** — the `pearsonr` function, which computes correlation and p-value in one call.
- **streamlit** — the interactive UI.
- **plotly** — the interactive correlation heatmap.
