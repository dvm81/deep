"""Main entry point for the company research system."""

import json
from pathlib import Path
from urllib.parse import urlparse
from typing import List
from pydantic import HttpUrl

from company_research.schema import ResearchBrief, ResearchState
from company_research.agents.graph import build_graph
from company_research.storage import save_state


def load_config(path: str = "config.json"):
    """Load configuration from JSON file.

    Args:
        path: Path to the configuration file

    Returns:
        Dictionary with configuration data
    """
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(config_path: str = "config.json"):
    """Main execution function.

    This function:
    1. Loads configuration from JSON file
    2. Creates the research brief
    3. Builds and runs the LangGraph workflow
    4. Saves the final state

    Args:
        config_path: Path to the configuration file
    """
    cfg = load_config(config_path)

    company_name: str = cfg["company_name"]
    request: str = cfg["request"]
    seed_urls: List[HttpUrl] = cfg["seed_urls"]

    allowed_domains = sorted({urlparse(u).netloc for u in seed_urls})

    brief = ResearchBrief(
        company_name=company_name,
        main_question=request.strip(),
        sub_questions=[],  # filled by planning_node
        seed_urls=seed_urls,
        allowed_domains=allowed_domains,
        constraints=[
            "Only use content from the scoped URLs and their domains.",
            "Use citations for every factual statement.",
        ],
    )

    state = ResearchState(brief=brief)
    app = build_graph()

    print(f"Starting research for {company_name}...")
    print(f"Seed URLs: {len(seed_urls)}")
    print(f"Allowed domains: {', '.join(allowed_domains)}")
    print()

    final_state = app.invoke({"state": state})
    final_research_state: ResearchState = final_state["state"]

    save_state(final_research_state)
    print(
        f"\nDone! Report written to artifacts/{company_name.lower().replace(' ', '_')}_private_investing_report.md"
    )


if __name__ == "__main__":
    import sys
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    main(config_file)
