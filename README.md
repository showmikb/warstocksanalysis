# War-Time Stock Performance Analyzer

Analyses how defence, energy, and commodity stocks performed during 10 major wars (1990–2023). Compares Open prices on the first and last trading day of a 60-day window after each war started. Generates an HTML report with tables, heatmaps, and per-stock charts.

## Prerequisites

### macOS

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Git and Python 3
brew install git python
```

### Windows

1. Download and install Git from https://git-scm.com/download/win
2. Download and install Python from https://www.python.org/downloads/
   - During installation, **check "Add Python to PATH"**

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install git python3 python3-pip python3-venv
```

## Installation

```bash
# Clone the repository
git clone https://github.com/showmikb/warstocksanalysis.git
cd warstocksanalysis

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# macOS / Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Run

```bash
python warstocks.py
```

This will:
1. Fetch historical stock data from Yahoo Finance
2. Print war-wise and per-stock tables in the terminal
3. Generate an HTML report at `report/war_stock_report.html` and open it in your browser

## Configuration

Edit the top of `warstocks.py` to customize:

| Variable | Description | Default |
|----------|-------------|---------|
| `WINDOW_DAYS` | Calendar days after war start to measure | `60` |
| `WARS` | List of wars with name and start date | 10 wars (1990–2023) |
| `CANDIDATE_STOCKS` | Stocks to track (ticker, name, country, industry) | 11 stocks (US + India) |

## Stocks Tracked

| Ticker | Company | Country | Sector |
|--------|---------|---------|--------|
| GD | General Dynamics | US | Defence |
| RTX | Raytheon Technologies | US | Defence |
| NOC | Northrop Grumman | US | Defence |
| LMT | Lockheed Martin | US | Defence |
| XOM | Exxon Mobil | US | Energy |
| CVX | Chevron | US | Energy |
| BEL.NS | Bharat Electronics | India | Defence |
| BHEL.NS | Bharat Heavy Electricals | India | Defence/Industrial |
| IOC.NS | Indian Oil Corp | India | Energy |
| ONGC.NS | Oil & Natural Gas Corp | India | Energy |
| HINDALCO.NS | Hindalco Industries | India | Metals |

## Output

- **Terminal**: War-wise tables and per-stock summaries
- **HTML Report** (`report/war_stock_report.html`):
  - Heatmap of all stocks across all wars
  - Win count chart (how many wars each stock went up)
  - Average gain chart (mean return when stock went up)
  - Per-stock bar charts across all wars
  - War-wise breakdown tables

## Data Source

All price data is fetched from [Yahoo Finance](https://finance.yahoo.com/) via the [yfinance](https://github.com/ranaroussi/yfinance) library. Prices are adjusted for stock splits and dividends.
