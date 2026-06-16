# ⚽ World Cup 2026 Predictions App

A Streamlit app for tracking all 104 World Cup 2026 matches and competing with friends on exact-score predictions.

---

## Features

- **Live match calendar** — all 104 fixtures pulled from the free [openfootball](https://github.com/openfootball/worldcup.json) API (no key needed, updates daily as results come in)
- **User accounts** — register/login with username & password (hashed)
- **Predictions** — pick an exact score for any upcoming match, edit anytime before kick-off
- **Leaderboard** — only exact scores count; ranked with 🥇🥈🥉 medals
- **My Predictions** — personal table showing all picks, results, and status
- **Google Sheets backend** — zero infrastructure, free forever

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up Google Sheets

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use an existing one)
3. Enable **Google Sheets API** and **Google Drive API**
4. Create a **Service Account** → generate a JSON key
5. Copy the contents into `.streamlit/secrets.toml`:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# then paste your service account JSON fields into it
```

The app will **automatically create** a spreadsheet called `WC2026_Predictions` with two sheets:
- `Users` — stores usernames and hashed passwords
- `Predictions` — stores all match predictions

> **Tip:** The spreadsheet is created with public "writer" access so all service account users can contribute. You can restrict this in Google Sheets settings once created.

### 3. Run
```bash
streamlit run app.py
```

---

## Deploying to Streamlit Community Cloud (free)

1. Push this folder to a GitHub repo
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app → connect your repo
3. In the app settings → **Secrets**, paste your `[gcp_service_account]` block
4. Deploy → share the URL with friends!

---

## Match Data Source

Matches are fetched from:
```
https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json
```

This is a community-maintained, public domain dataset. Results are updated manually (roughly once per day). The app caches data for 5 minutes.

---

## Scoring Rules

- ✅ **Exact score** = 1 point (e.g. you picked 2–1 and the result was 2–1)
- ❌ Correct winner but wrong score = 0 points
- ⏳ Match not yet played = pending

Only exact scores count — making it genuinely difficult and exciting!
