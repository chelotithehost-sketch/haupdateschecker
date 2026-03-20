"""
report_store.py — Simple JSON-based report history (works on Streamlit Cloud with session_state)
For production, swap the file backend with a database or Streamlit's built-in KV store.
"""

import json
import os
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)
INDEX_FILE = REPORTS_DIR / "index.json"


def _load_index() -> list[dict]:
    if INDEX_FILE.exists():
        try:
            return json.loads(INDEX_FILE.read_text())
        except Exception:
            return []
    return []


def _save_index(index: list[dict]):
    INDEX_FILE.write_text(json.dumps(index, indent=2))


def save_report(report_text: str, scraped_summary: dict) -> str:
    """Save a report and return its ID."""
    report_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"{report_id}.md"
    report_path.write_text(report_text)

    meta_path = REPORTS_DIR / f"{report_id}_meta.json"
    meta = {
        "id": report_id,
        "generated_at": datetime.utcnow().isoformat(),
        "sites_scraped": list(scraped_summary.keys()),
        "page_count": sum(len(v) for v in scraped_summary.values()),
    }
    meta_path.write_text(json.dumps(meta, indent=2))

    index = _load_index()
    index.insert(0, meta)
    # Keep last 20 reports in index
    _save_index(index[:20])

    return report_id


def load_report(report_id: str) -> str | None:
    path = REPORTS_DIR / f"{report_id}.md"
    if path.exists():
        return path.read_text()
    return None


def list_reports() -> list[dict]:
    """Return list of report metadata, newest first."""
    return _load_index()


def get_latest_report() -> tuple[str | None, dict | None]:
    """Return (report_text, meta) for the most recent report."""
    index = _load_index()
    if not index:
        return None, None
    latest = index[0]
    text = load_report(latest["id"])
    return text, latest


def delete_report(report_id: str):
    for suffix in [".md", "_meta.json"]:
        p = REPORTS_DIR / f"{report_id}{suffix}"
        if p.exists():
            p.unlink()
    index = [r for r in _load_index() if r["id"] != report_id]
    _save_index(index)
