"""Research supervisor that coordinates sub-agents."""

from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_core.prompts import ChatPromptTemplate
from ..config import get_llm
from ..schema import (
    ResearchState, Note, SubAgentTask, SubAgentResult, SupervisorReview
)
from ..scraping import CompanyScraper
from ..storage import save_page
from .sub_agent import execute_sub_agent
from ..logger import (
    log_phase, log_step, log_llm_call, log_verbose, log_success,
    log_warning, log_error, log_metric, Colors, Timer, format_size
)


SUPERVISOR_REVIEW_SYSTEM = """
You are a research supervisor reviewing findings from multiple specialized sub-agents.

CURRENT DATE: November 27, 2025

Your role:
- Review all sub-agent findings for completeness
- Identify any gaps or missing information
- Assess whether findings are ready for report generation
- Provide constructive feedback

Consider:
- Did each sub-agent extract ALL relevant details?
- Are there any obvious gaps or missing information?
- Are the findings comprehensive enough for a professional report?
- Did sub-agents properly cite their sources?
"""

SUPERVISOR_REVIEW_HUMAN = """
Company: {company_name}

Research brief:
{research_brief}

Sub-agent findings summary:
{findings_summary}

Sub-agent reflections:
{reflections}

REVIEW TASK:
1. Assess overall completeness of the research
2. Identify any gaps or missing information across all findings
3. Determine if findings are ready for report generation
4. Decide if refinement iteration is needed (set to false for now - we'll add iterative refinement later)

Provide your assessment.
"""

SUPERVISOR_REVIEW_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SUPERVISOR_REVIEW_SYSTEM),
    ("user", SUPERVISOR_REVIEW_HUMAN),
])


def supervisor_node(state: ResearchState) -> Dict[str, Any]:
    """Execute the research supervision phase with parallel sub-agents.

    This node:
    1. Fetches all seed URLs
    2. Creates sub-agent tasks for each research question
    3. Executes sub-agents in parallel
    4. Reviews all findings
    5. Compiles results into notes

    Args:
        state: Current research state

    Returns:
        Dictionary with updated pages, sub_agent_results, supervisor_review, and notes
    """
    log_phase(2, "RESEARCH SUPERVISOR")

    scraper = CompanyScraper(brief=state.brief)

    # Step 1: Fetch all seed URLs
    log_step(f"{Colors.GLOBE} [1/4] Fetching seed URLs...", emoji="")
    total_size = 0
    fetch_count = 0

    with Timer("URL Fetching") as fetch_timer:
        for url in state.brief.seed_urls:
            url_str = str(url)
            if url_str not in state.pages:
                try:
                    print(f"   {Colors.LINK} Fetching: {Colors.DIM}{url_str}{Colors.RESET}")
                    page = scraper.fetch(url_str)
                    state.pages[url_str] = page
                    save_page(page)

                    # Track metrics
                    page_size = len(page.text)
                    total_size += page_size
                    fetch_count += 1

                    log_verbose(f"      HTTP Status: 200")
                    log_verbose(f"      Raw HTML: {format_size(len(page.raw_html))}")
                    log_verbose(f"      Markdown: {format_size(page_size)}")
                    log_verbose(f"      Title: {page.title[:60]}")

                except Exception as e:
                    log_warning(f"Failed to fetch {url_str}: {str(e)}", indent=1)
                    continue

    pages_list = list(state.pages.values())
    log_success(f"Fetched {fetch_count}/{len(state.brief.seed_urls)} pages (total: {format_size(total_size)})", indent=1)
    log_verbose(f"   Average page size: {format_size(total_size // len(pages_list)) if pages_list else '0 B'}")
    log_verbose(f"   Total fetch time: {fetch_timer.elapsed():.1f}s")

    # Step 2: Create sub-agent tasks
    log_step(f"\n{Colors.TARGET} [2/4] Creating sub-agent tasks...", emoji="")
    tasks = []
    for idx, question in enumerate(state.brief.sub_questions):
        task = SubAgentTask(
            task_id=f"q_{idx}",
            question=question,
            context_urls=[p.url for p in pages_list]
        )
        tasks.append(task)

        # Show shortened question
        short_q = question[:65] + "..." if len(question) > 65 else question
        print(f"   {Colors.DIM}Task {idx + 1}: {task.task_id} - {short_q}{Colors.RESET}")
        log_verbose(f"      Full question: {question}")
        log_verbose(f"      Context: {len(pages_list)} pages, {format_size(total_size)}")

    # Step 3: Execute sub-agents in parallel
    log_step(f"\n{Colors.ROBOT} [3/4] Executing {len(tasks)} sub-agents in parallel (3 workers)...", emoji="")
    log_verbose(f"   ThreadPoolExecutor configured with max_workers=3")
    results = {}

    with Timer("Parallel Sub-Agent Execution") as parallel_timer:
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all sub-agent tasks
            future_to_task = {
                executor.submit(execute_sub_agent, task, pages_list, state.brief.company_name): task
                for task in tasks
            }

            log_verbose(f"   Submitted {len(future_to_task)} tasks to executor")

            # Collect results as they complete
            completed_count = 0
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results[result.task_id] = result
                    completed_count += 1

                    # Show progress
                    log_verbose(f"   ✓ {completed_count}/{len(tasks)} complete: {task.task_id}")

                except Exception as e:
                    log_error(f"Sub-agent {task.task_id} failed: {str(e)}", indent=1)

    log_success(f"Completed {len(results)}/{len(tasks)} sub-agents in {parallel_timer.elapsed():.1f}s", indent=1)
    log_verbose(f"   Average time per sub-agent: {parallel_timer.elapsed() / len(results):.1f}s" if results else "   No results")

    # Step 4: Supervisor review
    log_step(f"\n{Colors.CHART} [4/4] Supervisor reviewing findings...", emoji="")
    review_llm = get_llm().with_structured_output(SupervisorReview)

    # Prepare findings summary
    log_verbose(f"   Compiling findings from {len(results)} sub-agents...")
    findings_summary = ""
    reflections = ""
    total_findings_size = 0

    for task_id, result in results.items():
        findings_summary += f"\n### {task_id}\n{result.findings[:500]}...\n"
        reflections += f"\n### {task_id}\nComplete: {result.reflection.is_complete}, "
        reflections += f"Confidence: {result.reflection.confidence}\n"
        if result.reflection.missing_aspects:
            reflections += f"Missing: {', '.join(result.reflection.missing_aspects)}\n"

        total_findings_size += len(result.findings)
        log_verbose(f"      {task_id}: {format_size(len(result.findings))}, confidence={result.reflection.confidence}")

    log_verbose(f"   Total findings: {format_size(total_findings_size)}")

    # Invoke supervisor review
    review_prompt_text = SUPERVISOR_REVIEW_PROMPT.format(
        company_name=state.brief.company_name,
        research_brief=state.brief.main_question,
        findings_summary=findings_summary[:500] + "...",
        reflections=reflections[:500] + "..."
    )

    with Timer("Supervisor Review"):
        supervisor_review = (SUPERVISOR_REVIEW_PROMPT | review_llm).invoke({
            "company_name": state.brief.company_name,
            "research_brief": state.brief.main_question,
            "findings_summary": findings_summary,
            "reflections": reflections,
        })

    log_llm_call(
        purpose="Supervisor Review & Gap Analysis",
        prompt_preview=review_prompt_text,
        response_preview=f"Completeness: {supervisor_review.overall_completeness}, Ready: {supervisor_review.ready_for_writing}",
        truncate=600
    )

    # Display review results
    print(f"\n   {Colors.BOLD}Supervisor Assessment:{Colors.RESET}")
    log_metric("Completeness", supervisor_review.overall_completeness, "", indent=1)
    log_metric("Ready for Writing", supervisor_review.ready_for_writing, "", indent=1)

    if supervisor_review.gaps_identified:
        log_metric("Gaps Identified", len(supervisor_review.gaps_identified), "gaps", indent=1)
        log_verbose(f"      Gaps: {', '.join(supervisor_review.gaps_identified[:3])}")

    # Step 5: Convert sub-agent results to notes for the writer
    notes = {}
    for task_id, result in results.items():
        notes[task_id] = Note(
            question_id=task_id,
            content=result.findings,
            sources=result.sources
        )

    state.sub_agent_results = results
    state.supervisor_review = supervisor_review
    state.notes = notes

    print(f"\n✓ Research supervision complete")
    print("="*80 + "\n")

    return {
        "pages": state.pages,
        "sub_agent_results": state.sub_agent_results,
        "supervisor_review": state.supervisor_review,
        "notes": state.notes
    }
