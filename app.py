"""
app.py — HostAfrica Weekly FYI Generator
Main Streamlit application entry point.
"""

import streamlit as st
from datetime import datetime

from site_config import HOSTAFRICA_SITES, scrape_site
from ai_reporter import generate_report, generate_site_summary
from report_store import save_report, list_reports, load_report, get_latest_report, delete_report

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="HostAfrica FYI Generator",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# LOAD API KEY FROM STREAMLIT SECRETS ONLY
# ─────────────────────────────────────────────
def get_api_key() -> str | None:
    """Load Gemini API key exclusively from Streamlit secrets."""
    try:
        return st.secrets["GEMINI_API_KEY"]
    except (KeyError, FileNotFoundError):
        return None

API_KEY = get_api_key()

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .site-card {
        background: #1A1D27;
        border: 1px solid #2D3147;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    .site-card.ok      { border-left: 4px solid #22C55E; }
    .site-card.error   { border-left: 4px solid #EF4444; }
    .site-card.pending { border-left: 4px solid #F59E0B; }

    .report-box {
        background: #1A1D27;
        border: 1px solid #2D3147;
        border-radius: 12px;
        padding: 28px 32px;
        margin-top: 16px;
        font-size: 15px;
        line-height: 1.85;
    }

    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-green  { background: #14532D; color: #86EFAC; }
    .badge-red    { background: #450A0A; color: #FCA5A5; }
    .badge-yellow { background: #451A03; color: #FDE68A; }

    .api-status-ok  { background: #14532D; color: #86EFAC; padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 600; }
    .api-status-err { background: #450A0A; color: #FCA5A5; padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 600; }

    .stButton > button { border-radius: 8px; font-weight: 600; }
    div[data-testid="stExpander"] { border: 1px solid #2D3147 !important; border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
for key, default in [
    ("scraped_data", None),
    ("report_text", None),
    ("scraping_done", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.image("https://www.hostafrica.com/wp-content/uploads/2022/04/hostafrica-logo.png", width=180)

    st.markdown("### 🤖 AI Model")
    if API_KEY:
        st.markdown('<div class="api-status-ok">✅ Gemini 2.5 Flash Lite — Ready</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="api-status-err">❌ GEMINI_API_KEY not set in secrets</div>', unsafe_allow_html=True)
        st.caption("Add `GEMINI_API_KEY` under App Settings → Secrets to enable report generation.")

    st.markdown("---")
    st.markdown("### 🌐 Sites to Scan")
    selected_sites = {}
    for site_key, config in HOSTAFRICA_SITES.items():
        selected_sites[site_key] = st.checkbox(
            f"{config['flag']} {config['label']}",
            value=True,
            key=f"site_{site_key}",
        )

    st.markdown("---")
    st.markdown("### 📋 Past Reports")
    reports = list_reports()
    if reports:
        for r in reports[:8]:
            dt = datetime.fromisoformat(r["generated_at"])
            c1, c2 = st.columns([4, 1])
            with c1:
                if st.button(f"📄 {dt.strftime('%d %b %Y, %H:%M')}", key=f"load_{r['id']}", use_container_width=True):
                    st.session_state.report_text = load_report(r["id"])
            with c2:
                if st.button("🗑", key=f"del_{r['id']}"):
                    delete_report(r["id"])
                    st.rerun()
    else:
        st.caption("No reports yet. Run a scan to generate your first one!")

    st.markdown("---")
    st.caption("HostAfrica FYI Generator v1.0 · Gemini 2.5 Flash Lite")

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("# 🌍 HostAfrica Weekly FYI Generator")
st.markdown(
    "Automatically scans HostAfrica's regional websites and generates a polished "
    "team FYI report — powered by **Gemini 2.5 Flash Lite**."
)

tab_scan, tab_report, tab_sites = st.tabs(["🔍 Scan & Generate", "📄 Report", "🗺️ Site Explorer"])

# ─────────────────────────────────────────────
# TAB 1: SCAN & GENERATE
# ─────────────────────────────────────────────
with tab_scan:
    st.markdown("### Step 1 — Scan Websites")
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.markdown(
            "Click **Start Scan** to crawl the selected HostAfrica websites and collect fresh content. "
            "This usually takes 30–60 seconds."
        )
    with col_b:
        run_scan = st.button("🚀 Start Scan", type="primary", use_container_width=True)

    if run_scan:
        active_sites = {k: v for k, v in HOSTAFRICA_SITES.items() if selected_sites.get(k, False)}
        if not active_sites:
            st.warning("Please select at least one site to scan.")
        else:
            progress_bar = st.progress(0, text="Initialising scan...")
            sites_list = list(active_sites.keys())
            scraped = {}

            with st.spinner("Scanning websites..."):
                for i, site_key in enumerate(sites_list):
                    label = HOSTAFRICA_SITES[site_key]["label"]
                    progress_bar.progress(int((i / len(sites_list)) * 100), text=f"Scanning {label}...")
                    scraped[site_key] = scrape_site(site_key)

            progress_bar.progress(100, text="Scan complete!")
            st.session_state.scraped_data = scraped
            st.session_state.scraping_done = True

            st.markdown("#### Scan Results")
            cols = st.columns(min(len(scraped), 3))
            for idx, (site_key, pages) in enumerate(scraped.items()):
                cfg = HOSTAFRICA_SITES[site_key]
                ok_count = sum(1 for p in pages if p["status"] == "ok")
                total = len(pages)
                sc = "ok" if ok_count == total else ("error" if ok_count == 0 else "pending")
                bc = "badge-green" if ok_count == total else ("badge-red" if ok_count == 0 else "badge-yellow")
                with cols[idx % 3]:
                    st.markdown(
                        f'<div class="site-card {sc}">'
                        f'<strong>{cfg["flag"]} {cfg["label"]}</strong><br/>'
                        f'<span class="badge {bc}">{ok_count}/{total} pages OK</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            total_pages = sum(len(v) for v in scraped.values())
            st.success(f"✅ Scan complete! {total_pages} pages collected across {len(scraped)} sites.")

    st.markdown("---")
    st.markdown("### Step 2 — Generate FYI Report")

    if not st.session_state.scraping_done:
        st.info("👆 Run a scan first to collect fresh website content.")
    elif not API_KEY:
        st.error(
            "🔑 **GEMINI_API_KEY** not found in Streamlit secrets. "
            "Add it under **App Settings → Secrets** to enable report generation."
        )
    else:
        col_gen, col_opt = st.columns([2, 1])
        with col_opt:
            tone_note = st.text_area(
                "Optional: Add context",
                placeholder="e.g. Focus on new products. Highlight Kenya updates this week.",
                height=80,
            )
        with col_gen:
            st.markdown(
                "Gemini 2.5 Flash Lite will analyse the scraped content and write a warm, "
                "professional FYI report in the style your team loves. 🤖✍️"
            )
            generate_btn = st.button("✨ Generate FYI Report", type="primary", use_container_width=True)

        if generate_btn:
            st.markdown("#### 📝 Generating your report...")
            stream_box = st.empty()
            try:
                report = generate_report(
                    scraped_data=st.session_state.scraped_data,
                    api_key=API_KEY,
                    stream_placeholder=stream_box,
                )
                st.session_state.report_text = report
                report_id = save_report(report, st.session_state.scraped_data)
                st.success(f"🎉 Report generated and saved! (ID: {report_id})")
            except Exception as e:
                st.error(f"Error generating report: {e}")

# ─────────────────────────────────────────────
# TAB 2: REPORT VIEW
# ─────────────────────────────────────────────
with tab_report:
    if st.session_state.report_text:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button(
                "⬇️ Download as Markdown",
                data=st.session_state.report_text,
                file_name=f"hostafrica_fyi_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with c2:
            if st.button("📋 Copy hint (select all below)", use_container_width=True):
                st.info("Click inside the raw text area below and press Ctrl+A / Cmd+A to select all.")
        with c3:
            if st.button("🔄 Clear Report", use_container_width=True):
                st.session_state.report_text = None
                st.rerun()

        st.markdown("---")
        st.markdown('<div class="report-box">', unsafe_allow_html=True)
        st.markdown(st.session_state.report_text)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        with st.expander("📋 Raw text — for Slack / Teams / WhatsApp"):
            st.text_area("", value=st.session_state.report_text, height=400, label_visibility="collapsed")
    else:
        st.info("No report yet. Go to **Scan & Generate** to create one, or load a past report from the sidebar.")
        latest_text, latest_meta = get_latest_report()
        if latest_text:
            dt = datetime.fromisoformat(latest_meta["generated_at"])
            st.markdown(f"**Last report:** {dt.strftime('%A, %d %B %Y at %H:%M UTC')}")
            if st.button("📄 Load Latest Report"):
                st.session_state.report_text = latest_text
                st.rerun()

# ─────────────────────────────────────────────
# TAB 3: SITE EXPLORER
# ─────────────────────────────────────────────
with tab_sites:
    st.markdown("### 🗺️ Site Explorer")
    st.markdown("Explore the scraped content from each site or trigger a single-site scan.")

    selected_explorer_site = st.selectbox(
        "Select a site to explore",
        options=list(HOSTAFRICA_SITES.keys()),
        format_func=lambda k: f"{HOSTAFRICA_SITES[k]['flag']} {HOSTAFRICA_SITES[k]['label']}",
    )
    cfg = HOSTAFRICA_SITES[selected_explorer_site]
    st.markdown(f"**Base URL:** [{cfg['base_url']}]({cfg['base_url']})")
    st.markdown(f"**Tracked pages:** {len(cfg['key_pages'])}")

    ce1, ce2 = st.columns(2)
    with ce1:
        if st.button(f"🔍 Scan {cfg['label']} now", use_container_width=True):
            with st.spinner(f"Scanning {cfg['label']}..."):
                pages = scrape_site(selected_explorer_site)
                if st.session_state.scraped_data is None:
                    st.session_state.scraped_data = {}
                st.session_state.scraped_data[selected_explorer_site] = pages
            st.success("Scan done!")

    site_has_data = (
        st.session_state.scraped_data is not None
        and selected_explorer_site in st.session_state.scraped_data
    )
    with ce2:
        if site_has_data and API_KEY:
            if st.button("🤖 AI Summary of this site", use_container_width=True):
                with st.spinner("Asking Gemini for a summary..."):
                    try:
                        summary = generate_site_summary(
                            selected_explorer_site,
                            st.session_state.scraped_data[selected_explorer_site],
                            api_key=API_KEY,
                        )
                        st.markdown("#### 💡 AI Summary")
                        st.info(summary)
                    except Exception as e:
                        st.error(f"Error: {e}")
        elif site_has_data and not API_KEY:
            st.warning("Add GEMINI_API_KEY to secrets to enable AI summaries.")

    if site_has_data:
        pages = st.session_state.scraped_data[selected_explorer_site]
        st.markdown(f"#### 📄 Scraped Pages ({len(pages)})")
        for page in pages:
            icon = "✅" if page["status"] == "ok" else "❌"
            with st.expander(f"{icon} {page['url']}"):
                st.markdown(f"**Status:** `{page['status']}`")
                st.markdown(f"**Title:** {page.get('title', 'N/A')}")
                if page["status"] == "ok":
                    st.text_area(
                        "Content preview",
                        value=page["text"][:1500],
                        height=200,
                        label_visibility="collapsed",
                    )
    else:
        st.info("No data yet for this site. Click **Scan** above or run a full scan from the Scan tab.")

    st.markdown("---")
    st.markdown("### ➕ Add a New Site")
    with st.expander("Add a new HostAfrica domain to monitor"):
        st.markdown("Add new sites by editing `site_config.py` and adding an entry to `HOSTAFRICA_SITES`.")
        st.code('''
# Example: Adding hostafrica.com.tz (Tanzania)
"hostafrica.com.tz": {
    "label": "HostAfrica Tanzania (.TZ)",
    "base_url": "https://hostafrica.com.tz",
    "flag": "🇹🇿",
    "key_pages": ["/", "/blog/", "/vps-hosting/", "/web-hosting/"],
},
        ''', language="python")
