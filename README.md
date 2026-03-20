# 🌍 HostAfrica Weekly FYI Generator

An AI-powered Streamlit app that automatically scans HostAfrica's regional websites and compiles a polished weekly FYI report for your team — in the warm, professional tone your team loves.

---

## Features

- 🔍 **Auto-scrapes** all HostAfrica regional sites: `.COM`, `.CO.ZA`, `.KE`, `.NG`, `.GH`
- 🤖 **Claude AI** analyses the content and writes the FYI report
- 📄 **Report history** — view, download, and copy past reports
- 🗺️ **Site Explorer** — drill into any site's scraped content
- ➕ **Easily extensible** — add new TLDs in one place (`site_config.py`)
- ⬇️ **Download** reports as Markdown or copy raw text for Slack/Teams/WhatsApp

---

## Setup

### 1. Clone / upload to GitHub
Push this folder to a GitHub repo (public or private).

### 2. Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **New app**
3. Select your repo and set **Main file path** to `app.py`
4. Click **Deploy**

### 3. Set your Google Gemini API Key
Get your key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

**Option A (recommended for teams):** Add it as a Streamlit Secret:
- In your Streamlit Cloud dashboard → App settings → **Secrets**
- Add:
```toml
GEMINI_API_KEY = "AIza..."
```
Then in `app.py`, replace the sidebar API key input with:
```python
import os
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
```

**Option B:** Enter the key in the sidebar each session (current default — safe for personal use).

---

## Adding New HostAfrica Domains

Open `site_config.py` and add a new entry to `HOSTAFRICA_SITES`:

```python
"hostafrica.com.tz": {
    "label": "HostAfrica Tanzania (.TZ)",
    "base_url": "https://hostafrica.com.tz",
    "flag": "🇹🇿",
    "key_pages": [
        "/",
        "/blog/",
        "/vps-hosting/",
        "/web-hosting/",
    ],
},
```

That's it — it'll appear in the sidebar and be included in future scans automatically.

---

## File Structure

```
hostafrica-fyi/
├── app.py               # Main Streamlit app
├── site_config.py       # Site registry + web scraper
├── ai_reporter.py       # Claude AI report generation
├── report_store.py      # Report history (JSON file-based)
├── requirements.txt     # Python dependencies
├── .streamlit/
│   └── config.toml      # Theme config
└── README.md
```

---

## Running Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Notes

- Reports are saved as Markdown files in a `reports/` folder (auto-created).
- On Streamlit Cloud's free tier, the `reports/` folder resets on redeploy. For persistent storage, consider connecting a GitHub-backed store or Streamlit's experimental data persistence.
- The scraper is polite — it uses standard HTTP requests with a browser User-Agent. No JavaScript rendering is required for HostAfrica's pages.
