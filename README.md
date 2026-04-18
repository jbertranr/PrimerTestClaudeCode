# Swiss Job Finder 🇨🇭

Automated daily job search for French-speaking Switzerland (Romandy).  
Every morning it scrapes Swiss job portals, filters relevant postings, and sends a digest to Telegram.

Optionally generates personalised cover letters in French using the Claude API (requires an Anthropic API key — disabled by default).

---

## Features

- Scrapes **jobup.ch**, **jobs.ch**, **LinkedIn** and **Indeed Switzerland** daily
- Targets **Romandy** (Genève, Vaud, Neuchâtel, Fribourg, Valais)
- Two job categories: **Hospitality/Restaurant** and **Tourism**
- Deduplication via SQLite — never see the same job twice
- Sends a daily **Telegram** digest (job cards + optional cover letter files)
- Optional **email** digest via SMTP
- Optional **French cover letter generation** via Claude API (disabled by default)
- Runs as a cron job, systemd timer, or Python daemon

---

## Quick Start

### 1. Clone and install

```bash
git clone <repo-url>
cd swiss-job-finder
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set up credentials

```bash
cp .env.example .env
```

Edit `.env` and fill in your Telegram credentials (minimum required):

```
TELEGRAM_BOT_TOKEN=...   # from @BotFather on Telegram
TELEGRAM_CHAT_ID=...     # your personal chat ID
```

#### How to get your Telegram credentials

1. Open Telegram, search `@BotFather`
2. Send `/newbot` → follow the steps → copy the token
3. Start a chat with your new bot, send any message
4. Open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser
5. Find `"chat":{"id":XXXXXXX}` — that number is your `TELEGRAM_CHAT_ID`

### 3. Configure your search

Edit `config.yaml` — you can change keywords, locations, cantons, and schedule.  
Arnaud's profile is already filled in.

### 4. Run

```bash
python main.py
```

Results print to the console if Telegram is disabled, or are sent to Telegram if enabled.

---

## Enable Telegram notifications

In `config.yaml`:
```yaml
notifications:
  telegram:
    enabled: true
```

---

## Enable cover letter generation (optional)

Only if you have an Anthropic API key:

1. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`
2. In `config.yaml` set: `llm: enabled: true`

Cover letters are generated in French, tailored to each job posting, and sent as `.txt` file attachments on Telegram.

---

## Deploying on PythonAnywhere (recommended — free)

[PythonAnywhere](https://www.pythonanywhere.com) runs the script every day for free with a persistent database.

### Step-by-step

**1. Create a free account** at [pythonanywhere.com](https://www.pythonanywhere.com)

**2. Open a Bash console** — click *Dashboard → New console → Bash*

**3. Run the setup script:**
```bash
curl -fsSL https://raw.githubusercontent.com/jbertranr/primertestclaudecode/claude/initial-testing-setup-e5dFn/setup_pythonanywhere.sh | bash
```
This clones the repo, creates a virtualenv, installs dependencies, and initialises the database.

**4. Add your Telegram credentials:**
```bash
nano ~/swiss-job-finder/.env
```
Fill in `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` (see README section below for how to get these).

**5. Enable Telegram in the config:**
```bash
nano ~/swiss-job-finder/config.yaml
```
Set `notifications > telegram > enabled: true`

**6. Test a manual run:**
```bash
~/swiss-job-finder/.venv/bin/python ~/swiss-job-finder/main.py
```
You should receive a Telegram message within a minute.

**7. Schedule the daily task:**
- Go to *Dashboard → Tasks*
- Click *Add a new scheduled task*
- Set time: `08:00`
- Command:
```
/home/YOUR_USERNAME/swiss-job-finder/.venv/bin/python /home/YOUR_USERNAME/swiss-job-finder/main.py
```
(Replace `YOUR_USERNAME` with your PythonAnywhere username)

That's it — Arnaud will receive a Telegram message every morning with new jobs.

### Important note on PythonAnywhere free tier

The free tier restricts outbound HTTP to a whitelist of major domains. **LinkedIn and Indeed** (via `python-jobspy`) will work fine. **jobup.ch** and **jobs.ch** may be blocked — but you'll still get results from LinkedIn and Indeed every day. To unlock all sources, upgrade to the $5/month Hacker plan.

---

## Running daily automatically (alternative methods)

### Option A — cron (simplest)

```bash
crontab -e
# Add (runs at 08:00 Zurich time = 06:00 UTC in summer):
0 6 * * * /path/to/.venv/bin/python /path/to/swiss-job-finder/main.py >> /var/log/swiss-job-finder.log 2>&1
```

### Option B — Python daemon (APScheduler)

```bash
python scheduler.py
```

### Option C — systemd timer (VPS, recommended)

```bash
sudo cp deploy/systemd/swiss-job-finder.service /etc/systemd/system/
sudo cp deploy/systemd/swiss-job-finder.timer /etc/systemd/system/
# Edit the paths in the .service file to match your install location
sudo systemctl enable --now swiss-job-finder.timer
sudo journalctl -u swiss-job-finder.service -f
```

---

## Project Structure

```
swiss-job-finder/
├── main.py              # Entry point — run this
├── scheduler.py         # Daemon mode (APScheduler)
├── config.yaml          # All user settings
├── .env                 # Secrets (not committed)
├── scrapers/            # Job board scrapers
│   ├── base.py          # Job dataclass
│   ├── jobspy_scraper.py   # LinkedIn + Indeed
│   ├── jobup_scraper.py    # jobup.ch
│   └── jobs_ch_scraper.py  # jobs.ch
├── storage/
│   └── database.py      # SQLite deduplication
├── llm/
│   ├── claude_client.py # Anthropic API wrapper
│   └── prompts.py       # Cover letter prompts
├── notifications/
│   ├── telegram_bot.py  # Telegram digest
│   └── email_sender.py  # Email digest (optional)
├── templates/
│   └── cover_letter_context.j2  # Jinja2 prompt template
├── tests/               # Unit tests
└── deploy/              # systemd + cron configs
```

---

## Running tests

```bash
pip install pytest
pytest tests/
```

---

## Notes for Swiss job market

- Swiss employers often prefer local/EU candidates — a Swiss work reference (like the Glacier Express) is a major advantage. Always mention it.
- Jobs in Romandy are posted primarily on **jobup.ch** and **LinkedIn**.
- Tourist/mountain resort jobs in Valais (Verbier, Crans-Montana, Zermatt) are seasonal — best application window is September–November for winter season and March–May for summer season.
- Sending a physical letter to HR departments, in addition to online applications, is still common in Switzerland and can make a difference.
