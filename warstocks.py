"""
Find which pre-selected stocks went up after major wars started, and by how much.
Generates an HTML report with tables and graphs for each stock.

Requirements:
    pip install yfinance pandas tabulate matplotlib seaborn

Usage:
    python warstocks.py
    # Opens report/war_stock_report.html in your browser
"""

import base64
import datetime as dt
import io
import os
import webbrowser
from typing import List, Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import pandas as pd
import yfinance as yf
from tabulate import tabulate


# ========= CONFIG =========

WINDOW_DAYS = 60

WARS: List[Dict[str, str]] = [
    {"name": "Gulf War",                "date": "1990-08-02"},
    {"name": "Kargil War",              "date": "1999-05-03"},
    {"name": "9/11 & Afghanistan War",  "date": "2001-10-07"},
    {"name": "Iraq War",                "date": "2003-03-20"},
    {"name": "Russia-Georgia War",      "date": "2008-08-08"},
    {"name": "Libya Intervention",      "date": "2011-03-19"},
    {"name": "Crimea Annexation",       "date": "2014-02-27"},
    {"name": "US Strikes on Syria",     "date": "2017-04-07"},
    {"name": "Russia-Ukraine War",      "date": "2022-02-24"},
    {"name": "Israel-Hamas War",        "date": "2023-10-07"},
]

CANDIDATE_STOCKS: Dict[str, Dict] = {
    "GD":           {"name": "General Dynamics",         "country": "US",    "industry": "Defence"},
    "RTX":          {"name": "Raytheon Technologies",    "country": "US",    "industry": "Defence"},
    "NOC":          {"name": "Northrop Grumman",         "country": "US",    "industry": "Defence"},
    "LMT":          {"name": "Lockheed Martin",          "country": "US",    "industry": "Defence"},
    "BA":           {"name": "Boeing",                   "country": "US",    "industry": "Defence/Aerospace"},
    "XOM":          {"name": "Exxon Mobil",              "country": "US",    "industry": "Energy"},
    "CVX":          {"name": "Chevron",                  "country": "US",    "industry": "Energy"},
    "BEL.NS":       {"name": "Bharat Electronics",       "country": "India", "industry": "Defence"},
    "BHEL.NS":      {"name": "Bharat Heavy Electricals", "country": "India", "industry": "Defence/Industrial"},
    "IOC.NS":       {"name": "Indian Oil Corp",          "country": "India", "industry": "Energy"},
    "ONGC.NS":      {"name": "Oil & Natural Gas Corp",   "country": "India", "industry": "Energy"},
    "HINDALCO.NS":  {"name": "Hindalco Industries",      "country": "India", "industry": "Metals"},
}

REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report")


# ========= DATA LOGIC =========

def get_war_window(start_date_str: str, window_days: int):
    start = dt.datetime.fromisoformat(start_date_str)
    end = start + dt.timedelta(days=window_days)
    return start, end


def fetch_prices_for_window(tickers: List[str],
                            start: dt.datetime,
                            end: dt.datetime) -> pd.DataFrame:
    """Download Open prices for all tickers in the window (split/dividend adjusted)."""
    data = yf.download(tickers=tickers, start=start, end=end,
                       auto_adjust=True, progress=False)
    if data.empty:
        return data

    col = "Open"
    if isinstance(data.columns, pd.MultiIndex):
        level_0_vals = data.columns.get_level_values(0)
        if col in level_0_vals:
            prices = data[col]
        else:
            prices = data.xs(col, axis=1, level=1)
    else:
        prices = data[[col]]
        if len(tickers) == 1:
            prices = prices.rename(columns={col: tickers[0]})
    return prices


def compute_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Open-to-Open % change: first trading day to last trading day in window."""
    results = []
    for ticker in prices.columns:
        series = prices[ticker].dropna()
        if series.empty or len(series) < 2:
            continue
        start_price = float(series.iloc[0])
        end_price = float(series.iloc[-1])
        if start_price == 0:
            continue
        pct = (end_price - start_price) / start_price * 100.0
        results.append({
            "ticker": ticker,
            "start_price": round(start_price, 2),
            "end_price": round(end_price, 2),
            "pct_change": round(pct, 2),
        })
    return pd.DataFrame(results)


def collect_all_data(tickers: List[str]) -> pd.DataFrame:
    """Fetch returns for every war and return a single master DataFrame."""
    all_rows = []
    for war in WARS:
        start_dt, end_dt = get_war_window(war["date"], WINDOW_DAYS)
        prices = fetch_prices_for_window(tickers, start_dt, end_dt)
        if prices.empty:
            continue
        returns_df = compute_returns(prices)
        for _, row in returns_df.iterrows():
            info = CANDIDATE_STOCKS.get(row["ticker"], {})
            all_rows.append({
                "war": war["name"],
                "war_date": war["date"],
                "ticker": row["ticker"],
                "company": info.get("name", ""),
                "country": info.get("country", ""),
                "industry": info.get("industry", ""),
                "open_start": row["start_price"],
                "open_end": row["end_price"],
                "pct_change": row["pct_change"],
            })
    return pd.DataFrame(all_rows)


# ========= CHART HELPERS =========

def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def make_heatmap(master: pd.DataFrame) -> str:
    """Stocks (rows) x Wars (columns) heatmap of % change. Returns base64 PNG."""
    pivot = master.pivot_table(index="company", columns="war",
                               values="pct_change", aggfunc="first")
    war_order = [w["name"] for w in WARS]
    pivot = pivot[[c for c in war_order if c in pivot.columns]]

    fig, ax = plt.subplots(figsize=(16, 7))
    sns.heatmap(pivot, annot=True, fmt=".1f", center=0,
                cmap="RdYlGn", linewidths=0.5, ax=ax,
                cbar_kws={"label": "% Change"})
    ax.set_title("Stock Performance Across Wars  (Open-to-Open, 60-day window)",
                 fontsize=14, fontweight="bold", pad=12)
    ax.set_ylabel("")
    ax.set_xlabel("")
    plt.xticks(rotation=35, ha="right", fontsize=9)
    plt.yticks(fontsize=9)
    return _fig_to_base64(fig)


def make_stock_chart(stock_df: pd.DataFrame, ticker: str, company: str) -> str:
    """Bar chart of a single stock's % change across wars. Returns base64 PNG."""
    df = stock_df.copy()
    war_order = [w["name"] for w in WARS]
    df["war"] = pd.Categorical(df["war"], categories=war_order, ordered=True)
    df = df.sort_values("war")

    colors = ["#2ecc71" if v > 0 else "#e74c3c" for v in df["pct_change"]]

    fig, ax = plt.subplots(figsize=(12, 5))
    bars = ax.bar(df["war"], df["pct_change"], color=colors, edgecolor="white", width=0.6)

    for bar, val in zip(bars, df["pct_change"]):
        y_off = 1.2 if val >= 0 else -2.5
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + y_off,
                f"{val:+.1f}%", ha="center", va="bottom" if val >= 0 else "top",
                fontsize=9, fontweight="bold")

    ax.axhline(0, color="grey", linewidth=0.8)
    ax.set_title(f"{company}  ({ticker})", fontsize=14, fontweight="bold", pad=10)
    ax.set_ylabel("% Change (Open-to-Open)")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%+.0f%%"))
    plt.xticks(rotation=35, ha="right", fontsize=9)
    sns.despine()
    return _fig_to_base64(fig)


def make_wins_summary_chart(master: pd.DataFrame) -> str:
    """Horizontal bar: number of wars each stock went UP. Returns base64 PNG."""
    wins = master[master["pct_change"] > 0].groupby("company").size().sort_values()
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = sns.color_palette("YlGn", len(wins))
    wins.plot.barh(ax=ax, color=colors, edgecolor="white")
    for i, (v, name) in enumerate(zip(wins, wins.index)):
        ax.text(v + 0.15, i, str(v), va="center", fontweight="bold")
    ax.set_title("Number of Wars Where Stock Went UP  (out of 10)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Wars with positive return")
    ax.set_ylabel("")
    ax.set_xlim(0, wins.max() + 1.5)
    sns.despine()
    return _fig_to_base64(fig)


def make_avg_return_chart(master: pd.DataFrame) -> str:
    """Horizontal bar: average % return across all wars (only positive wars)."""
    pos = master[master["pct_change"] > 0]
    avg = pos.groupby("company")["pct_change"].mean().sort_values()
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = sns.color_palette("YlGn", len(avg))
    avg.plot.barh(ax=ax, color=colors, edgecolor="white")
    for i, (v, name) in enumerate(zip(avg, avg.index)):
        ax.text(v + 0.3, i, f"{v:.1f}%", va="center", fontweight="bold")
    ax.set_title("Average Gain When Stock Went UP",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Avg % Change (winning wars only)")
    ax.set_ylabel("")
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%+.0f%%"))
    sns.despine()
    return _fig_to_base64(fig)


# ========= HTML REPORT =========

def build_html(master: pd.DataFrame) -> str:
    sections = []

    # --- header ---
    sections.append(f"""
    <h1>War-Time Stock Performance Report</h1>
    <p class="subtitle">
        {len(CANDIDATE_STOCKS)} stocks &middot; {len(WARS)} wars &middot;
        {WINDOW_DAYS}-day window &middot; Open-to-Open price comparison
    </p>
    """)

    # --- heatmap ---
    heatmap_b64 = make_heatmap(master)
    sections.append(f"""
    <h2>Overview Heatmap</h2>
    <img src="data:image/png;base64,{heatmap_b64}" class="chart">
    """)

    # --- win count + avg return ---
    wins_b64 = make_wins_summary_chart(master)
    avg_b64 = make_avg_return_chart(master)
    sections.append(f"""
    <div class="row">
        <div class="col"><img src="data:image/png;base64,{wins_b64}" class="chart"></div>
        <div class="col"><img src="data:image/png;base64,{avg_b64}" class="chart"></div>
    </div>
    """)

    # --- war-wise tables ---
    sections.append("<h2>War-wise Breakdown</h2>")
    for war in WARS:
        wdf = master[master["war"] == war["name"]].copy()
        if wdf.empty:
            continue
        wdf = wdf.sort_values("pct_change", ascending=False)
        winners = wdf[wdf["pct_change"] > 0]
        losers = wdf[wdf["pct_change"] <= 0]

        sections.append(f"<h3>{war['name']}  <span class='date'>({war['date']})</span></h3>")

        if not winners.empty:
            sections.append("<p class='label up'>WENT UP</p>")
            sections.append(_df_to_html_table(winners))
        if not losers.empty:
            sections.append("<p class='label down'>WENT DOWN (or flat)</p>")
            sections.append(_df_to_html_table(losers))

    # --- per-stock charts (only stocks that went up at least once) ---
    sections.append("<h2>Per-Stock Performance Across Wars</h2>")
    up_tickers = master[master["pct_change"] > 0]["ticker"].unique()
    for ticker in sorted(up_tickers):
        info = CANDIDATE_STOCKS.get(ticker, {})
        company = info.get("name", ticker)
        stock_df = master[master["ticker"] == ticker]
        chart_b64 = make_stock_chart(stock_df, ticker, company)

        wins = int((stock_df["pct_change"] > 0).sum())
        total = len(stock_df)
        avg_up = stock_df[stock_df["pct_change"] > 0]["pct_change"].mean()
        avg_up_str = f"{avg_up:+.2f}%" if not pd.isna(avg_up) else "N/A"

        sections.append(f"""
        <div class="stock-card">
            <h3>{company} ({ticker})
                <span class="badge">{info.get('country','')} &middot; {info.get('industry','')}</span>
            </h3>
            <p>Went up in <strong>{wins}/{total}</strong> wars &middot;
               Avg gain (when up): <strong>{avg_up_str}</strong></p>
            <img src="data:image/png;base64,{chart_b64}" class="chart">
        </div>
        """)

    return _wrap_html("\n".join(sections))


def _df_to_html_table(df: pd.DataFrame) -> str:
    display = df[["ticker", "company", "country", "industry",
                  "open_start", "open_end", "pct_change"]].copy()
    display.columns = ["Ticker", "Company", "Country", "Industry",
                       "Open Start", "Open End", "Change %"]
    display["Change %"] = display["Change %"].apply(
        lambda v: f"+{v:.2f}%" if v > 0 else f"{v:.2f}%")
    return display.to_html(index=False, classes="data-table", border=0)


def _wrap_html(body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>War-Time Stock Report</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa; color: #2c3e50; padding: 30px 50px; }}
    h1 {{ font-size: 28px; margin-bottom: 4px; }}
    h2 {{ font-size: 22px; margin: 35px 0 15px; border-bottom: 2px solid #3498db; padding-bottom: 6px; }}
    h3 {{ font-size: 17px; margin: 20px 0 8px; }}
    .subtitle {{ color: #7f8c8d; margin-bottom: 25px; font-size: 15px; }}
    .date {{ color: #95a5a6; font-weight: normal; font-size: 14px; }}
    .badge {{ background: #ecf0f1; padding: 2px 10px; border-radius: 12px;
              font-size: 12px; font-weight: normal; margin-left: 8px; }}
    .label {{ font-weight: 700; margin: 10px 0 4px; font-size: 14px; }}
    .label.up {{ color: #27ae60; }}
    .label.down {{ color: #c0392b; }}
    .chart {{ max-width: 100%; margin: 10px 0 20px; border-radius: 8px;
              box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
    .row {{ display: flex; gap: 20px; flex-wrap: wrap; }}
    .col {{ flex: 1; min-width: 400px; }}
    .stock-card {{ background: #fff; border-radius: 10px; padding: 20px 25px;
                   margin-bottom: 25px; box-shadow: 0 2px 10px rgba(0,0,0,0.06); }}
    .data-table {{ border-collapse: collapse; width: 100%; margin: 6px 0 16px; font-size: 13px; }}
    .data-table th {{ background: #34495e; color: #fff; padding: 8px 12px; text-align: left; }}
    .data-table td {{ padding: 7px 12px; border-bottom: 1px solid #ecf0f1; }}
    .data-table tr:hover {{ background: #f9f9f9; }}
</style></head><body>
{body}
<p style="margin-top:40px;color:#bdc3c7;font-size:12px;">
    Generated on {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} &middot;
    Data source: Yahoo Finance (yfinance) &middot; Prices adjusted for splits &amp; dividends
</p>
</body></html>"""


# ========= MAIN =========

def main():
    tickers = list(CANDIDATE_STOCKS.keys())
    print(f"Tracking {len(tickers)} stocks across {len(WARS)} wars")
    print(f"Window: {WINDOW_DAYS} days after war start  |  Price: Open-to-Open\n")

    print("Fetching data from Yahoo Finance...")
    master = collect_all_data(tickers)

    if master.empty:
        print("No data returned. Check network / tickers.")
        return

    # --- console output: war-wise tables ---
    for war in WARS:
        wdf = master[master["war"] == war["name"]].copy()
        if wdf.empty:
            continue
        wdf = wdf.sort_values("pct_change", ascending=False)

        print("=" * 90)
        print(f"  {war['name']}  ({war['date']})  —  {WINDOW_DAYS}-day window")
        print("=" * 90)

        display = wdf[["ticker", "company", "country", "industry",
                        "open_start", "open_end", "pct_change"]].copy()
        display.columns = ["Ticker", "Company", "Country", "Industry",
                           "Open Start", "Open End", "Change %"]
        display["Change %"] = display["Change %"].apply(
            lambda v: f"+{v:.2f}%" if v > 0 else f"{v:.2f}%")
        print(tabulate(display, headers="keys", tablefmt="pretty",
                        showindex=False, numalign="right", stralign="left"))
        print()

    # --- per-stock summary ---
    print("=" * 90)
    print("  PER-STOCK SUMMARY (wars where stock went UP)")
    print("=" * 90)
    for ticker in sorted(CANDIDATE_STOCKS.keys()):
        info = CANDIDATE_STOCKS[ticker]
        sdf = master[master["ticker"] == ticker]
        if sdf.empty:
            continue
        wins = sdf[sdf["pct_change"] > 0]
        print(f"\n  {info['name']} ({ticker})  —  UP in {len(wins)}/{len(sdf)} wars")
        if not wins.empty:
            display = wins[["war", "open_start", "open_end", "pct_change"]].copy()
            display.columns = ["War", "Open Start", "Open End", "Change %"]
            display["Change %"] = display["Change %"].apply(lambda v: f"+{v:.2f}%")
            print(tabulate(display, headers="keys", tablefmt="pretty",
                            showindex=False, numalign="right", stralign="left"))

    # --- generate HTML report ---
    print("\nGenerating HTML report with graphs...")
    os.makedirs(REPORT_DIR, exist_ok=True)
    html = build_html(master)
    report_path = os.path.join(REPORT_DIR, "war_stock_report.html")
    with open(report_path, "w") as f:
        f.write(html)

    print(f"Report saved to: {report_path}")
    webbrowser.open(f"file://{report_path}")


if __name__ == "__main__":
    main()
