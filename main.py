from dotenv import load_dotenv
import os

import yfinance as yf
from datetime import date, timedelta
from flask import Flask, redirect, url_for, render_template, request, session, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

load_dotenv('.env')
app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.permanent_session_lifetime = timedelta(minutes=5)

db = SQLAlchemy(app)
TICKER = ''
multiple_stocks = []

@app.route("/favicon.ico")
def favicon():
    return "", 204

def todays_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="5d")

        if data.empty:
            print(f"[ERROR] No data returned for {ticker}")
            return None

        latest = data.iloc[-1]
        return round(latest['Open'], 2), round(latest['Close'], 2)
    except Exception as e:
        print(f"[ERROR] Failed to get today's price for {ticker}: {e}")
        return None

def yesterday_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="5d")

        if len(data) < 2:
            return 0.0, 0.0

        yesterday = data.iloc[-2]
        return round(yesterday['Open'], 2), round(yesterday['Close'], 2)
    except Exception as e:
        print(f"[ERROR] Failed to get yesterday's price for {ticker}: {e}")
        return 0.0, 0.0

def daily_change(ticker):
    _, y_close = yesterday_price(ticker)
    t_price = todays_price(ticker)
    if t_price is None:
        return 0, 'no_data'
    _, t_close = t_price

    if t_close == 0:
        return 0, 'no_data'

    change = round((1 - (y_close / t_close)) * 100, 2)
    if 5 > change > 0:
        return change, "lit_pos"
    elif change > 5:
        return change, "very_pos"
    elif -5 < change < 0:
        return change, "lit_neg"
    elif change < -5:
        return change, "very_neg"
    else:
        return change, "neutral"

def change_price(ticker):
    _, y_close = yesterday_price(ticker)
    t_price = todays_price(ticker)
    if t_price is None:
        return 0.0
    _, t_close = t_price
    return t_close - y_close

def get_popular_stocks():
    tickers = ["AAPL", "GOOGL", "AMZN"]
    result = []
    for t in tickers:
        try:
            price_result = todays_price(t)
            if price_result is None:
                continue
            _, price = price_result
            if price == 0.0:
                continue
            chg = change_price(t)
            chg_pct, color = daily_change(t)
            result.append({
                "ticker": t,
                "price": round(price, 2),
                "change": round(chg, 2),
                "change_percent": round(chg_pct, 2),
                "change_color": color
            })
        except Exception as e:
            print(f"[ERROR] Failed to fetch data for {t}: {e}")
    return result

class stores_stocks(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    User_login = db.Column(db.String(100), nullable=False, default='')
    ticker = db.Column(db.String(100), nullable=False, default='')

    def __init__(self, login, ticker):
        self.User_login = login
        self.ticker = ticker

class single_stock():
    def __init__(self, ticker, price, change, change_color):
        self.ticker = ticker
        self.price = price
        self.change = change
        self.change_color = change_color

@app.route("/", methods=["POST", "GET"])
@app.route("/home", methods=["GET"])
def home():
    popular_stocks = get_popular_stocks()
    if request.method == "POST":
        TICKER = request.form['tkr'].upper()
        return redirect(url_for("view_single", tkr=TICKER))
    return render_template("home.html", popular_stocks=popular_stocks)

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        session.permanent = True
        loginId = request.form["loginId"]
        session.clear()
        session["loginId"] = loginId
        session["stocks"] = []

        found = stores_stocks.query.filter_by(User_login=loginId).first()
        if not found:
            flash("Not an Existing User! Create a New One")
            return redirect(url_for("create"))
        else:
            if found.ticker:
                session["stocks"] = found.ticker.split(",")
            flash("Login Successful!")
            return redirect(url_for("view"))
    else:
        if "loginId" in session:
            flash("Already Logged In")
            return redirect(url_for("view"))
        return render_template("login.html")

@app.route("/createUser", methods=["POST", "GET"])
def create():
    if "loginId" not in session:
        if request.method == "POST":
            loginId = request.form["loginId"]
            if stores_stocks.query.filter_by(User_login=loginId).first():
                flash("User Already Exists, Please Enter a New Username")
                return render_template("create_user.html")
            session["stocks"] = []
            db.session.add(stores_stocks(loginId, ''))
            db.session.commit()
            flash(f"User {loginId} Created!")
            return redirect(url_for("view"))
    return render_template("create_user.html")

@app.route("/view", methods=["POST", "GET"])
def view():
    if "loginId" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    login_id = session["loginId"]
    login_user = stores_stocks.query.filter_by(User_login=login_id).first()
    tickers = session.get("stocks", [])

    if request.method == "POST":
        TICKER = request.form['tkr'].upper()
        if TICKER and TICKER not in tickers:
            if todays_price(TICKER) is None:
                flash(f"No data found for '{TICKER}'. Please enter a valid stock symbol.")
                return redirect(url_for("view"))
            tickers.append(TICKER)
            session["stocks"] = tickers
            login_user.ticker = ",".join(tickers)
            db.session.commit()
        else:
            flash("Stock Already Shown or Invalid!")

    user_stocks = []
    for t in tickers:
        price_result = todays_price(t)
        if price_result is None:
            continue
        _, price = price_result
        chg, clr = daily_change(t)
        user_stocks.append(single_stock(t, price, chg, clr))

    return render_template("view.html", stocks=user_stocks)

@app.route("/logout")
def logout():
    if "loginId" in session:
        flash(f"You have been logged out, {session['loginId']}!")
    session.clear()
    return redirect(url_for("login"))

@app.route("/clear_db", methods=["POST", "GET"])
def clear_db():
    db.drop_all()
    db.create_all()
    return redirect(url_for("home"))

@app.route("/<tkr>")
def view_single(tkr):
    if not tkr.isalpha() or len(tkr) > 5:
        return "", 204

    price_result = todays_price(tkr)
    if price_result is None:
        flash(f"No data found for '{tkr}'. Please enter a valid stock symbol.")
        return redirect(url_for("home"))

    _, price = price_result
    chg, clr = daily_change(tkr)
    stock = single_stock(tkr, price, chg, clr)
    return render_template("view_single.html", stock=stock)

@app.route("/view-multiple", methods=["POST", "GET"])
def view_multiple():
    if request.method == "POST":
        TICKER = request.form['tkr'].upper()
        price_result = todays_price(TICKER)
        if price_result is None:
            flash(f"No data found for '{TICKER}'. Please enter a valid stock symbol.")
            return redirect(url_for("view_multiple"))
        _, price = price_result
        chg, clr = daily_change(TICKER)
        stock = single_stock(TICKER, price, chg, clr)
        if any(s.ticker == TICKER for s in multiple_stocks):
            flash("Stock Already Shown!")
        else:
            multiple_stocks.append(stock)
    return render_template("view_multiple.html", stocks=multiple_stocks)

@app.route("/app_remove_stock", methods=["POST"])
def user_remove_stock():
    if "loginId" not in session:
        flash("Please log in.")
        return redirect(url_for("login"))

    login_id = session["loginId"]
    login_user = stores_stocks.query.filter_by(User_login=login_id).first()
    t_remove = request.form['tkr'].upper()

    session["stocks"] = [t for t in session.get("stocks", []) if t != t_remove]

    if login_user:
        current = login_user.ticker.split(",") if login_user.ticker else []
        if t_remove in current:
            current.remove(t_remove)
            login_user.ticker = ",".join(current)
            db.session.commit()

    flash(f"Removed {t_remove}")
    return redirect(url_for("view"))

@app.route("/remove_stock", methods=["POST", "GET"])
def remove_stock():
    t_remove = request.form['tkr'].upper()
    global multiple_stocks
    multiple_stocks = [s for s in multiple_stocks if s.ticker != t_remove]
    flash(f"Removed {t_remove}")
    return redirect(url_for("view_multiple"))

if __name__ == "__main__":
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Tables created successfully.")
    app.run(debug=True)