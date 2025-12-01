"""MCP-powered intelligent search for refinement."""

import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SearchPattern:
    """Pattern for searching scraped content."""
    name: str
    regex: str
    context_lines: int = 5  # Lines before/after match


@dataclass
class SearchSnippet:
    """A snippet extracted from search results."""
    file_path: str
    match_text: str
    context_before: str
    context_after: str
    pattern_name: str


# Predefined search patterns for common gaps
# V2.9: Expanded from 5 to 16 patterns for maximum extraction quality
SEARCH_PATTERNS = {
    # ===== NEWS & DATES (5 patterns) =====
    "news_dates": SearchPattern(
        name="news_dates",
        regex=r"\d{4}-\d{2}-\d{2}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
        context_lines=5
    ),
    "quarter_dates": SearchPattern(
        name="quarter_dates",
        regex=r"Q[1-4]\s+\d{4}|(?:first|second|third|fourth)\s+quarter\s+(?:of\s+)?\d{4}",
        context_lines=4
    ),
    "month_year_dates": SearchPattern(
        name="month_year_dates",
        regex=r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
        context_lines=4
    ),

    # ===== COMPANIES & PORTFOLIO (3 patterns) =====
    "company_names": SearchPattern(
        name="company_names",
        regex=r"[A-Z][a-z]+(?:\s[A-Z][a-z]+)*(?:\sInc\.|\sLLC|\sLtd\.|\sCorp\.)?",
        context_lines=3
    ),
    "private_entities": SearchPattern(
        name="private_entities",
        regex=r"[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\s+(?:LP|GP|Holdings?|Partners?|Group|Management|Advisors?)",
        context_lines=3
    ),
    "sector_keywords": SearchPattern(
        name="sector_keywords",
        regex=r"\b(?:biotech(?:nology)?|fintech|healthtech|climate tech|clean tech|SaaS|enterprise software|consumer|B2B|B2C|healthcare|financial services|real estate|infrastructure)\b",
        context_lines=3
    ),

    # ===== PEOPLE & LEADERSHIP (4 patterns) =====
    "people_with_titles": SearchPattern(
        name="people_with_titles",
        regex=r"[A-Z][a-z]+\s[A-Z][a-z]+,?\s+(?:CEO|CTO|CFO|COO|Partner|Managing Director|Director|Vice President|VP|Head of|Chief)",
        context_lines=2
    ),
    "academic_titles": SearchPattern(
        name="academic_titles",
        regex=r"[A-Z][a-z]+\s[A-Z][a-z]+,?\s+(?:PhD|MD|MBA|JD|CFA|M\.D\.|Ph\.D\.)",
        context_lines=2
    ),
    "board_roles": SearchPattern(
        name="board_roles",
        regex=r"[A-Z][a-z]+\s[A-Z][a-z]+,?\s+(?:Board Member|Trustee|Advisory Board|Board of Directors|Independent Director|Non-Executive Director)",
        context_lines=2
    ),
    "senior_titles": SearchPattern(
        name="senior_titles",
        regex=r"\b(?:Senior|Principal|Executive|General)\s+(?:Partner|Director|Manager|Vice President|Advisor)\b",
        context_lines=2
    ),

    # ===== FINANCIAL METRICS (3 patterns) =====
    "dollar_amounts": SearchPattern(
        name="dollar_amounts",
        regex=r"\$\d+(?:\.\d+)?(?:M|B|bn|mn|million|billion|\s+million|\s+billion)",
        context_lines=3
    ),
    "percentages": SearchPattern(
        name="percentages",
        regex=r"\d+(?:\.\d+)?%(?:\s+(?:stake|ownership|equity|interest|return|growth|increase))?",
        context_lines=3
    ),
    "employee_counts": SearchPattern(
        name="employee_counts",
        regex=r"\d+\+?\s+(?:employees?|people|team members?|professionals?)",
        context_lines=2
    ),

    # ===== GEOGRAPHY (1 pattern) =====
    "geography": SearchPattern(
        name="geography",
        regex=r"\b(?:APAC|EMEA|North America|Europe|Asia|Latin America|Middle East|Africa|US|UK|China|India|San Francisco|New York|Boston|London|Singapore)\b",
        context_lines=2
    ),

    # ===== INVESTMENT TERMS (2 patterns) =====
    "investment_rounds": SearchPattern(
        name="investment_rounds",
        regex=r"\b(?:Seed|Series\s+[A-F]|Pre-seed|Growth\s+(?:round|equity)|Late\s+stage|Early\s+stage)\b",
        context_lines=3
    ),
    "fund_names": SearchPattern(
        name="fund_names",
        regex=r"(?:[A-Z][a-z]+\s)*(?:Fund|Venture|Capital|Growth|Stage|Portfolio|Strategy)",
        context_lines=3
    ),
}


def generate_search_patterns(gap_description: str, question: str) -> List[SearchPattern]:
    """Generate relevant search patterns based on reflection gap.

    V2.9: Enhanced with 16 patterns for comprehensive extraction

    Args:
        gap_description: Description of what's missing from reflection
        question: Original research question

    Returns:
        List of SearchPattern objects to use
    """
    patterns = []
    gap_lower = gap_description.lower()
    question_lower = question.lower()

    # ===== NEWS & DATES =====
    if any(word in gap_lower for word in ["news", "announcement", "press release", "date"]):
        patterns.append(SEARCH_PATTERNS["news_dates"])
        patterns.append(SEARCH_PATTERNS["quarter_dates"])
        patterns.append(SEARCH_PATTERNS["month_year_dates"])

    # ===== COMPANIES & PORTFOLIO =====
    if any(word in gap_lower or word in question_lower for word in ["company", "companies", "portfolio", "investment", "firm"]):
        patterns.append(SEARCH_PATTERNS["company_names"])
        patterns.append(SEARCH_PATTERNS["private_entities"])
        patterns.append(SEARCH_PATTERNS["sector_keywords"])

    # ===== PEOPLE & LEADERSHIP =====
    if any(word in gap_lower or word in question_lower for word in ["team", "leadership", "decision maker", "people", "member", "executive", "board"]):
        patterns.append(SEARCH_PATTERNS["people_with_titles"])
        patterns.append(SEARCH_PATTERNS["academic_titles"])
        patterns.append(SEARCH_PATTERNS["board_roles"])
        patterns.append(SEARCH_PATTERNS["senior_titles"])

    # ===== FINANCIAL METRICS =====
    if any(word in gap_lower for word in ["amount", "aum", "assets", "fund size", "capital", "investment", "valuation", "stake", "ownership"]):
        patterns.append(SEARCH_PATTERNS["dollar_amounts"])
        patterns.append(SEARCH_PATTERNS["percentages"])
        patterns.append(SEARCH_PATTERNS["fund_names"])

    # ===== GEOGRAPHY =====
    if any(word in gap_lower or word in question_lower for word in ["region", "geographic", "location", "country", "market"]):
        patterns.append(SEARCH_PATTERNS["geography"])

    # ===== INVESTMENT TERMS =====
    if any(word in gap_lower or word in question_lower for word in ["round", "series", "stage", "strategy", "fund"]):
        patterns.append(SEARCH_PATTERNS["investment_rounds"])
        patterns.append(SEARCH_PATTERNS["fund_names"])

    # ===== METRICS & SCALE =====
    if any(word in gap_lower for word in ["employee", "team size", "headcount", "scale"]):
        patterns.append(SEARCH_PATTERNS["employee_counts"])

    # Default: if no patterns matched, use comprehensive news search (most common gap)
    if not patterns:
        patterns.append(SEARCH_PATTERNS["news_dates"])
        patterns.append(SEARCH_PATTERNS["quarter_dates"])
        patterns.append(SEARCH_PATTERNS["company_names"])

    # Remove duplicates while preserving order
    seen = set()
    unique_patterns = []
    for p in patterns:
        if p.name not in seen:
            seen.add(p.name)
            unique_patterns.append(p)

    return unique_patterns


def search_file_with_pattern(
    file_path: Path,
    pattern: SearchPattern
) -> List[SearchSnippet]:
    """Search a single JSON file for pattern matches.

    Args:
        file_path: Path to the JSON file (contains PageContent)
        pattern: Search pattern to use

    Returns:
        List of SearchSnippet objects with matches and context
    """
    try:
        # Load the page content JSON
        data = json.loads(file_path.read_text(encoding="utf-8"))
        markdown_text = data.get("text", "")

        if not markdown_text:
            return []

        # Split into lines for context extraction
        lines = markdown_text.split('\n')
        snippets = []

        # Search each line
        for line_idx, line in enumerate(lines):
            matches = list(re.finditer(pattern.regex, line))

            for match in matches:
                # Extract context lines
                start_idx = max(0, line_idx - pattern.context_lines)
                end_idx = min(len(lines), line_idx + pattern.context_lines + 1)

                context_before = '\n'.join(lines[start_idx:line_idx])
                context_after = '\n'.join(lines[line_idx + 1:end_idx])

                snippet = SearchSnippet(
                    file_path=str(file_path),
                    match_text=match.group(),
                    context_before=context_before,
                    context_after=context_after,
                    pattern_name=pattern.name
                )
                snippets.append(snippet)

        return snippets

    except Exception as e:
        print(f"Error searching {file_path}: {e}")
        return []


def search_scraped_pages(
    patterns: List[SearchPattern],
    pages_dir: Path = Path("artifacts/pages")
) -> Dict[str, List[SearchSnippet]]:
    """Search all scraped pages for multiple patterns.

    Args:
        patterns: List of search patterns to apply
        pages_dir: Directory containing scraped page JSON files

    Returns:
        Dictionary mapping pattern names to lists of snippets
    """
    results = {pattern.name: [] for pattern in patterns}

    if not pages_dir.exists():
        return results

    # Search all JSON files
    for json_file in pages_dir.glob("*.json"):
        for pattern in patterns:
            snippets = search_file_with_pattern(json_file, pattern)
            results[pattern.name].extend(snippets)

    return results


def build_targeted_context(
    search_results: Dict[str, List[SearchSnippet]],
    max_snippets_per_pattern: int = 20
) -> Tuple[str, List[str]]:
    """Build targeted context string from search results.

    Args:
        search_results: Dictionary of pattern names to snippets
        max_snippets_per_pattern: Maximum snippets to include per pattern

    Returns:
        Tuple of (targeted_context_string, list_of_patterns_used)
    """
    if not search_results or all(len(snippets) == 0 for snippets in search_results.values()):
        return "", []

    context_parts = []
    patterns_used = []

    for pattern_name, snippets in search_results.items():
        if not snippets:
            continue

        patterns_used.append(pattern_name)

        # Limit snippets to avoid overwhelming context
        limited_snippets = snippets[:max_snippets_per_pattern]

        context_parts.append(f"=== PATTERN: {pattern_name.upper()} ({len(limited_snippets)} matches) ===\n")

        for idx, snippet in enumerate(limited_snippets, 1):
            context_parts.append(f"\n--- Match {idx}: \"{snippet.match_text}\" ---")

            if snippet.context_before.strip():
                context_parts.append(f"Context before:\n{snippet.context_before}")

            context_parts.append(f"\n>>> MATCH: {snippet.match_text} <<<\n")

            if snippet.context_after.strip():
                context_parts.append(f"Context after:\n{snippet.context_after}")

            context_parts.append("")  # Blank line separator

    targeted_context = "\n".join(context_parts)
    return targeted_context, patterns_used


def execute_mcp_search(
    gap_description: str,
    question: str,
    pages_dir: Path = Path("artifacts/pages")
) -> Tuple[str, List[str]]:
    """Execute full MCP search pipeline.

    This is the main entry point for refinement.

    Args:
        gap_description: What's missing from reflection
        question: Original research question
        pages_dir: Directory with scraped pages

    Returns:
        Tuple of (targeted_context, patterns_used)
    """
    # Generate relevant search patterns
    patterns = generate_search_patterns(gap_description, question)

    # Search scraped pages
    results = search_scraped_pages(patterns, pages_dir)

    # Build targeted context
    targeted_context, patterns_used = build_targeted_context(results)

    return targeted_context, patterns_used
