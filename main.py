from dotenv import load_dotenv
from twilio.rest import Client
from datetime import datetime as dt, timedelta as td
import requests
import os

load_dotenv()

# Calling all relevant APIs:
stock_api_key = os.getenv('STOCK_API')
news_api_key = os.getenv('NEWS_API')
twillio_account_SID = os.getenv('ACCOUNT_SID')
twillio_auth_token = os.getenv('AUTH_TOKEN')

# Stock and company name to look into (can be customized):
STOCK = "TSLA"
COMPANY_NAME = "Tesla Inc"

# Setting the API end point for stock price check and News fetching:
STOCK_ENDPOINT = "https://www.alphavantage.co/query"
NEWS_ENDPOINT = "https://newsapi.org/v2/everything"

stock_parameters = {
    "function": "TIME_SERIES_DAILY",
    "symbol": STOCK,
    "outputsize": "compact",
    "apikey": stock_api_key,
}

# Using the Stock endpoint to fetch stock prices on relevant days:
stock_connection = requests.get(STOCK_ENDPOINT, params=stock_parameters)
stock_connection.raise_for_status()
stock_http_code = stock_connection.status_code
stock_data = stock_connection.json()

date_today = dt.now()
weekday_today = date_today.weekday()

_today = str(date_today)
_1day_ago = str(date_today - td(days=1))
_2days_ago = str(date_today - td(days=2))
_3days_ago = str(date_today - td(days=3))
_4days_ago = str(date_today - td(days=4))

date_today = _today.split(" ")[0]
date_1day_ago = _1day_ago.split(" ")[0]
date_2days_ago = _2days_ago.split(" ")[0]
date_3days_ago = _3days_ago.split(" ")[0]
date_4days_ago = _4days_ago.split(" ")[0]


def check_stock_close():
    """Calculates the percentage of difference between yesterday's close and before yesterday's close and takes into
    consideration weekends, in which it calculates the difference on the last 2 work days"""
    try:
        _1day_ago_close = float(stock_data["Time Series (Daily)"][date_1day_ago]["4. close"])
        _2days_ago_close = float(stock_data["Time Series (Daily)"][date_2days_ago]["4. close"])
        difference = _1day_ago_close - _2days_ago_close
        difference_percentage = round((difference/_1day_ago_close)*100, 2)
        print(f"Yesterday, Tesla stock's moved by: {difference_percentage}%")
    except KeyError:
        # If today is a Sunday:
        try:
            _2days_ago_close = float(stock_data["Time Series (Daily)"][date_2days_ago]["4. close"])
            _3days_ago_close = float(stock_data["Time Series (Daily)"][date_3days_ago]["4. close"])
            difference = _2days_ago_close - _3days_ago_close
            difference_percentage = round((difference / _2days_ago_close) * 100, 2)
            print(f"Yesterday was a Saturday, Tesla stock's on Friday moved by: {difference_percentage}%")
        except KeyError:
            # If today is a Monday:
            try:
                _3days_ago_close = float(stock_data["Time Series (Daily)"][date_3days_ago]["4. close"])
                _4days_ago_close = float(stock_data["Time Series (Daily)"][date_4days_ago]["4. close"])
                difference = _3days_ago_close - _4days_ago_close
                difference_percentage = round((difference / _3days_ago_close) * 100, 2)
                print(f"Yesterday was a Sunday, Tesla stock's on Friday moved by: {difference_percentage}%")
            except KeyError:
                # If today is a Tuesday:
                _1days_ago_close = float(stock_data["Time Series (Daily)"][date_1day_ago]["4. close"])
                _4days_ago_close = float(stock_data["Time Series (Daily)"][date_4days_ago]["4. close"])
                difference = _1days_ago_close - _4days_ago_close
                difference_percentage = round((difference / _1days_ago_close) * 100, 2)
                print(f"Yesterday, Tesla stock's moved by: {difference_percentage}%")
    return difference_percentage


change_percentage = check_stock_close()


def news_date():
    """Returns the relevant date on which to check the news as the stock market is closed on the weekend"""
    if weekday_today == 6:
        return date_2days_ago
    else:
        return date_1day_ago


news_date = news_date()
print(f"Fetching relevant {COMPANY_NAME} news on {news_date}...")

news_parameters = {"q": COMPANY_NAME,
                   "apiKey": news_api_key,
                   "from": news_date,
                   }

# Using the News API endpoint, we fetch the news from the indicated news date:
news_connection = requests.get("https://newsapi.org/v2/everything?", params=news_parameters)
news_connection.raise_for_status()
new_http_code = news_connection.status_code
news_data = news_connection.json()


def get_news(percentage):
    """Checks if the stock price difference is significant enough (5% change) to fetch the news and organize the first
    three relevant articles from various sources in a readable format"""
    articles = news_data["articles"]
    news_dict = {}
    if abs(percentage) >= 5:
        for element in range(3):
            title = articles[element]["title"]
            url = articles[element]["url"]
            description = articles[element]["description"]
            news_dict[f"title {element+1}"] = title
            news_dict[f"url {element+1}"] = url
            news_dict[f"description {element+1}"] = description
        if percentage < 0:
            sign = "🔻"
        else:
            sign = "🔺"
        body = (f"{STOCK}: {sign}{abs(percentage)}%\n"
                f"Headline 1: {news_dict["title 1"]}\n"
                f"Brief: {news_dict["description 1"]}\n"
                f"Link: {news_dict["url 1"]}\n\n"
                f"Headline 2: {news_dict["title 2"]}\n"
                f"Brief: {news_dict["description 2"]}\n"
                f"Link: {news_dict["url 2"]}\n\n"
                f"Headline 3: {news_dict["title 3"]}\n"
                f"Brief: {news_dict["description 3"]}\n"
                f"Link: {news_dict["url 3"]}")

        send_notification(body)
    else:
        print("Nothing to report")


def send_notification(body):
    """Calls Twillio API to send the news articles and price difference as an SMS from the indicated number to the
    indicated recipient's number"""
    client = Client(twillio_account_SID, twillio_auth_token)

    message = client.messages.create(body=body,
                                     from_="number of sender",
                                     to="number of recipient")

    print("Report sent successfully!")


get_news(change_percentage)
