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
    base_url = "https://www.nseindia.com"
    api_url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "application/json",
        "Connection": "keep-alive"
    }

    session = requests.Session()

    # Step 1: Visit homepage to get cookies
    session.get(base_url, headers=headers, timeout=10)

    # Step 2: Call API using same session
    response = session.get(api_url, headers=headers, timeout=10)

    if response.status_code != 200:
        raise Exception(f"NSE API blocked or failed: {response.status_code}")

    data = response.json()

    # Safety check
    if "records" not in data:
        raise Exception("NSE returned unexpected response. Possibly blocked.")

    return data

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
