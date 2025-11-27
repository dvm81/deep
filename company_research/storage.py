"""Storage helpers for persisting research data."""

import json
from pathlib import Path
from typing import Dict
from .schema import PageContent, Note, ResearchState

BASE_DIR = Path("artifacts")


def save_page(page: PageContent) -> None:
    """Save a scraped page to JSON file.

    Args:
        page: The PageContent to save
    """
    url_slug = str(page.url).replace("https://", "").replace("http://", "").replace("/", "_").replace("#", "_")
    out = BASE_DIR / "pages" / f"{url_slug}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page.model_dump_json(indent=2), encoding="utf-8")


def save_notes(notes: Dict[str, Note]) -> None:
    """Save all research notes to JSON file.

    Args:
        notes: Dictionary of notes to save
    """
    out = BASE_DIR / "notes.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {k: v.model_dump() for k, v in notes.items()}
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_report(report_md: str, company_name: str) -> Path:
    """Save the final markdown report.

    Args:
        report_md: The markdown content to save
        company_name: Name of the company for the filename

    Returns:
        Path to the saved report file
    """
    safe_name = company_name.lower().replace(" ", "_")
    out = BASE_DIR / f"{safe_name}_private_investing_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report_md, encoding="utf-8")
    return out


def save_state(state: ResearchState) -> None:
    """Save the entire research state to JSON.

    Args:
        state: The ResearchState to save
    """
    out = BASE_DIR / "state.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(state.model_dump_json(indent=2), encoding="utf-8")
