"""Writer agent for generating the final report."""

from typing import Dict, Any
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from ..config import get_llm
from ..schema import ResearchState, StructuredReport
from ..storage import save_report, save_report_json
from ..logger import (
    log_phase, log_step, log_llm_call, log_verbose, log_success,
    log_metric, Colors, Timer, format_size
)


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
  * IMPORTANT: Research notes may contain dates from 2025 (some might say "November 2025", "October 2025" for recent items)
  * Use the MOST PRECISE date available in research notes
  * Format as "Month DD, YYYY" (e.g., "October 31, 2025") if day is available
  * Format as "Month YYYY" (e.g., "November 2025", "October 2025") if only month/year available
  * Never use "2025" if the notes contain "October 31, 2025" or "October 2025"
  * Never use "Q4 2025" if the notes contain a specific month
  * Include all news items from notes, even if dated as recently as November 2025
  * Only use vague dates (year, quarter) if that's all that's available
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
     * Use the MOST PRECISE date from research notes
     * Preferred format: "Month DD, YYYY" (e.g., "June 25, 2025")
     * If only month+year: "Month YYYY" (e.g., "November 2025", "October 2025")
     * If only year: "YYYY" (e.g., "2025")
     * NEVER use vague dates if precise dates are in the notes
     * Include ALL news items from notes, even recent ones from November 2025 or October 2025
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


# JSON structured output prompt
JSON_EXTRACTOR_SYSTEM = """
You are a data extraction specialist converting markdown research reports into structured JSON format.

CURRENT DATE: November 27, 2025

Your task:
- Extract key information from the markdown report
- Structure it according to the JSON schema
- Preserve all important details
- Maintain data accuracy
"""

JSON_EXTRACTOR_HUMAN = """
Extract structured data from this research report and format it as JSON.

Company: {company_name}

Full Markdown Report:
{markdown_report}

Instructions:
1. Extract executive summary and overview text
2. Parse key decision makers into structured list (name, title, location)
3. Extract regions and sectors as separate lists
4. Parse AUM metrics
5. Convert portfolio companies table to structured list
6. Extract strategies/funds/programs with descriptions
7. Parse news announcements table (date, headline, description)
8. Extract conclusion
9. Extract all source URLs

Return structured JSON matching the StructuredReport schema.
"""

JSON_EXTRACTOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", JSON_EXTRACTOR_SYSTEM),
    ("user", JSON_EXTRACTOR_HUMAN),
])


def writer_node(state: ResearchState) -> Dict[str, Any]:
    """Execute the writing phase.

    This node:
    1. Compiles all research notes
    2. Generates a professional markdown report
    3. Generates structured JSON report
    4. Saves both reports to files

    Args:
        state: Current research state

    Returns:
        Dictionary with the report markdown and JSON
    """
    log_phase(3, "REPORT WRITING")

    llm = get_llm()
    json_llm = get_llm().with_structured_output(StructuredReport, method="function_calling")

    # Step 1: Compile research notes
    log_step(f"{Colors.WRITE} [1/2] Compiling research notes...", emoji="")
    log_verbose(f"   Compiling {len(state.notes)} research notes...")

    notes_text = ""
    total_notes_size = 0
    for k, note in state.notes.items():
        note_section = f"### {k}\n{note.content}\n\n"
        notes_text += note_section
        total_notes_size += len(note.content)
        log_verbose(f"      {k}: {format_size(len(note.content))}, {len(note.sources)} sources")

    log_success(f"Compiled {len(state.notes)} notes (total: {format_size(total_notes_size)})", indent=1)
    log_verbose(f"   Average note size: {format_size(total_notes_size // len(state.notes))}")

    # Generate markdown report
    log_step(f"\n{Colors.WRITE} Generating markdown report...", emoji="")

    # Prepare prompt preview for logging
    writer_prompt_text = WRITER_PROMPT.format(
        company_name=state.brief.company_name,
        brief=state.brief.main_question,
        notes=notes_text[:800] + "..."  # Truncated for preview
    )

    with Timer("Markdown Report Generation"):
        resp = (WRITER_PROMPT | llm).invoke({
            "company_name": state.brief.company_name,
            "brief": state.brief.main_question,
            "notes": notes_text,
        })

    report_md = resp.content

    log_llm_call(
        purpose="Markdown Report Generation",
        prompt_preview=writer_prompt_text,
        response_preview=report_md,
        truncate=600
    )

    # Calculate report statistics
    lines = report_md.count('\n') + 1
    report_size = len(report_md)
    log_verbose(f"   Report statistics:")
    log_verbose(f"      Size: {format_size(report_size)}")
    log_verbose(f"      Lines: {lines}")
    log_verbose(f"      Citations: {report_md.count('[')}")

    state.report_markdown = report_md
    save_report(report_md, state.brief.company_name)
    log_success(f"Markdown report saved ({format_size(report_size)}, {lines} lines)", indent=1)

    # Step 2: Generate structured JSON report
    log_step(f"\n{Colors.WRITE} [2/2] Generating structured JSON report...", emoji="")

    # Prepare JSON extractor prompt for logging
    json_prompt_text = JSON_EXTRACTOR_PROMPT.format(
        company_name=state.brief.company_name,
        markdown_report=report_md[:800] + "..."  # Truncated for preview
    )

    with Timer("JSON Report Extraction"):
        structured_report = (JSON_EXTRACTOR_PROMPT | json_llm).invoke({
            "company_name": state.brief.company_name,
            "markdown_report": report_md,
        })

    # Add report date
    structured_report.report_date = datetime.now().strftime("%Y-%m-%d")

    # Convert to dict for storage
    report_json = structured_report.model_dump()

    log_llm_call(
        purpose="JSON Data Extraction",
        prompt_preview=json_prompt_text,
        response_preview=f"Company: {structured_report.company_name}, Sections: {len(report_json)}",
        truncate=400
    )

    # Log JSON report statistics
    json_size = len(str(report_json))
    log_verbose(f"   JSON report statistics:")
    log_verbose(f"      Size: {format_size(json_size)}")
    log_verbose(f"      Key Decision Makers: {len(structured_report.key_decision_makers)}")
    log_verbose(f"      Portfolio Companies: {len(structured_report.portfolio_companies)}")
    log_verbose(f"      News Items: {len(structured_report.news_announcements)}")
    log_verbose(f"      Sources: {len(structured_report.sources)}")

    state.report_json = report_json
    save_report_json(report_json, state.brief.company_name)
    log_success(f"JSON report saved ({format_size(json_size)})", indent=1)

    print(f"\n✓ Report writing complete")
    print("="*80 + "\n")

    return {
        "report_markdown": report_md,
        "report_json": report_json
    }
