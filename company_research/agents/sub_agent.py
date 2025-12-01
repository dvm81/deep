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
3. What's your confidence level? (high/medium/low)
4. What should be done next to improve these findings?

{question_specific_checklist}

Be critical and thorough in your assessment.
"""

REFLECTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", REFLECTION_SYSTEM),
    ("user", REFLECTION_HUMAN),
])


# V2.7: Refinement prompt for targeted follow-up
REFINEMENT_SYSTEM = """
You are a specialized research sub-agent conducting TARGETED FOLLOW-UP research.

CURRENT DATE: November 27, 2025

Context:
- You previously researched this question and found some information
- Your reflection identified specific gaps or missing information
- You are now conducting a FOCUSED second-pass to address those gaps

Your role:
- Review what you found previously
- Focus SPECIFICALLY on the identified gaps
- Search the content with laser precision for the missing information
- Extract ONLY the new/missing information (don't repeat what was already found)

CRITICAL: This is targeted refinement, not a full re-do:
- Address the SPECIFIC gap mentioned
- Search in sections you may have missed (news, press releases, footnotes, etc.)
- Extract precise details (names, dates, amounts) that were missed before
- Use inline citations [1], [2], [3] for new findings
"""

REFINEMENT_HUMAN = """
Your original research question:
{question}

Company: {company_name}

Your previous findings (truncated):
{previous_findings}

IDENTIFIED GAP TO ADDRESS:
{gap_to_address}

{targeted_snippets_section}

Complete context from all available sources:
{context}

REFINEMENT TASK:
1. Review your previous findings above
2. {mcp_instruction}
3. Search through the context for ONLY the missing information
4. Extract precise details that address the gap
5. Use inline citations [1], [2] for new findings
6. Be concise - only report NEW information that fills the gap

What new information can you find to address the gap?
"""

REFINEMENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", REFINEMENT_SYSTEM),
    ("user", REFINEMENT_HUMAN),
])


def get_reflection_checklist(question: str) -> str:
    """Generate question-type-specific reflection checklist.

    V2.9: Enhanced reflection with targeted checklists for quality

    Args:
        question: The research question

    Returns:
        Formatted checklist string for reflection prompt
    """
    question_lower = question.lower()

    # NEWS/ANNOUNCEMENTS CHECKLIST
    if any(word in question_lower for word in ["news", "announcement", "press release"]):
        return """
CRITICAL CHECKLIST FOR NEWS QUESTIONS:
☐ Did you count all news items? How many did you extract? (5? 10? 20?)
☐ Did you search ALL sources for: fund closures, acquisitions, exits, appointments, partnerships, awards, surveys, press releases?
☐ Are dates as precise as possible? Did you check for:
   - ISO dates (YYYY-MM-DD like "2025-06-25")
   - Full written dates ("June 25, 2025", "October 31, 2025")
   - Quarter dates ("Q4 2025")
   - Month-year dates ("November 2025")
   - Publication timestamps in metadata
☐ DATE VALIDATION: Are there any dates AFTER November 27, 2025? If yes, they are INVALID
☐ Did you check phrases like "announced on", "as of", "dated" for dates?
☐ Did you extract headlines/titles for each news item?
☐ Are you CERTAIN there aren't more news items you missed?
"""

    # PEOPLE/LEADERSHIP CHECKLIST
    elif any(word in question_lower for word in ["decision maker", "leadership", "team", "people", "executive"]):
        return """
CRITICAL CHECKLIST FOR PEOPLE/LEADERSHIP QUESTIONS:
☐ Did you extract EVERY name mentioned across ALL pages?
☐ Did EVERY person have a complete title/position?
☐ Did you check for:
   - Executive titles (CEO, CTO, CFO, COO, Managing Director, Partner)
   - Senior titles (Senior Partner, Principal, Executive Director)
   - Academic credentials (PhD, MD, MBA, JD, CFA)
   - Board roles (Board Member, Trustee, Independent Director)
☐ Did you search team pages, about pages, leadership pages, bios?
☐ Did you look for team listings in case studies or news items?
☐ Did you count how many people you extracted? Is that comprehensive for this company size?
☐ Did you check for Advisory Board or Board of Directors separately?
"""

    # PORTFOLIO/COMPANIES CHECKLIST
    elif any(word in question_lower for word in ["portfolio", "compan", "invest", "firm"]):
        return """
CRITICAL CHECKLIST FOR PORTFOLIO/COMPANIES QUESTIONS:
☐ Did you count how many companies you extracted?
☐ Did you search ALL sources including: portfolio pages, case studies, press releases, news items?
☐ For each company, did you extract:
   - Company name (exact spelling)
   - Sector/industry
   - Stage (early, late, growth, etc.)
   - Any other details (location, investment date, ownership)
☐ Did you check case study pages for additional companies?
☐ Did you check news announcements for recent investments/acquisitions?
☐ Did you look for portfolio lists, tables, or structured data?
☐ Are you CERTAIN you didn't miss any companies mentioned in the sources?
"""

    # AUM/FINANCIAL METRICS CHECKLIST
    elif any(word in question_lower for word in ["aum", "assets under management", "fund size", "capital"]):
        return """
CRITICAL CHECKLIST FOR FINANCIAL METRICS QUESTIONS:
☐ Did you find specific dollar amounts? ($500M, $2.5B, etc.)
☐ Did you find percentages? (ownership stakes, returns, growth rates)
☐ Did you extract dates for when these metrics were reported?
☐ Did you search for: total AUM, fund sizes, committed capital, dry powder?
☐ Did you check multiple pages (about, fund pages, press releases) for metrics?
☐ Did you find metrics for individual funds vs. total platform?
☐ If no metrics found, did you check footnotes, disclaimers, regulatory disclosures?
☐ Did you note if metrics are "as of" a specific date?
"""

    # STRATEGY/FUNDS CHECKLIST
    elif any(word in question_lower for word in ["strateg", "fund", "program"]):
        return """
CRITICAL CHECKLIST FOR STRATEGY/FUNDS QUESTIONS:
☐ Did you list EVERY fund/strategy mentioned by name?
☐ For each strategy, did you extract:
   - Official name
   - Focus area (sector, stage, geography)
   - Description/approach
   - Fund size (if available)
☐ Did you check dedicated strategy/fund pages?
☐ Did you look for sub-strategies or programs within main strategies?
☐ Did you count how many strategies you found? Is that complete?
☐ Did you check for vintage/launch dates?
"""

    # GENERIC CHECKLIST
    else:
        return """
CRITICAL CHECKLIST:
☐ Did you extract ALL relevant information from ALL sources?
☐ Did you use specific details (names, dates, numbers) rather than summaries?
☐ Did you check all pages including case studies, news, and specialized sections?
☐ Are you confident this is comprehensive or might you have missed information?
☐ Did you use inline citations [1], [2], [3] for every fact?
"""


def extract_keywords(question: str) -> List[str]:
    """Extract key terms from question for relevance ranking.

    V2.9: Helper for smart context building

    Args:
        question: Research question

    Returns:
        List of keywords to look for
    """
    keywords = []
    question_lower = question.lower()

    # Question-type keywords
    if "news" in question_lower or "announcement" in question_lower:
        keywords.extend(["news", "announcement", "press release", "announced", "partnership", "acquisition", "fund closure", "appointment", "award"])
    if "decision maker" in question_lower or "leadership" in question_lower or "team" in question_lower:
        keywords.extend(["team", "leadership", "partner", "director", "executive", "ceo", "cfo", "cto", "management", "our team"])
    if "portfolio" in question_lower or "companies" in question_lower or "invest" in question_lower:
        keywords.extend(["portfolio", "investment", "company", "companies", "case study", "exits", "acquisition"])
    if "aum" in question_lower or "assets" in question_lower:
        keywords.extend(["aum", "assets under management", "billion", "million", "capital", "fund size"])
    if "strategy" in question_lower or "fund" in question_lower:
        keywords.extend(["strategy", "fund", "approach", "focus", "program", "venture", "growth", "stage"])
    if "region" in question_lower or "sector" in question_lower:
        keywords.extend(["region", "sector", "industry", "geography", "market", "focus area"])

    return keywords


def calculate_page_relevance(page: PageContent, keywords: List[str]) -> float:
    """Calculate relevance score for a page based on keywords.

    V2.9: Used for smart context ranking

    Args:
        page: Page content
        keywords: List of keywords to search for

    Returns:
        Relevance score (higher is more relevant)
    """
    if not keywords:
        return 1.0  # No keywords = equal relevance

    text_lower = (page.title + " " + page.text).lower()
    score = 0.0

    for keyword in keywords:
        # Count occurrences (normalized by text length to favor density over volume)
        count = text_lower.count(keyword.lower())
        if count > 0:
            # Title matches worth more
            if keyword.lower() in page.title.lower():
                score += 5.0
            # Content matches
            score += count * (1000.0 / max(len(text_lower), 1000))  # Normalize by text length

    return score


def build_context(pages: List[PageContent], question: str = None) -> str:
    """Build context string from pages with smart relevance ranking.

    V2.9: Pages are ranked by keyword relevance to question,
    with most relevant pages placed first for better LLM attention.

    Args:
        pages: List of PageContent objects
        question: Research question (optional, for smart ranking)

    Returns:
        Formatted context string with content ranked by relevance
    """
    # Smart ranking if question provided
    if question:
        keywords = extract_keywords(question)
        if keywords:
            # Calculate relevance and sort
            pages_with_scores = [(p, calculate_page_relevance(p, keywords)) for p in pages]
            pages_with_scores.sort(key=lambda x: x[1], reverse=True)
            sorted_pages = [p for p, score in pages_with_scores]

            log_verbose(f"      Context ranking: Using {len(keywords)} keywords to rank {len(pages)} pages")
        else:
            sorted_pages = pages
    else:
        sorted_pages = pages

    # Build context with ranked pages
    chunks = []
    for i, p in enumerate(sorted_pages, start=1):
        chunks.append(f"=== SOURCE [{i}] ===\nURL: {p.url}\nTitle: {p.title}\n\n{p.text}\n")
    return "\n\n" + "="*80 + "\n\n".join(chunks)


def execute_sub_agent(
    task: SubAgentTask,
    pages: List[PageContent],
    company_name: str,
    original_question: str = None
) -> SubAgentResult:
    """Execute a sub-agent research task with reflection.

    Args:
        task: The research task assignment
        pages: All available page content
        company_name: Name of the company being researched
        original_question: Original question text (for refinement tasks)

    Returns:
        SubAgentResult with findings and reflection
    """
    llm = get_llm()
    reflection_llm = get_llm().with_structured_output(Reflection)

    # Build context from all pages with smart ranking
    # V2.9: Context now ranked by keyword relevance to question
    log_verbose(f"   Building context for {task.task_id}...")
    question_for_context = original_question if task.is_refinement and original_question else task.question
    context = build_context(pages, question=question_for_context)
    context_size = len(context)
    log_verbose(f"      Context size: {format_size(context_size)} from {len(pages)} pages")

    # Step 1: Research - Sub-agent analyzes content
    if task.is_refinement:
        print(f"  → Sub-agent REFINING: {task.task_id}")
        log_verbose(f"      Mode: Targeted refinement (second-pass)")

        # V2.8: Build MCP snippets section
        if task.targeted_snippets:
            targeted_snippets_section = f"""
=== TARGETED SNIPPETS (MCP Intelligent Search) ===

The following snippets were extracted using pattern matching (patterns: {', '.join(task.search_patterns_used)}).
These are the MOST LIKELY locations of the missing information.

{task.targeted_snippets}

=== END TARGETED SNIPPETS ===
"""
            mcp_instruction = "START with the targeted snippets above - they contain patterns matching your gap"
            log_verbose(f"      Using {len(task.targeted_snippets)} chars of MCP-targeted snippets")
        else:
            targeted_snippets_section = ""
            mcp_instruction = "Focus SPECIFICALLY on the identified gap"

        # Use refinement prompt
        question_text = original_question if original_question else task.question
        research_prompt_text = REFINEMENT_PROMPT.format(
            question=question_text,
            company_name=company_name,
            previous_findings=task.previous_findings,
            gap_to_address=task.gap_to_address,
            targeted_snippets_section=targeted_snippets_section,
            mcp_instruction=mcp_instruction,
            context=context[:500] + "..."
        )

        research_response = (REFINEMENT_PROMPT | llm).invoke({
            "question": question_text,
            "company_name": company_name,
            "previous_findings": task.previous_findings,
            "gap_to_address": task.gap_to_address,
            "targeted_snippets_section": targeted_snippets_section,
            "mcp_instruction": mcp_instruction,
            "context": context,
        })
    else:
        print(f"  → Sub-agent working on: {task.task_id}")
        log_verbose(f"      Mode: Initial research (first-pass)")

        # Use regular prompt
        research_prompt_text = SUB_AGENT_PROMPT.format(
            question=task.question,
            company_name=company_name,
            context=context[:500] + "..."
        )

        research_response = (SUB_AGENT_PROMPT | llm).invoke({
            "question": task.question,
            "company_name": company_name,
            "context": context,
        })

    findings = research_response.content

    mode_label = "Refinement" if task.is_refinement else "Research"
    log_llm_call(
        purpose=f"Sub-Agent {mode_label}: {task.task_id}",
        prompt_preview=research_prompt_text,
        response_preview=findings,
        truncate=400
    )

    log_verbose(f"      Findings size: {format_size(len(findings))}")

    # Step 2: Reflection - Self-critique
    # V2.9: Enhanced with question-specific checklists
    print(f"  → Sub-agent reflecting on: {task.task_id}")
    context_sample = context[:2000]  # Sample for reflection

    # Get question-specific checklist for targeted reflection
    question_for_checklist = original_question if task.is_refinement and original_question else task.question
    checklist = get_reflection_checklist(question_for_checklist)

    reflection_prompt_text = REFLECTION_PROMPT.format(
        question=task.question,
        findings=findings[:500] + "...",
        context_sample=context_sample[:300] + "...",
        question_specific_checklist=checklist[:200] + "..."
    )

    reflection = (REFLECTION_PROMPT | reflection_llm).invoke({
        "question": task.question,
        "findings": findings,
        "context_sample": context_sample,
        "question_specific_checklist": checklist,
    })

    log_llm_call(
        purpose=f"Sub-Agent Reflection: {task.task_id}",
        prompt_preview=reflection_prompt_text,
        response_preview=f"Complete: {reflection.is_complete}, Confidence: {reflection.confidence}",
        truncate=400
    )

    # Log reflection details
    log_verbose(f"      Reflection assessment:")
    log_verbose(f"         Is Complete: {reflection.is_complete}")
    log_verbose(f"         Confidence: {reflection.confidence}")
    if reflection.missing_aspects:
        log_verbose(f"         Missing Aspects: {', '.join(reflection.missing_aspects[:3])}")
    if reflection.next_steps:
        log_verbose(f"         Next Steps: {reflection.next_steps[:100]}...")

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
