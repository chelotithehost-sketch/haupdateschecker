"""
ai_reporter.py — Uses Google Gemini 2.5 Flash Lite to generate the HostAfrica weekly FYI report.
"""

import json
from datetime import datetime
import google.generativeai as genai

GEMINI_MODEL = "gemini-2.5-flash-lite-preview-06-17"

SYSTEM_PROMPT = """You are the HostAfrica Internal Communications AI.
Your job is to analyse fresh website content scraped from HostAfrica's regional websites
and produce the weekly Friday FYI report for the support and sales team.

Tone: Professional, warm, friendly, and lightly fun — no cliché jokes.
Write in flowing prose paragraphs. No markdown headers with ###. No bullet points. No numbered lists.

Output the report in EXACTLY this structure — match the tone, flow, and style as closely as possible:

---

👋 Hey team! Welcome to your weekly Friday FYI — your go-to roundup of everything new and noteworthy across our websites. Think of it as your end-of-week cheat sheet, no studying required. 🗒️

To keep this segment useful and accurate, here's how you can help: if you spot something new or interesting on any of our sites during the week, give one of the leads a heads-up. They'll drop it in the leads channel so we can pull together a solid report for Fridays. Teamwork makes the FYI work. 🙌

---

THIS WEEK'S UPDATES

[For each noteworthy item found in the scraped data, write a short titled entry like this:]

**[Short descriptive title of the update]** [1–3 warm, clear sentences describing it. End with the direct URL on its own line.]

[URL]

[Blank line between each entry. Repeat for every update found. Keep the same conversational prose style throughout — no bullets, no sub-headers, no lists.]

---

That's a wrap for this week's FYI! As always, if you have questions or spot something we missed, the leads are just a message away. Have a great weekend, team! 🎉

---

STRICT RULES — follow these exactly:
1. ONLY include content that is genuinely present in the scraped data. Never invent features, products, or URLs.
2. Write every update as a flowing paragraph — never use bullet points, dashes as list items, or numbered lists.
3. Bold the title of each update using **title**.
4. Place each URL on its own line directly after its description, with a blank line separating entries.
5. If a site had no interesting or new content, skip it entirely — do not mention it.
6. If scraping failed for a site, skip it silently.
7. Do not add any extra sections, headers, or categories beyond what is shown in the template.
8. Keep language warm, human, and team-friendly throughout — this is an internal comms piece, not a press release.
"""


def build_user_prompt(scraped_data: dict, previous_snapshot: dict | None = None) -> str:
    """Build the user prompt from scraped site data."""
    lines = [
        f"Today's date: {datetime.utcnow().strftime('%A, %d %B %Y')}",
        "",
        "Below is the freshly scraped content from HostAfrica's websites.",
        "Please analyse it and produce the weekly Friday FYI report following the template exactly.",
        "",
    ]

    for site_key, pages in scraped_data.items():
        lines.append(f"## Site: {site_key}")
        for page in pages:
            if page["status"] != "ok":
                lines.append(f"  - {page['url']} — could not fetch ({page['status']})")
                continue
            lines.append(f"  Page: {page['url']}")
            lines.append(f"  Title: {page['title']}")
            lines.append(f"  Content:")
            lines.append(page["text"][:3000])
            lines.append("")

    if previous_snapshot:
        lines.append("---")
        lines.append("PREVIOUS REPORT (for reference — highlight anything that has changed or is new):")
        lines.append(json.dumps(previous_snapshot, indent=2)[:2000])

    return "\n".join(lines)


def generate_report(
    scraped_data: dict,
    api_key: str,
    previous_snapshot: dict | None = None,
    stream_placeholder=None,
) -> str:
    """
    Call Gemini 2.5 Flash Lite to generate the FYI report.
    Streams output live if stream_placeholder (st.empty()) is provided.
    Returns the full report text.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
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
    """Generate a quick AI summary for a single site (used in the Site Explorer tab)."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=GEMINI_MODEL)

    content_lines = [
        "Summarise in 3–5 sentences what is notable on this HostAfrica website page for the internal support team. "
        "Be warm and practical.\n"
    ]
    for page in pages:
        if page["status"] == "ok":
            content_lines.append(f"Page: {page['url']}\n{page['text'][:1500]}\n")

    response = model.generate_content("\n".join(content_lines))
    return response.text
