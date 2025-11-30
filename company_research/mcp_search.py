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
SEARCH_PATTERNS = {
    "news_dates": SearchPattern(
        name="news_dates",
        regex=r"\d{4}-\d{2}-\d{2}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
        context_lines=5
    ),
    "company_names": SearchPattern(
        name="company_names",
        regex=r"[A-Z][a-z]+(?:\s[A-Z][a-z]+)*(?:\sInc\.|\sLLC|\sLtd\.|\sCorp\.)?",
        context_lines=3
    ),
    "dollar_amounts": SearchPattern(
        name="dollar_amounts",
        regex=r"\$\d+(?:\.\d+)?(?:M|B|million|billion|\s+million|\s+billion)",
        context_lines=3
    ),
    "people_with_titles": SearchPattern(
        name="people_with_titles",
        regex=r"[A-Z][a-z]+\s[A-Z][a-z]+,?\s+(?:CEO|CTO|CFO|Partner|Managing Director|Director|Vice President|VP|Head of)",
        context_lines=2
    ),
    "fund_names": SearchPattern(
        name="fund_names",
        regex=r"(?:[A-Z][a-z]+\s)*(?:Fund|Venture|Capital|Growth|Stage|Portfolio)",
        context_lines=3
    ),
}


def generate_search_patterns(gap_description: str, question: str) -> List[SearchPattern]:
    """Generate relevant search patterns based on reflection gap.

    Args:
        gap_description: Description of what's missing from reflection
        question: Original research question

    Returns:
        List of SearchPattern objects to use
    """
    patterns = []
    gap_lower = gap_description.lower()
    question_lower = question.lower()

    # News/announcements gaps
    if any(word in gap_lower for word in ["news", "announcement", "press release", "date"]):
        patterns.append(SEARCH_PATTERNS["news_dates"])

    # Company/portfolio gaps
    if any(word in gap_lower or word in question_lower for word in ["company", "companies", "portfolio", "investment"]):
        patterns.append(SEARCH_PATTERNS["company_names"])

    # Financial gaps
    if any(word in gap_lower for word in ["amount", "aum", "assets", "fund size", "investment"]):
        patterns.append(SEARCH_PATTERNS["dollar_amounts"])
        patterns.append(SEARCH_PATTERNS["fund_names"])

    # People/team gaps
    if any(word in gap_lower or word in question_lower for word in ["team", "leadership", "decision maker", "people", "member"]):
        patterns.append(SEARCH_PATTERNS["people_with_titles"])

    # Default: if no patterns matched, use news dates (most common gap)
    if not patterns:
        patterns.append(SEARCH_PATTERNS["news_dates"])

    return patterns


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
