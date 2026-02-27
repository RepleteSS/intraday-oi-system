from flask import Flask
import requests
import os
from openai import OpenAI
from datetime import datetime

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com"
}

session = requests.Session()
session.get("https://www.nseindia.com", headers=HEADERS)

def fetch_option_chain(symbol):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    response = session.get(url, headers=HEADERS)
    return response.json()

def process_data(data):
    records = data['records']['data']
    spot = data['records']['underlyingValue']

    call_oi = {}
    put_oi = {}

    for item in records:
        strike = item['strikePrice']
        if 'CE' in item:
            call_oi[strike] = item['CE']['openInterest']
        if 'PE' in item:
            put_oi[strike] = item['PE']['openInterest']

    max_call = max(call_oi, key=call_oi.get)
    max_put = max(put_oi, key=put_oi.get)

    total_call = sum(call_oi.values())
    total_put = sum(put_oi.values())
    pcr = round(total_put / total_call, 2)

    return {
        "spot": spot,
        "pcr": pcr,
        "max_call_strike": max_call,
        "max_put_strike": max_put
    }

def generate_post(nifty, banknifty):
    prompt = f"""
Generate intraday posts using:

NIFTY:
Spot: {nifty['spot']}
PCR: {nifty['pcr']}
Resistance: {nifty['max_call_strike']}
Support: {nifty['max_put_strike']}

BANKNIFTY:
Spot: {banknifty['spot']}
PCR: {banknifty['pcr']}
Resistance: {banknifty['max_call_strike']}
Support: {banknifty['max_put_strike']}

Output:
1) WhatsApp Version
2) LinkedIn Version
3) X Version (under 280 characters)
Professional structured tone.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

@app.route("/")
def home():
    return "Intraday OI Automation Running"

@app.route("/run")
def run_analysis():
    nifty_raw = fetch_option_chain("NIFTY")
    banknifty_raw = fetch_option_chain("BANKNIFTY")

    nifty = process_data(nifty_raw)
    banknifty = process_data(banknifty_raw)

    post = generate_post(nifty, banknifty)

    return f"<pre>{post}</pre>"

if __name__ == "__main__":
    app.run()