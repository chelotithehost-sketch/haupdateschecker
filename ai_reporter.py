"""
ai_reporter.py — Uses Google Gemini to analyse scraped content and produce the FYI report
"""

import json
from datetime import datetime
import google.generativeai as genai


SYSTEM_PROMPT = """You are the HostAfrica Internal Communications AI.
Your job is to analyse fresh website content scraped from HostAfrica's regional websites 
and produce a polished weekly Friday FYI report for the support/sales team.

Tone: Professional, warm, friendly, and lightly fun — without cliché jokes.
Format: Use Markdown. Emoji section headers. Bullet points for lists.

Structure your report EXACTLY like this:

---
👋 Hey team!

[1–2 sentence warm intro for the weekly FYI.]

---
📌 THIS WEEK'S HIGHLIGHTS

[For each site that has something noteworthy, create a sub-section like:]
### 🇿🇦 HostAfrica South Africa (.CO.ZA)
- **[Feature/Update name]**: Brief, clear description. Include the URL as a markdown link.

[Repeat for each site with updates.]

---
🔖 GOOD THINGS TO BOOKMARK
[List any pages that are great reference resources for the team, with URL links.]

---
💡 TEAM TIPS
[1–3 practical tips for the team based on what you found — e.g., how to handle customer queries about new features.]

---
That's your FYI for this week! Have a great weekend, team 🎉

---

Rules:
- Only include real content found in the scraped data. Do NOT invent features or URLs.
- If a site had no new/interesting content, skip it or note it briefly.
- Keep each bullet concise — 1–2 sentences max.
- Always include the actual URL as a clickable markdown link for each item.
- If scraping failed for a site, mention it briefly and move on.
"""


def build_user_prompt(scraped_data: dict, previous_snapshot: dict | None = None) -> str:
    """Build the prompt from scraped site data."""
    lines = [
        f"Today's date: {datetime.utcnow().strftime('%A, %d %B %Y')}",
        "",
        "Below is the freshly scraped content from HostAfrica's websites.",
        "Please analyse it and produce the weekly Friday FYI report.",
        "",
    ]

    for site_key, pages in scraped_data.items():
        lines.append(f"## Site: {site_key}")
        for page in pages:
            if page["status"] != "ok":
                lines.append(f"  - URL: {page['url']} | Status: {page['status']} (could not fetch)")
                continue
            lines.append(f"  ### Page: {page['url']}")
            lines.append(f"  Title: {page['title']}")
            lines.append(f"  Content snippet:")
            lines.append(page["text"][:3000])  # limit per page for token budget
            lines.append("")

    if previous_snapshot:
        lines.append("---")
        lines.append("PREVIOUS REPORT SNAPSHOT (for comparison — highlight what changed):")
        lines.append(json.dumps(previous_snapshot, indent=2)[:2000])

    return "\n".join(lines)


def generate_report(
    scraped_data: dict,
    api_key: str,
    previous_snapshot: dict | None = None,
    stream_placeholder=None,
) -> str:
    """
    Call Gemini to generate the FYI report.
    If stream_placeholder is provided (a st.empty()), streams output live.
    Returns the full report text.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        system_instruction=SYSTEM_PROMPT,
    )

    user_prompt = build_user_prompt(scraped_data, previous_snapshot)
    full_text = ""

    response = model.generate_content(user_prompt, stream=True)
    for chunk in response:
        if chunk.text:
            full_text += chunk.text
            if stream_placeholder:
                stream_placeholder.markdown(full_text + "▌")

    if stream_placeholder:
        stream_placeholder.markdown(full_text)

    return full_text


def generate_site_summary(site_key: str, pages: list[dict], api_key: str) -> str:
    """Generate a quick summary for a single site (used in site detail view)."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="gemini-1.5-pro")

    content_lines = ["Summarise what's notable on this HostAfrica site for the support team.\n"]
    for page in pages:
        if page["status"] == "ok":
            content_lines.append(f"Page: {page['url']}\n{page['text'][:1500]}\n")

    response = model.generate_content("\n".join(content_lines))
    return response.text
