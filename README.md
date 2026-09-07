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
5. Displays everything in an interactive Streamlit UI, written for people who don't speak
   statistics:
   - **Industry-based selection** — pick one or more industries (US Tech, US Finance,
     US Healthcare, Indian IT, Indian Banking, Indian Energy & Manufacturing) from a
     dropdown, and the ticker list fills in automatically. A second dropdown lets you add
     or remove individual tickers, drawing on every ticker across all industries, so you
     aren't limited to the groups you picked.
   - **Grouped results tables** — instead of one long flat list, pairs are split into
     collapsible sections by relationship: "Within Indian IT", "Within US Tech",
     "Indian IT vs US Tech", and so on. Each section header shows how many pairs it
     holds and how many are reliable, with the first section open by default.
   - **Plain-English labels** — rather than a bare "Yes"/"No", each pair is marked
     **✓ Likely real** (green) or **✗ Could be chance** (red). Hovering any column header
     gives a one-line definition, with the technical term in parentheses for anyone who
     wants it. The correlation column doubles as an inline bar, so relative strength is
     visible at a glance next to the number.
   - **Inspect a pair** — two dropdowns, Stock A and Stock B, let you compare *any* two
     stocks in the analysis, related or not. You get the correlation, the p-value, and a
     scatter plot of the two stocks' daily returns with an OLS trend line. The dots and
     line are coloured by significance (green when the relationship is likely real, grey
     with a red trend line when it could be chance), plus a sentence spelling out what
     the pair's particular result means.
   - **A collapsible "How this works" explainer** — the longer walkthrough of what's being
     measured sits behind an expander, collapsed by default, so returning users skip
     straight to the numbers.
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

Running the app's default selection — **Indian IT** and **US Tech** — over roughly the last
two years (444 trading days) gives 171 pairs, of which 98 come back as likely real. Grouping
those pairs by relationship is where it gets interesting:

| Relationship | Pairs | Avg correlation | % likely real |
|---|---|---|---|
| Within Indian IT | 36 | 0.58 | 100% |
| Within US Tech | 45 | 0.33 | 100% |
| Indian IT vs US Tech | 90 | 0.06 | 19% |

- **Same-industry pairs hold up.** Every single within-industry pair, in both countries,
  passed the significance test. The strongest were `COFORGE.NS` / `PERSISTENT.NS` (0.77) and
  `INFY.NS` / `TCS.NS` (0.76) — believable, since these companies share a sector, a currency,
  a trading calendar and the same macro news.
- **Cross-country pairs mostly don't.** Of the 90 Indian-IT-vs-US-Tech pairs, only 19% were
  statistically significant, averaging a correlation of just 0.06. Two large, famous tech
  companies on opposite sides of the world mostly do *not* move together day to day.
- **The best illustration of the whole point:** `MSFT` and `TCS.NS` came out at a correlation
  of 0.092 with a p-value of **0.053**. That's a real-looking number that lands just barely on
  the wrong side of the 0.05 cutoff — so the app labels it **✗ Could be chance**. Eyeballing
  the correlation alone, you'd probably have called that a weak-but-real relationship. The
  significance test says don't.

This is exactly the distinction the tool is built to surface: a correlation number alone
doesn't tell you whether a relationship is real. You need the significance test alongside it.

*(One practical note: `LTIM.NS` gets dropped automatically in this run — Yahoo Finance no
longer returns data for that symbol. The app warns you which tickers were dropped rather than
silently shrinking your sample.)*

## Note on limitations

With many pairs tested at once — the default selection alone produces 171 — some correlations
are expected to look "significant" at the 0.05 threshold by chance alone, even if nothing real
is going on. This is known as the multiple comparisons problem. This tool reports the standard
per-pair p-value as a first pass; treat any single "likely real" result with proportionally
more skepticism as the number of pairs you test grows.

## Tools used

- **Python** — the language.
- **yfinance** — free stock price history, no signup needed.
- **pandas** — data wrangling.
- **scipy** — the `pearsonr` function, which computes correlation and p-value in one call.
- **streamlit** — the interactive UI.
- **plotly** — the interactive return scatter plots.
- **statsmodels** — fits the OLS trend line drawn through the scatter plot.
