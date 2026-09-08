"""Price watcher: checks product pages on a schedule, logs prices to CSV,
and sends an email alert when a price drops below your target.

Setup:
  pip install requests beautifulsoup4
  Edit WATCHES below (url, css selector for the price, target price).
  Optional: fill in the SMTP settings to get email alerts on drops.

Run once:      python price_watch.py
Run forever:   python price_watch.py --loop        (checks every CHECK_MINUTES)

Demo targets point at books.toscrape.com, a site built for scraping practice,
so you can run this out of the box and see it work.
"""
import argparse
import csv
import os
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# --- your watches ---------------------------------------------------------
WATCHES = [
    {
        "name": "A Light in the Attic",
        "url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        "selector": "p.price_color",
        "target": 60.00,          # alert if price goes below this
    },
    {
        "name": "Tipping the Velvet",
        "url": "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html",
        "selector": "p.price_color",
        "target": 50.00,
    },
]

# email alerts (optional). Works with Gmail app passwords or any SMTP server.
SMTP_HOST = os.environ.get("SMTP_HOST", "")        # e.g. smtp.gmail.com
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
ALERT_TO = os.environ.get("ALERT_TO", "")          # where alerts go

CSV_FILE = "price_history.csv"
CHECK_MINUTES = 30
HEADERS = {"User-Agent": "Mozilla/5.0 (price-watch script)"}
# --------------------------------------------------------------------------


def get_price(url, selector):
    """Fetch the page and pull the first number out of the price element."""
    for attempt in range(3):                      # retry: one bad load shouldn't kill the run
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            el = BeautifulSoup(r.text, "html.parser").select_one(selector)
            if el is None:
                return None
            m = re.search(r"[\d,]+\.?\d*", el.get_text())
            return float(m.group().replace(",", "")) if m else None
        except requests.RequestException:
            time.sleep(5 * (attempt + 1))
    return None


def alert(subject, msg):
    print("ALERT:", msg)
    if not (SMTP_HOST and SMTP_USER and ALERT_TO):
        return
    try:
        import smtplib
        from email.message import EmailMessage
        em = EmailMessage()
        em["From"] = SMTP_USER
        em["To"] = ALERT_TO
        em["Subject"] = subject
        em.set_content(msg)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(em)
    except Exception as e:
        print(f"  (email alert failed: {e})")       # alert failing shouldn't crash the watcher


def log_row(name, price):
    new_file = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["timestamp", "product", "price"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), name, price])


def check_all():
    for item in WATCHES:
        price = get_price(item["url"], item["selector"])
        if price is None:
            print(f"  {item['name']}: couldn't read price (site change? selector?)")
            continue
        log_row(item["name"], price)
        below = price < item["target"]
        print(f"  {item['name']}: {price:.2f}" + ("  <-- below target!" if below else ""))
        if below:
            alert(f"Price alert: {item['name']} at {price:.2f}",
                  f"{item['name']} dropped to {price:.2f} (target {item['target']:.2f})\n{item['url']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", action="store_true", help="keep checking every CHECK_MINUTES")
    args = ap.parse_args()
    while True:
        print(f"[{datetime.now():%Y-%m-%d %H:%M}] checking {len(WATCHES)} products...")
        check_all()
        if not args.loop:
            break
        time.sleep(CHECK_MINUTES * 60)


if __name__ == "__main__":
    main()
