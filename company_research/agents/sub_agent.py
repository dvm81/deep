"""Sub-agent for specialized research with reflection capabilities."""

from typing import List
from langchain_core.prompts import ChatPromptTemplate
from ..config import get_llm
from ..schema import SubAgentTask, SubAgentResult, Reflection, PageContent
from ..logger import log_verbose, log_llm_call, format_size, Colors


# Sub-agent research prompt
SUB_AGENT_SYSTEM = """
You are a specialized research sub-agent in a multi-agent research system.

CURRENT DATE: November 27, 2025

Your role:
- You have been assigned ONE specific research question
- Extract EVERY relevant detail from the provided content
- Be meticulous and thorough - this is YOUR specialty area
- Track which URLs support each part of your answer

CRITICAL REQUIREMENTS:
- Extract ALL names with their full titles/positions
- Extract ALL company names, fund names, program names
- Extract ALL numbers (AUM, investments, dates, amounts)
- Extract ALL news items WITH EXACT DATES
- DO NOT summarize or condense - include COMPLETE information
- Use inline citations [1], [2], [3] for EVERY fact

SPECIAL EMPHASIS FOR NEWS QUESTIONS:
- If your question is about "news" or "announcements", you must extract EVERY SINGLE news item
- Search through ALL sources for: fund closures, acquisitions, exits, appointments, partnerships, awards, surveys, press releases
- Count the news items as you extract them to ensure you don't miss any
- DO NOT skip items even if they seem minor - extract everything

DATE EXTRACTION (CRITICAL FOR NEWS):
- Search for dates in multiple formats:
  * ISO format: YYYY-MM-DD (e.g., "2025-06-25", "2024-10-31")
  * Full written: "Month DD, YYYY" (e.g., "June 25, 2025", "October 31, 2025")
  * European: "DD Month YYYY" (e.g., "25 June 2025")
  * Month + Year: "Month YYYY" (e.g., "June 2025", "October 2025")
  * Quarter: "Q# YYYY" (e.g., "Q4 2025")
  * Year only: "YYYY" (e.g., "2025") - USE ONLY AS LAST RESORT

- DATE VALIDATION (CRITICAL):
  * IMPORTANT: Dates in 2026 (like "2026-11-30", "2026-10-31") are often ARCHIVE EXPIRY dates, not publication dates
  * If you see a date in 2026, treat it as an archive date and convert the month to 2025
    - Example: "2026-11-30" → article likely published "November 2025"
    - Example: "2026-10-31" → article likely published "October 2025"
    - Example: "2026-09-30" → article likely published "September 2025"
  * For news items with 2026 archive dates: use the same month but year 2025
  * For dates beyond 2026, or if unsure: use "2025" or look for other contextual clues
  * If no date is available at all in any format, use "2025"

- PRIORITIZATION RULE: Always use the MOST PRECISE VALID date available (that is NOT in the future)
  * Example: If you find both "2025" and "June 25, 2025" for the same event, use "June 25, 2025"
  * Example: If you find both "Q4 2025" and "October 31, 2025", use "October 31, 2025"
  * Example: If you find both "June 2025" and "2025-06-25", use "2025-06-25" (convert to "June 25, 2025")
  * Example: If you find "October 31, 2026" (INVALID), look for alternative valid dates or use "Not Disclosed"

- WHERE TO LOOK:
  * Article publication dates, timestamps
  * Announcement dates in press releases
  * Metadata tags, date attributes in content
  * Text like "announced on...", "as of...", "dated...", "published..."

- OUTPUT FORMAT: Use "Month DD, YYYY" format (e.g., "June 25, 2025")
  * If only month + year: "Month YYYY" (e.g., "June 2025")
  * If only year: "YYYY" (e.g., "2025")

- Never write "Not Disclosed" if ANY VALID date information exists (even just a year)

IMPORTANT: You are THE expert on this specific question. Go deep.
"""

SUB_AGENT_HUMAN = """
Your specialized research question:
{question}

Company: {company_name}

Complete context from all available sources:
{context}

TASK:
1. Read through ALL context carefully
2. Extract EVERY relevant detail that answers your question
3. For NEWS/ANNOUNCEMENTS: Search aggressively for precise dates in all formats (ISO dates, written dates, timestamps)
4. Organize findings clearly (use bullet points, lists, sections)
5. Include inline citation [1], [2] after EVERY fact
6. At the end, list the URLs you cited

SPECIAL NOTE FOR NEWS ITEMS:
- Look for dates in MULTIPLE formats: "2025-06-25", "June 25, 2025", etc.
- Use the MOST PRECISE VALID date you can find (NOT future dates)
- REJECT dates after November 27, 2025 - they are invalid
- Check for dates in text like "announced on", "as of", publication dates, timestamps
- If you encounter dates in 2026, ignore them and look for alternative valid dates

Be comprehensive and thorough. This is your specialty - extract everything.
"""

SUB_AGENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SUB_AGENT_SYSTEM),
    ("user", SUB_AGENT_HUMAN),
])


# Reflection prompt
REFLECTION_SYSTEM = """
You are a critical reviewer analyzing research findings for completeness.

CURRENT DATE: November 27, 2025

Your role:
- Review the research findings objectively
- Identify what's missing or incomplete
- Assess confidence in the findings
- Suggest next steps if needed

Be honest and critical - better to catch gaps now than in the final report.
"""

REFLECTION_HUMAN = """
Research question:
{question}

Findings:
{findings}

Original context sample (first 2000 chars):
{context_sample}

REFLECTION TASK:
1. Is the research complete and thorough?
2. What aspects might be missing or need more detail?
3. FOR NEWS ITEMS: Are dates as precise as possible? Did you check for ISO dates (YYYY-MM-DD), full written dates, and timestamps?
4. What's your confidence level? (high/medium/low)
5. What should be done next to improve these findings?

CRITICAL FOR NEWS QUESTIONS:
- If you have vague dates like "2025" or "Q4 2025", did you search for more precise dates?
- Did you check the source content for ISO format dates like "2025-06-25"?
- Did you look for phrases like "announced on", "as of", "dated", publication dates?
- DATE VALIDATION: Are there any dates AFTER November 27, 2025? If yes, they are INVALID and should be removed/replaced
- COMPLETENESS CHECK: If the question is about news, did you extract EVERY news item from ALL sources? Count them - did you extract 5 items? 10? 20? Are you sure there aren't more?
- Did you search for: fund closures, acquisitions, exits, appointments, partnerships, awards, surveys, press releases?

Be critical and thorough in your assessment.
"""

REFLECTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", REFLECTION_SYSTEM),
    ("user", REFLECTION_HUMAN),
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
        chunks.append(f"=== SOURCE [{i}] ===\nURL: {p.url}\nTitle: {p.title}\n\n{p.text}\n")
    return "\n\n" + "="*80 + "\n\n".join(chunks)


def execute_sub_agent(
    task: SubAgentTask,
    pages: List[PageContent],
    company_name: str
) -> SubAgentResult:
    """Execute a sub-agent research task with reflection.

    Args:
        task: The research task assignment
        pages: All available page content
        company_name: Name of the company being researched

    Returns:
        SubAgentResult with findings and reflection
    """
    llm = get_llm()
    reflection_llm = get_llm().with_structured_output(Reflection)

    # Build context from all pages
    context = build_context(pages)

    # Step 1: Research - Sub-agent analyzes content
    print(f"  → Sub-agent working on: {task.task_id}")
    research_response = (SUB_AGENT_PROMPT | llm).invoke({
        "question": task.question,
        "company_name": company_name,
        "context": context,
    })

    findings = research_response.content

    # Step 2: Reflection - Self-critique
    print(f"  → Sub-agent reflecting on: {task.task_id}")
    context_sample = context[:2000]  # Sample for reflection
    reflection = (REFLECTION_PROMPT | reflection_llm).invoke({
        "question": task.question,
        "findings": findings,
        "context_sample": context_sample,
    })

    # Collect sources from pages
    sources = [p.url for p in pages]

    result = SubAgentResult(
        task_id=task.task_id,
        findings=findings,
        reflection=reflection,
        sources=sources
    )

    print(f"  ✓ Sub-agent completed: {task.task_id} (confidence: {reflection.confidence})")

    return result
