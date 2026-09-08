# price-watch-automation

Checks product pages on a schedule, logs prices to CSV, emails you when a price drops below your target.

Retries failed page loads. An alert failure won't crash the watcher. Demo points at books.toscrape.com so it runs out of the box.

```
pip install requests beautifulsoup4
python price_watch.py          # one pass
python price_watch.py --loop   # every 30 min
```

Email alerts: set SMTP_HOST / SMTP_USER / SMTP_PASS / ALERT_TO env vars (Gmail app passwords work).
