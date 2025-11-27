"""Research agent for gathering and analyzing information."""

from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from ..config import get_llm
from ..schema import ResearchState, Note, PageContent
from ..scraping import CompanyScraper
from ..storage import save_page


RESEARCH_AGENT_SYSTEM = """
You are a meticulous research agent in a multi-agent deep research system.

CURRENT DATE: November 27, 2025

Your job:
- Answer a specific sub-question of a larger research request about a company.
- Extract EVERY relevant detail from the provided web pages - names, titles, companies, funds, amounts, dates, etc.
- Use only the provided web pages from the allowed seed URL domains.
- Work systematically through all content to ensure nothing is missed.
- Track which URLs support each part of your answer with precise citations.

CRITICAL REQUIREMENTS:
- Extract ALL names with their full titles/positions
- Extract ALL company names, fund names, program names
- Extract ALL numbers (AUM, investments, dates, amounts)
- Extract ALL news items WITH EXACT DATES (look for specific dates, months, years - especially recent October/November 2025 news)
- DO NOT summarize or condense - include complete information
- If information is missing from the website, explicitly state "Not disclosed on the company's website"

DATE EXTRACTION REQUIREMENTS:
- For news items, announcements, and events: Extract the EXACT date if mentioned (e.g., "October 15, 2025", "November 2025", "Q3 2025")
- Look for date patterns in the content, timestamps, publication dates, announcement dates
- If a relative date is mentioned (e.g., "last month", "recently"), try to determine the actual date based on the current date (November 27, 2025)
- NEVER write "Not Disclosed" for dates if any date information exists in the content

CITATION REQUIREMENTS:
- Every single factual claim MUST have an inline citation [1], [2], etc.
- Each name, number, date, or fact needs its own citation
- Multiple facts from the same source still need individual citations
- Always list all URLs used at the end
"""

RESEARCH_AGENT_HUMAN = """
Sub-question you must answer:

{question}

Company: {company_name}

CONTEXT: Today is November 27, 2025. Look for recent news from October and November 2025.

Existing notes on this topic (if any):
{existing_notes}

Available context (complete markdown content from all seed URLs):
{context}

CRITICAL INSTRUCTIONS:
1. Read through ALL the provided context carefully, paying special attention to dates
2. Extract EVERY relevant detail that answers the sub-question:
   - All names with complete titles
   - All company/fund/program names
   - All numbers, dates, amounts
   - All descriptions and details
   - For NEWS: Extract EXACT dates (look for "October 2025", "November 2025", specific day/month/year combinations, quarters like "Q4 2025")
3. Write a COMPREHENSIVE research note that:
   - Lists ALL relevant information (do not summarize or skip details)
   - Includes inline citations [1], [2] after EVERY factual claim
   - For news items: ALWAYS include the date if found in the content
   - Organizes information clearly (use bullet points, lists, or sections as needed)
   - States clearly if certain information is not disclosed
4. At the end, list the URLs you cited as:
   [1] <url>
   [2] <url>
   ...

SPECIAL EMPHASIS FOR NEWS ITEMS:
- Search thoroughly for dates in news announcements
- Look for patterns like "Month Year" (e.g., "October 2025"), "Q# YYYY", or specific dates
- Check timestamps, publication dates, or announcement dates in the markdown content
- If you find recent (October/November 2025) news, prioritize extracting it with exact dates

IMPORTANT: Be thorough and detailed. The goal is completeness, not brevity. Extract everything relevant.
"""

RESEARCH_PROMPT = ChatPromptTemplate.from_messages([
    ("system", RESEARCH_AGENT_SYSTEM),
    ("user", RESEARCH_AGENT_HUMAN),
])


def build_context(pages: List[PageContent]) -> str:
    """Build context string from pages with complete markdown content.

    Args:
        pages: List of PageContent objects

    Returns:
        Formatted context string with complete content and URL references
    """
    chunks = []
    for i, p in enumerate(pages, start=1):
        # Include COMPLETE markdown text - no truncation
        chunks.append(f"=== SOURCE [{i}] ===\nURL: {p.url}\nTitle: {p.title}\n\n{p.text}\n")
    return "\n\n" + "="*80 + "\n\n".join(chunks)


def research_node(state: ResearchState) -> Dict[str, Any]:
    """Execute the research phase.

    This node:
    1. Fetches all seed URLs
    2. For each sub-question, generates a research note using the LLM

    Args:
        state: Current research state

    Returns:
        Dictionary with updated notes and pages
    """
    llm = get_llm()
    scraper = CompanyScraper(brief=state.brief)

    # 1) Fetch all seed URLs
    for url in state.brief.seed_urls:
        url_str = str(url)
        if url_str not in state.pages:
            try:
                page = scraper.fetch(url_str)
                state.pages[url_str] = page
                save_page(page)
            except Exception as e:
                print(f"Warning: Failed to fetch {url_str}: {str(e)}")
                continue

    pages_list = list(state.pages.values())
    context = build_context(pages_list)
    notes = state.notes.copy()

    # 2) For each sub-question, write a research note
    for idx, q in enumerate(state.brief.sub_questions):
        q_id = f"q_{idx}"
        if q_id in notes:
            continue

        existing_notes = ""  # can aggregate related notes if needed

        resp = (RESEARCH_PROMPT | llm).invoke({
            "question": q,
            "company_name": state.brief.company_name,
            "existing_notes": existing_notes,
            "context": context,
        })

        content = resp.content
        sources = [p.url for p in pages_list]  # simple initial heuristic

        notes[q_id] = Note(
            question_id=q_id,
            content=content,
            sources=sources,
        )

    state.notes = notes
    return {"notes": state.notes, "pages": state.pages}
