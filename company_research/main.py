"""Main entry point for the company research system."""

import json
import argparse
from pathlib import Path
from urllib.parse import urlparse
from typing import List
from pydantic import HttpUrl

from company_research.schema import ResearchBrief, ResearchState
from company_research.agents.graph import build_graph
from company_research.storage import save_state
from company_research import logger
from company_research.logger import Colors, log_header, log_step, log_metric, log_tree, Timer


def load_config(path: str = "config.json"):
    """Load configuration from JSON file.

    Args:
        path: Path to the configuration file

    Returns:
        Dictionary with configuration data
    """
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(config_path: str = "config.json", verbose: bool = False):
    """Main execution function.

    This function:
    1. Loads configuration from JSON file
    2. Creates the research brief
    3. Builds and runs the LangGraph workflow
    4. Saves the final state

    Args:
        config_path: Path to the configuration file
        verbose: Enable verbose logging
    """
    # Set verbose mode globally
    logger.set_verbose(verbose)

    # Display banner
    log_header(f"{Colors.ROCKET} COMPANY PRIVATE INVESTING RESEARCH AGENT V2.9", level=1)

    # Load configuration
    log_step(f"{Colors.CONFIG} Configuration Loading", emoji="")
    cfg = load_config(config_path)

    company_name: str = cfg["company_name"]
    request: str = cfg["request"]
    seed_urls: List[HttpUrl] = cfg["seed_urls"]

    allowed_domains = sorted({urlparse(u).netloc for u in seed_urls})

    log_tree([
        f"Company: {company_name}",
        f"Research Focus: {request[:80]}..." if len(request) > 80 else f"Research Focus: {request}",
        f"Seed URLs: {len(seed_urls)} URLs",
        f"Allowed Domains: {', '.join(allowed_domains)}",
    ])

    # Create research brief
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

    # Show research strategy
    if verbose:
        print(f"\n{Colors.THINKING} {Colors.BOLD}Research Strategy:{Colors.RESET}")
        log_tree([
            "Phase 1: SCOPE (Planning)",
            "Phase 2: RESEARCH (Supervisor + 6 Sub-Agents with Reflection)",
            "Phase 2.5: REFINEMENT (MCP Intelligent Search + Targeted Follow-Up)",
            "Phase 3: WRITE (Markdown + JSON Reports)"
        ])

    state = ResearchState(brief=brief)
    app = build_graph()

    # Execute workflow with timing
    print()  # spacing
    with Timer("Total Execution Time", verbose_only=False) as total_timer:
        final_state = app.invoke({"state": state})

    final_research_state: ResearchState = final_state["state"]

    # Save state
    save_state(final_research_state)

    # Display completion summary
    log_header(f"{Colors.CELEBRATE} RESEARCH COMPLETE", level=1)

    print(f"{Colors.CHART} {Colors.BOLD}Final Statistics:{Colors.RESET}")
    log_metric("Total Execution Time", f"{total_timer.elapsed():.1f}", "s", indent=0)
    log_metric("Pages Scraped", len(final_research_state.pages), "pages", indent=0)
    log_metric("Sub-Agents Executed", len(final_research_state.sub_agent_results), "agents", indent=0)
    log_metric("Research Notes", len(final_research_state.notes), "notes", indent=0)

    if final_research_state.report_markdown:
        lines = final_research_state.report_markdown.count('\n') + 1
        size = len(final_research_state.report_markdown)
        log_metric("Markdown Report", f"{logger.format_size(size)}, {lines} lines", "", indent=0)

    if final_research_state.report_json:
        size = len(str(final_research_state.report_json))
        log_metric("JSON Report", logger.format_size(size), "structured", indent=0)

    # Show output files
    print(f"\n{Colors.FILE} {Colors.BOLD}Output Files:{Colors.RESET}")
    safe_name = company_name.lower().replace(' ', '_')
    log_tree([
        f"artifacts/{safe_name}_private_investing_report.md",
        f"artifacts/{safe_name}_private_investing_report.json",
        f"artifacts/state.json",
        f"artifacts/notes.json",
        f"artifacts/pages/ ({len(final_research_state.pages)} files)"
    ])

    print(f"\n{Colors.CELEBRATE} {Colors.GREEN}All done! Check artifacts/ for your reports.{Colors.RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Company Private Investing Research Agent V2.8",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m company_research.main config.json
  python -m company_research.main config.json --verbose
  python -m company_research.main config.json -v
        """
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config.json",
        help="Path to configuration JSON file (default: config.json)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output with detailed logging"
    )

    args = parser.parse_args()
    main(args.config, verbose=args.verbose)
