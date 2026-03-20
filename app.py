"""
app.py — HostAfrica Weekly FYI Generator
Main Streamlit application entry point.
"""

import streamlit as st
import json
from datetime import datetime

from site_config import HOSTAFRICA_SITES, scrape_all_sites, scrape_site
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
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Card style for site status */
    .site-card {
        background: #1A1D27;
        border: 1px solid #2D3147;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    .site-card.ok { border-left: 4px solid #22C55E; }
    .site-card.error { border-left: 4px solid #EF4444; }
    .site-card.pending { border-left: 4px solid #F59E0B; }

    /* Report output */
    .report-box {
        background: #1A1D27;
        border: 1px solid #2D3147;
        border-radius: 12px;
        padding: 28px 32px;
        margin-top: 16px;
        font-size: 15px;
        line-height: 1.75;
    }

    /* Pill badge */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-green { background: #14532D; color: #86EFAC; }
    .badge-red { background: #450A0A; color: #FCA5A5; }
    .badge-yellow { background: #451A03; color: #FDE68A; }

    /* Streamlit overrides */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #2D3147 !important;
        border-radius: 10px !important;
    }
    .stTextInput > div > div > input {
        background: #1A1D27;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────
if "scraped_data" not in st.session_state:
    st.session_state.scraped_data = None
if "report_text" not in st.session_state:
    st.session_state.report_text = None
if "scraping_done" not in st.session_state:
    st.session_state.scraping_done = False


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.image("https://www.hostafrica.com/wp-content/uploads/2022/04/hostafrica-logo.png", width=180)
    st.markdown("### ⚙️ Settings")

    # Try to load from Streamlit secrets first, fallback to manual input
    api_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""

    if api_key:
        st.success("🔑 Gemini API key loaded from secrets.", icon="✅")
    else:
        api_key = st.text_input(
            "Google Gemini API Key",
            type="password",
            help="No secret found. Enter your key manually, or add GEMINI_API_KEY to Streamlit secrets. Get one at https://aistudio.google.com/app/apikey",
            placeholder="AIza...",
        )

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
            label = dt.strftime("%d %b %Y, %H:%M")
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(f"📄 {label}", key=f"load_{r['id']}", use_container_width=True):
                    st.session_state.report_text = load_report(r["id"])
                    st.session_state.active_tab = "report"
            with col2:
                if st.button("🗑", key=f"del_{r['id']}"):
                    delete_report(r["id"])
                    st.rerun()
    else:
        st.caption("No reports yet. Run a scan to generate your first one!")

    st.markdown("---")
    st.caption("HostAfrica FYI Generator v1.0")


# ─────────────────────────────────────────────
# MAIN AREA
# ─────────────────────────────────────────────
st.markdown("# 🌍 HostAfrica Weekly FYI Generator")
st.markdown(
    "Automatically scans HostAfrica's regional websites and generates a polished team FYI report — powered by Google Gemini AI."
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
            status_area = st.empty()
            progress_bar = st.progress(0, text="Initialising scan...")
            site_status_area = st.container()

            site_results_display = {}

            def on_progress(site_key, i, total):
                pct = int((i / total) * 100)
                config = HOSTAFRICA_SITES[site_key]
                progress_bar.progress(pct, text=f"Scanning {config['label']}...")
                site_results_display[site_key] = "⏳ Scanning..."

            with st.spinner("Scanning websites..."):
                scraped = {}
                sites_list = list(active_sites.keys())
                for i, site_key in enumerate(sites_list):
                    on_progress(site_key, i, len(sites_list))
                    scraped[site_key] = scrape_site(site_key)

            progress_bar.progress(100, text="Scan complete!")
            st.session_state.scraped_data = scraped
            st.session_state.scraping_done = True

            # Show results summary
            st.markdown("#### Scan Results")
            cols = st.columns(min(len(scraped), 3))
            for idx, (site_key, pages) in enumerate(scraped.items()):
                config = HOSTAFRICA_SITES[site_key]
                ok_count = sum(1 for p in pages if p["status"] == "ok")
                total = len(pages)
                with cols[idx % 3]:
                    status_class = "ok" if ok_count == total else ("error" if ok_count == 0 else "pending")
                    badge_class = "badge-green" if ok_count == total else ("badge-red" if ok_count == 0 else "badge-yellow")
                    badge_text = f"{ok_count}/{total} pages OK"
                    st.markdown(f"""
                    <div class="site-card {status_class}">
                        <strong>{config['flag']} {config['label']}</strong><br/>
                        <span class="badge {badge_class}">{badge_text}</span>
                    </div>
                    """, unsafe_allow_html=True)

            st.success(f"✅ Scan complete! {sum(len(v) for v in scraped.values())} pages collected across {len(scraped)} sites.")

    st.markdown("---")
    st.markdown("### Step 2 — Generate FYI Report")

    if not st.session_state.scraping_done:
        st.info("👆 Run a scan first to collect fresh website content.")
    elif not api_key:
        st.warning("🔑 Enter your Google Gemini API key in the sidebar to generate the report.")
    else:
        col_gen, col_opt = st.columns([2, 1])
        with col_opt:
            tone_note = st.text_area(
                "Optional: Add context for Gemini",
                placeholder="e.g. Focus on new products. Highlight Kenya updates this week.",
                height=80,
            )
        with col_gen:
            st.markdown(
                "Gemini will analyse the scraped content and write a warm, professional FYI report "
                "in the style your team loves. 🤖✍️"
            )
            generate_btn = st.button("✨ Generate Report with Gemini", type="primary", use_container_width=True)

        if generate_btn:
            st.markdown("#### 📝 Generating your report...")
            stream_box = st.empty()

            try:
                report = generate_report(
                    scraped_data=st.session_state.scraped_data,
                    api_key=api_key,
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
        col_r1, col_r2, col_r3 = st.columns([1, 1, 1])
        with col_r1:
            st.download_button(
                "⬇️ Download as Markdown",
                data=st.session_state.report_text,
                file_name=f"hostafrica_fyi_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col_r2:
            if st.button("📋 Copy to Clipboard (select all below)", use_container_width=True):
                st.info("Use the text area below to select-all and copy.")
        with col_r3:
            if st.button("🔄 Clear Report", use_container_width=True):
                st.session_state.report_text = None
                st.rerun()

        st.markdown("---")
        # Rendered markdown version
        st.markdown('<div class="report-box">', unsafe_allow_html=True)
        st.markdown(st.session_state.report_text)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        # Raw text for copying
        with st.expander("📋 Raw text (for copying to Slack/Teams/WhatsApp)"):
            st.text_area("", value=st.session_state.report_text, height=400, label_visibility="collapsed")
    else:
        st.info("No report yet. Go to the **Scan & Generate** tab to create one, or load a past report from the sidebar.")

        # Load latest if exists
        latest_text, latest_meta = get_latest_report()
        if latest_text:
            dt = datetime.fromisoformat(latest_meta["generated_at"])
            st.markdown(f"**Last report was generated on:** {dt.strftime('%A, %d %B %Y at %H:%M UTC')}")
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

    config = HOSTAFRICA_SITES[selected_explorer_site]
    st.markdown(f"**Base URL:** [{config['base_url']}]({config['base_url']})")
    st.markdown(f"**Tracked pages:** {len(config['key_pages'])}")

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        if st.button(f"🔍 Scan {config['label']} now", use_container_width=True):
            with st.spinner(f"Scanning {config['label']}..."):
                pages = scrape_site(selected_explorer_site)
                if st.session_state.scraped_data is None:
                    st.session_state.scraped_data = {}
                st.session_state.scraped_data[selected_explorer_site] = pages
            st.success("Scan done!")

    with col_e2:
        if api_key and st.session_state.scraped_data and selected_explorer_site in st.session_state.scraped_data:
            if st.button("🤖 AI Summary of this site", use_container_width=True):
                with st.spinner("Asking Gemini for a summary..."):
                    summary = generate_site_summary(
                        selected_explorer_site,
                        st.session_state.scraped_data[selected_explorer_site],
                        api_key,
                    )
                st.markdown("#### 💡 AI Summary")
                st.info(summary)

    # Show pages
    if st.session_state.scraped_data and selected_explorer_site in st.session_state.scraped_data:
        pages = st.session_state.scraped_data[selected_explorer_site]
        st.markdown(f"#### 📄 Scraped Pages ({len(pages)})")
        for page in pages:
            icon = "✅" if page["status"] == "ok" else "❌"
            with st.expander(f"{icon} {page['url']}"):
                st.markdown(f"**Status:** `{page['status']}`")
                st.markdown(f"**Title:** {page.get('title', 'N/A')}")
                if page["status"] == "ok":
                    st.text_area("Content preview", value=page["text"][:1500], height=200, label_visibility="collapsed")
    else:
        st.info("No data yet for this site. Click **Scan** above or run a full scan from the Scan tab.")

    st.markdown("---")
    st.markdown("### ➕ Add a New Site")
    with st.expander("Add a new HostAfrica domain to monitor"):
        st.markdown("Add new sites by editing `site_config.py` and adding an entry to `HOSTAFRICA_SITES`.")
        st.code("""
# Example: Adding hostafrica.com.tz (Tanzania)
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
        """, language="python")
