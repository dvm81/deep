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
    print("\n" + "="*80)
    print("PHASE 2: RESEARCH SUPERVISOR")
    print("="*80)

    scraper = CompanyScraper(brief=state.brief)

    # Step 1: Fetch all seed URLs
    print("\n[1/4] Fetching seed URLs...")
    for url in state.brief.seed_urls:
        url_str = str(url)
        if url_str not in state.pages:
            try:
                print(f"  Fetching: {url_str}")
                page = scraper.fetch(url_str)
                state.pages[url_str] = page
                save_page(page)
            except Exception as e:
                print(f"  ⚠ Warning: Failed to fetch {url_str}: {str(e)}")
                continue

    pages_list = list(state.pages.values())
    print(f"  ✓ Fetched {len(pages_list)} pages")

    # Step 2: Create sub-agent tasks
    print("\n[2/4] Creating sub-agent tasks...")
    tasks = []
    for idx, question in enumerate(state.brief.sub_questions):
        task = SubAgentTask(
            task_id=f"q_{idx}",
            question=question,
            context_urls=[p.url for p in pages_list]
        )
        tasks.append(task)
        print(f"  Task {idx + 1}: {task.task_id}")

    # Step 3: Execute sub-agents in parallel
    print(f"\n[3/4] Executing {len(tasks)} sub-agents in parallel...")
    results = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all sub-agent tasks
        future_to_task = {
            executor.submit(execute_sub_agent, task, pages_list, state.brief.company_name): task
            for task in tasks
        }

        # Collect results as they complete
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                results[result.task_id] = result
            except Exception as e:
                print(f"  ✗ Sub-agent {task.task_id} failed: {str(e)}")

    print(f"  ✓ Completed {len(results)}/{len(tasks)} sub-agents")

    # Step 4: Supervisor review
    print("\n[4/4] Supervisor reviewing findings...")
    review_llm = get_llm().with_structured_output(SupervisorReview)

    # Prepare findings summary
    findings_summary = ""
    reflections = ""
    for task_id, result in results.items():
        findings_summary += f"\n### {task_id}\n{result.findings[:500]}...\n"
        reflections += f"\n### {task_id}\nComplete: {result.reflection.is_complete}, "
        reflections += f"Confidence: {result.reflection.confidence}\n"
        if result.reflection.missing_aspects:
            reflections += f"Missing: {', '.join(result.reflection.missing_aspects)}\n"

    supervisor_review = (SUPERVISOR_REVIEW_PROMPT | review_llm).invoke({
        "company_name": state.brief.company_name,
        "research_brief": state.brief.main_question,
        "findings_summary": findings_summary,
        "reflections": reflections,
    })

    print(f"  Completeness: {supervisor_review.overall_completeness}")
    print(f"  Ready for writing: {supervisor_review.ready_for_writing}")
    if supervisor_review.gaps_identified:
        print(f"  Gaps identified: {len(supervisor_review.gaps_identified)}")

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
