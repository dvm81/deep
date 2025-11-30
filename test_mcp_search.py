"""Test MCP search functionality on scraped pages."""

from pathlib import Path
from company_research.mcp_search import execute_mcp_search, SEARCH_PATTERNS

print("="*80)
print("TESTING MCP SEARCH ON SCRAPED PAGES")
print("="*80)

# Check if artifacts/pages exists
pages_dir = Path("artifacts/pages")
if not pages_dir.exists():
    print("\n❌ No artifacts/pages directory found")
    print("Run the research agent first to generate scraped pages")
    exit(1)

# Count pages
page_files = list(pages_dir.glob("*.json"))
print(f"\n✓ Found {len(page_files)} scraped pages")

# Test 1: News dates search
print("\n" + "-"*80)
print("TEST 1: Search for news dates")
print("-"*80)

targeted_snippets, patterns_used = execute_mcp_search(
    gap_description="missing news items and announcements with dates",
    question="What are the recent news items and announcements?"
)

if targeted_snippets:
    print(f"✓ Found snippets using patterns: {patterns_used}")
    print(f"✓ Total snippet size: {len(targeted_snippets)} chars")
    print(f"\nFirst 500 chars of snippets:")
    print(targeted_snippets[:500])
else:
    print("❌ No snippets found")

# Test 2: Company names search
print("\n" + "-"*80)
print("TEST 2: Search for company names")
print("-"*80)

targeted_snippets, patterns_used = execute_mcp_search(
    gap_description="missing portfolio companies",
    question="What are the portfolio companies?"
)

if targeted_snippets:
    print(f"✓ Found snippets using patterns: {patterns_used}")
    print(f"✓ Total snippet size: {len(targeted_snippets)} chars")
else:
    print("❌ No snippets found")

# Test 3: Dollar amounts search
print("\n" + "-"*80)
print("TEST 3: Search for dollar amounts")
print("-"*80)

targeted_snippets, patterns_used = execute_mcp_search(
    gap_description="missing investment amounts and AUM",
    question="What are the assets under management?"
)

if targeted_snippets:
    print(f"✓ Found snippets using patterns: {patterns_used}")
    print(f"✓ Total snippet size: {len(targeted_snippets)} chars")
else:
    print("❌ No snippets found")

# Test 4: People with titles search
print("\n" + "-"*80)
print("TEST 4: Search for people with titles")
print("-"*80)

targeted_snippets, patterns_used = execute_mcp_search(
    gap_description="missing team members and leadership",
    question="Who are the key decision makers?"
)

if targeted_snippets:
    print(f"✓ Found snippets using patterns: {patterns_used}")
    print(f"✓ Total snippet size: {len(targeted_snippets)} chars")
else:
    print("❌ No snippets found")

print("\n" + "="*80)
print("MCP SEARCH TESTS COMPLETE")
print("="*80)
