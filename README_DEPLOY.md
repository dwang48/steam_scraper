# Steam Daily Crawler

This package contains **one** production-ready script – `steam_daily.py` – which:

1. Downloads the full Steam app list every time it runs.
2. Detects **new** app_ids (i.e. IDs never seen before).
3. Fetches rich metadata for each new app.
4. Exports `exports/new_games_YYYY-MM-DD.csv` with the following columns:

   * type  
   * name  
   * steam_appid  
   * developers  
   * header_image  
   * website  
   * publishers  
   * categories  
   * genres  
   * steam_url

5. E-mails the CSV to the configured recipient.
6. Stores the master list of known app_ids in `steam_data/applist.json` so subsequent
   runs only include brand-new titles.

---

## 1. Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Environment variables

Create a `.env` (or set in your shell):

```bash
SMTP_HOST=smtp.yourprovider.com
SMTP_PORT=587  # or 465 for SSL
SMTP_USER=your_smtp_username
SMTP_PASS=your_smtp_password
TO_EMAIL=recipient@example.com
FROM_EMAIL=steam-bot@example.com  # optional – defaults to SMTP_USER
```

> `python-dotenv` is included; values in `.env` are automatically loaded when
> you run the script.

## 3. One-off run

```bash
python steam_daily.py
```

If this is the first run, the script will cache the full app list and exit with
"No new app_ids detected."  Subsequent runs will emit a CSV & e-mail.

## 4. Daily cron (08:00 PT)

Edit the crontab (`crontab ‑e`) **on a server whose system time is UTC**:

```
0 16 * * * /usr/bin/env bash -c 'cd /opt/steam_crawler && source venv/bin/activate && python steam_daily.py > logs/$(date +\%F).log 2>&1'
```

16:00 UTC == 08:00 Pacific Time. Adjust if your host uses a different timezone.

## 5. Files to deploy

• `steam_daily.py` – the main script  
• `requirements.txt`  
• `README_DEPLOY.md` (this file)  
• `steam_data/` (empty; will be populated automatically)  
• `exports/`   (empty)

Everything else in the repo is **development artefacts** and can be removed for
production. 