# Stock_website
# 📈 Stock Tracker Web App

A responsive web application built with **Flask**, **YFinance**, and **SQLite** that allows users to track real-time stock prices, view daily percentage changes, and manage personalized watchlists.

## 🚀 Features

- 🔍 Search for any stock ticker (e.g., AAPL, GOOGL, AMZN)
- 📊 View live stock price, daily change, and percentage difference
- ✅ Register and log in to create a personal watchlist
- ➕ Add/remove multiple stocks from your dashboard
- ⚠️ Error handling for invalid or unavailable tickers
- 💾 Persistent user data using SQLite and Flask SQLAlchemy
- 🖥️ Simple and clean UI using Flask templates (Jinja2)

## 🛠️ Tech Stack

- **Python 3**
- **Flask**
- **YFinance** (for financial data)
- **SQLite** (for user data)
- **HTML/CSS (Jinja Templates)**

## 📦 Installation

```bash
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt