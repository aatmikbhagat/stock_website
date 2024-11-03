from dotenv import load_dotenv
import os

import yfinance as yf
from datetime import date, datetime, timedelta
import pandas as pd 

from flask import Flask, redirect, url_for, render_template, request, session, flash 
from datetime import timedelta, time
from flask_sqlalchemy import SQLAlchemy 


today = date.today()
yesterday = today - timedelta(days = 1)
tomorrow = today + timedelta(days = 1)

app = Flask(__name__)

load_dotenv('.env')
key: str = os.getenv('SECRET_KEY')
app.secret_key = key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.permanent_session_lifetime = timedelta(minutes=5)

db = SQLAlchemy(app)
TICKER = ''

multiple_stocks = []
user_multiple_stocks=[]


def adjust_to_weekday(given_date):
    now = datetime.now().time()

    market_open_time = time(9, 30)

    if now < market_open_time:
        print(f"Time is before market open. Adjusting to the previous day's close.")
        given_date -= timedelta(days=1)

    if given_date.weekday() >= 5:  # Saturday (5) or Sunday (6)
        given_date -= timedelta(days=(given_date.weekday() - 4))
    
    return given_date


def daily_change(date, ticker):
    change = 0 
    change_color = ''
    date = adjust_to_weekday(date)
    _,yesterday_close = yesterday_price(date, ticker)
    _, today_close = todays_price(date, ticker)
    price_unrounded = (1 - (yesterday_close / today_close)) * 100
    change = round(price_unrounded, 2)
    if 5 > change > 0:
        change_color = "lit_pos"
    elif change > 5:
        change_color = "very_pos"
    elif -5 < change < 0:
        change_color = "lit_neg"
    elif change < -5: 
        change_color = "very_neg"
    return change, change_color

def change_price(date, ticker):
    change = 0
    date = adjust_to_weekday(date)
    _,yesterday_close = yesterday_price(date, ticker)
    _, today_close = todays_price(date, ticker)

    change = today_close - yesterday_close

    return change


def todays_price(date, ticker):
    date = adjust_to_weekday(date)
    today = date
    tomorrow = date + timedelta(days = 1)

    data = yf.download(tickers=ticker, start=today, end=tomorrow, period="1d", interval="1d")

    open_price = round(data['Open'].iloc[0],2)
    close_price = round(data['Close'].iloc[0],2)
    return open_price,close_price


def yesterday_price(date, ticker):

    yesterday = date - timedelta(days = 1)

    open_price, close_price = todays_price(yesterday, ticker)
    return open_price, close_price

def get_popular_stocks():
    popular_tickers = ["AAPL", "GOOGL", "AMZN"] 
    popular_stocks = []

    for ticker in popular_tickers:
        stock_data = yf.Ticker(ticker)
        _, price = todays_price(today, ticker)
        change = change_price(today,ticker)
        change_percent, change_color = daily_change(today, ticker)

        popular_stocks.append({
            "ticker": ticker,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "change_color": change_color
        })
    
    return popular_stocks


class stores_stocks(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    User_login = db.Column(db.String(100), nullable=False, default='')
    ticker = db.Column(db.String(100), nullable=False, default='')

    def __init__(self, login, ticker, change, change_price):
        self.User_login = login
        self.ticker = ticker


class single_stock():
    ticker = ''
    price = 0.0
    change = 0.0
    change_color = ''
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
        TICKER = request.form['tkr']
        return redirect(url_for("view_single",tkr=TICKER))
    return render_template("home.html", popular_stocks=popular_stocks)


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        session.permanent = True
        loginId = request.form["loginId"]
        
        session.clear()
        
        session["loginId"] = loginId
        session["stocks"] = [] 

        found_login = stores_stocks.query.filter_by(User_login=loginId).first()
        

        if not found_login:
            session.clear()
            flash(f"Not an Existing User! Create a New One")
            return redirect(url_for("create"))
        else:
            if found_login.ticker:
                session["stocks"] = found_login.ticker.split(",")  #
            flash(f"Login Successful!")

        return redirect(url_for("view"))  
    else: 
        if "loginId" in session:
            flash("Already Logged In")
            return redirect(url_for("view"))
        return render_template("login.html")

@app.route("/createUser", methods=["POST","GET"])
def create():
    if "loginId" not in session:
        if request.method == "POST":
            loginId = request.form["loginId"]
            if(stores_stocks.query.filter_by(User_login=loginId).first()):
                flash("User Already Exists, Please Enter a New Username")
                return render_template("create_user.html")
            session["stocks"] = []

            stock = stores_stocks(loginId, '', 0, 0)
            db.session.add(stock)
            db.session.commit()

            flash(f"User {loginId} Created!")
            return redirect(url_for("view"))

    return render_template("create_user.html")

@app.route("/view", methods=["POST", "GET"])
def view():
    if "loginId" in session:
        login_id = session["loginId"]

        login_user = stores_stocks.query.filter_by(User_login=login_id).first()
        if not login_user:
            flash("User not found.")
            return redirect(url_for("login"))

        list_of_tickers = session.get("stocks", [])

        if request.method == "POST":
            TICKER = request.form['tkr'].upper()
            if TICKER and TICKER not in list_of_tickers:
                list_of_tickers.append(TICKER)
                session["stocks"] = list_of_tickers
                login_user.ticker = ",".join(list_of_tickers)
                db.session.commit()
            else:
                flash("Stock Already Shown , Please Choose Another One!")

        user_multiple_stocks = []
        for ticker in list_of_tickers:
            _, price = todays_price(today, ticker)
            change, change_color = daily_change(today, ticker)
            stock = single_stock(ticker, price, change, change_color)
            user_multiple_stocks.append(stock)
        
        return render_template("view.html", stocks=user_multiple_stocks)
    else:
        flash("Not Logged In, Please Login to Continue")
        return redirect(url_for("login"))


@app.route("/logout")
def logout():
    if "loginId" in session:
        loginId = session["loginId"]
        flash(f"You have been logged out, {loginId}!")
        
    session.clear()
    return redirect(url_for("login"))


@app.route("/clear_db", methods=["POST","GET"])
def clear_db():
    # Drop all tables
    db.drop_all()
    # Create all tables again
    db.create_all()
    return redirect(url_for("home"))


@app.route("/<tkr>")
def view_single(tkr):
    TICKER = tkr
    _, price = todays_price(today, TICKER)
    change, change_color = daily_change(today, TICKER)
    stock = single_stock(TICKER, price, change, change_color)

    return render_template("view_single.html", stock = stock)

@app.route("/view-multiple", methods=["POST","GET"])
def view_multiple():
    if request.method == "POST":
        TICKER = request.form['tkr'].upper()
        _, price = todays_price(today, TICKER)
        change, change_color = daily_change(today, TICKER)
        stock = single_stock(TICKER, price, change, change_color)
        ticker_exists = any(s.ticker == TICKER for s in multiple_stocks)
        if ticker_exists:
            flash("Stock Already Shown, Please Choose Another One!")
        else:
            multiple_stocks.append(stock)

    return render_template("view_multiple.html", stocks=multiple_stocks)

@app.route("/app_remove_stock", methods=["POST"])
def user_remove_stock():
    if "loginId" in session:
        login_id = session["loginId"]

        # Get the user from the database
        login_user = stores_stocks.query.filter_by(User_login=login_id).first()

        # Get the ticker to remove from the form submission
        ticker_to_remove = request.form['tkr'].upper()

        # Remove the stock from the session
        if "stocks" in session:
            session["stocks"] = [stock for stock in session["stocks"] if stock != ticker_to_remove]

        # Update the user's stock list in the database
        if login_user:
            user_stocks = login_user.ticker.split(",") if login_user.ticker else []
            if ticker_to_remove in user_stocks:
                user_stocks.remove(ticker_to_remove)
                # Update the user's stock list in the database
                login_user.ticker = ",".join(user_stocks)  # Join the list back to a comma-separated string
                db.session.commit()

        flash(f"Stock {ticker_to_remove} removed successfully!")
        return redirect(url_for("view"))
    else:
        flash("Please log in to continue.")
        return redirect(url_for("login"))


@app.route("/remove_stock", methods=["POST", "GET"])
def remove_stock():
    ticker_to_remove = request.form['tkr'].upper()
    global multiple_stocks
    multiple_stocks = [stock for stock in multiple_stocks if stock.ticker != ticker_to_remove]
    flash(f"Stock {ticker_to_remove} removed successfully!")
    return redirect(url_for("view_multiple"))



if __name__ == "__main__":
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Tables created successfully.")
    app.run(debug=True)
    
