"""
site_config.py — HostAfrica website registry and scraping utilities
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

# ─────────────────────────────────────────────
# SITE REGISTRY  (add new TLDs here as needed)
# ─────────────────────────────────────────────
HOSTAFRICA_SITES = {
    "hostafrica.com": {
        "label": "HostAfrica Global (.COM)",
        "base_url": "https://www.hostafrica.com",
        "flag": "🌍",
        "key_pages": [
            "/",
            "/blog/",
            "/application-hosting/",
            "/reseller-program/african-domains-resellers/",
            "/vps-hosting/",
            "/web-hosting/",
            "/domain-registration/",
        ],
    },
    "hostafrica.co.za": {
        "label": "HostAfrica South Africa (.CO.ZA)",
        "base_url": "https://hostafrica.co.za",
        "flag": "🇿🇦",
        "key_pages": [
            "/",
            "/blog/",
            "/research/smelab/",
            "/accreditations-and-partnerships/",
            "/website-builder/easy-ai-builder/",
            "/vps-hosting/",
            "/web-hosting/",
        ],
    },
    "hostafrica.ke": {
        "label": "HostAfrica Kenya (.KE)",
        "base_url": "https://hostafrica.ke",
        "flag": "🇰🇪",
        "key_pages": [
            "/",
            "/blog/",
            "/vps-hosting/",
            "/web-hosting/",
            "/domain-registration/",
        ],
    },
    "hostafrica.ng": {
        "label": "HostAfrica Nigeria (.NG)",
        "base_url": "https://hostafrica.ng",
        "flag": "🇳🇬",
        "key_pages": [
            "/",
            "/blog/",
            "/vps-hosting/",
            "/web-hosting/",
            "/domain-registration/",
        ],
    },
    "hostafrica.com.gh": {
        "label": "HostAfrica Ghana (.GH)",
        "base_url": "https://hostafrica.com.gh",
        "flag": "🇬🇭",
        "key_pages": [
            "/",
            "/blog/",
            "/vps-hosting/",
            "/web-hosting/",
            "/domain-registration/",
        ],
    },
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_page(url: str, timeout: int = 15) -> dict:
    """Fetch a page and return status + cleaned text content."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Remove nav/footer/script/style noise
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
            tag.decompose()

        # Extract meaningful text
        text = soup.get_text(separator="\n", strip=True)
        # Collapse excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)

        # Grab page title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url

        # Extract all internal links for discovery
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/") or url.split("/")[2] in href:
                links.append(href)

        return {
            "url": url,
            "title": title,
            "text": text[:8000],  # cap per page
            "links": list(set(links))[:50],
            "status": "ok",
            "fetched_at": datetime.utcnow().isoformat(),
        }

    except requests.exceptions.Timeout:
        return {"url": url, "status": "timeout", "text": "", "title": url, "links": []}
    except requests.exceptions.ConnectionError:
        return {"url": url, "status": "connection_error", "text": "", "title": url, "links": []}
    except Exception as e:
        return {"url": url, "status": f"error: {str(e)}", "text": "", "title": url, "links": []}


def scrape_site(site_key: str, max_pages: int = 5) -> list[dict]:
    """Scrape key pages for a given site and return list of page data."""
    config = HOSTAFRICA_SITES[site_key]
    base = config["base_url"]
    pages_to_fetch = [base + p for p in config["key_pages"]][:max_pages]

    results = []
    for url in pages_to_fetch:
        data = fetch_page(url)
        data["site_key"] = site_key
        data["site_label"] = config["label"]
        results.append(data)

    return results


def scrape_all_sites(progress_callback=None) -> dict[str, list[dict]]:
    """Scrape all registered HostAfrica sites. Calls progress_callback(site_key, i, total)."""
    all_data = {}
    sites = list(HOSTAFRICA_SITES.keys())
    for i, site_key in enumerate(sites):
        if progress_callback:
            progress_callback(site_key, i, len(sites))
        all_data[site_key] = scrape_site(site_key)
    return all_data
