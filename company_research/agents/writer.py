"""Writer agent for generating the final report."""

from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from ..config import get_llm
from ..schema import ResearchState
from ..storage import save_report


FINAL_REPORT_SYSTEM = """
You are a meticulous professional financial analyst and report writer.

CURRENT DATE: November 27, 2025

You will receive:
- A research brief that defines the question to answer
- Comprehensive research notes with complete findings from web research

Your job is to write a detailed, structured markdown report that includes EVERY piece of relevant information.

CRITICAL REQUIREMENTS:
- Use ONLY the information in the provided notes
- Include ALL names, titles, companies, funds, dates, amounts mentioned in the notes
- DO NOT summarize or condense - include complete details
- Every factual claim MUST have an inline citation [1], [2], etc.
- For news/announcements dates:
  * REJECT ANY DATES AFTER November 27, 2025 (invalid future dates)
  * Use the MOST PRECISE VALID date available in research notes
  * Format as "Month DD, YYYY" (e.g., "October 31, 2025")
  * Never use "2025" if the notes contain "October 31, 2025"
  * Never use "Q4 2025" if the notes contain a specific month/day
  * If you encounter dates in 2026 or later, use "Not Disclosed" instead
  * Only use vague dates (year, quarter) if that's all that's available AND valid
- If specific information is not in the notes, state "Not disclosed on the company's website"
- Maintain a professional financial/institutional investor tone
"""

FINAL_REPORT_HUMAN = """
Company: {company_name}

Research brief:
{brief}

Comprehensive research notes:
{notes}

Write a detailed markdown report with the following sections:

1. **Executive Summary** - High-level overview with key findings

2. **Private Investing / Private Markets Overview** - Complete description of their operations

3. **Key Decision Makers**
   - List EVERY name with complete title/position found in the notes
   - If names not disclosed, state clearly

4. **Regions and Sectors**
   - List ALL regions and sectors mentioned
   - Include complete details about each

5. **Assets Under Management and Platform Metrics**
   - Include ALL numbers, amounts, statistics found
   - If not disclosed, state clearly

6. **Portfolio Companies or Deal Examples**
   - Create comprehensive markdown table(s) with ALL companies mentioned
   - Include columns for: Company Name, Sector, Stage, Details (if available)
   - If not disclosed, state clearly

7. **Strategies / Funds / Programs**
   - List ALL strategies, funds, and programs by name
   - Include complete descriptions for each
   - Use sub-sections if needed

8. **Recent News & Announcements**
   - Create comprehensive markdown table with ALL news items
   - Columns: Date, Headline/Topic, Description
   - CRITICAL DATE FORMATTING:
     * REJECT dates after November 27, 2025 (invalid/future dates)
     * Use the MOST PRECISE VALID date from research notes
     * Preferred format: "Month DD, YYYY" (e.g., "June 25, 2025")
     * If only month+year: "Month YYYY" (e.g., "June 2025")
     * If only year: "YYYY" (e.g., "2025")
     * NEVER use vague dates if precise dates are in the notes
     * If research notes contain dates in 2026+, use "Not Disclosed"
   - Sort by date (most recent first)
   - If no news items found at all, state clearly

9. **Conclusion** - Summary of key findings

10. **Sources** - Complete list mapping citation numbers to URLs

CRITICAL INSTRUCTIONS:
- Include EVERY detail from the research notes
- Use tables extensively for structured data
- Cite every claim with [1], [2], etc.
- Be comprehensive, not concise
- The goal is completeness and accuracy
"""

WRITER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", FINAL_REPORT_SYSTEM),
    ("user", FINAL_REPORT_HUMAN),
])


def writer_node(state: ResearchState) -> Dict[str, Any]:
    """Execute the writing phase.

    This node:
    1. Compiles all research notes
    2. Generates a professional markdown report
    3. Saves the report to file

    Args:
        state: Current research state

    Returns:
        Dictionary with the report markdown
    """
    llm = get_llm()

    notes_text = ""
    for k, note in state.notes.items():
        notes_text += f"### {k}\n{note.content}\n\n"

    resp = (WRITER_PROMPT | llm).invoke({
        "company_name": state.brief.company_name,
        "brief": state.brief.main_question,
        "notes": notes_text,
    })

    report_md = resp.content
    state.report_markdown = report_md
    save_report(report_md, state.brief.company_name)
    return {"report_markdown": report_md}
