"""Refinement node for targeted follow-up research."""

from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from ..schema import ResearchState, SubAgentTask, SubAgentResult
from ..scraping import CompanyScraper
from .sub_agent import execute_sub_agent
from ..mcp_search import execute_mcp_search
from ..logger import (
    log_phase, log_step, log_llm_call, log_verbose, log_success,
    log_warning, log_metric, Colors, Timer, format_size
)


def should_refine_task(result: SubAgentResult) -> bool:
    """Determine if a sub-agent task needs refinement.

    Args:
        result: Sub-agent result to evaluate

    Returns:
        True if refinement would be helpful
    """
    reflection = result.reflection

    # Refine if marked as incomplete
    if not reflection.is_complete:
        return True

    # Refine if confidence is low or medium
    if reflection.confidence in ["low", "medium"]:
        return True

    # Refine if there are missing aspects identified
    if reflection.missing_aspects and len(reflection.missing_aspects) > 0:
        return True

    return False


def create_refinement_task(
    original_result: SubAgentResult,
    pages_list: List,
    company_name: str,
    original_question: str
) -> SubAgentTask:
    """Create a targeted refinement task based on gaps with MCP search.

    Args:
        original_result: Original sub-agent result with reflection
        pages_list: List of available page content
        company_name: Company being researched
        original_question: Original research question text

    Returns:
        Refined SubAgentTask with focused instructions and MCP snippets
    """
    reflection = original_result.reflection

    # Build gap description
    gap_description = ""
    if reflection.missing_aspects:
        gap_description = f"Missing aspects: {', '.join(reflection.missing_aspects[:3])}"
    if reflection.next_steps:
        gap_description += f"\nSuggested next steps: {reflection.next_steps[:200]}"

    # V2.8: Execute MCP search to find targeted snippets
    log_verbose(f"   Executing MCP search for {original_result.task_id}...")
    targeted_snippets, patterns_used = execute_mcp_search(
        gap_description=gap_description,
        question=original_question
    )

    # Log MCP search results
    if targeted_snippets:
        log_verbose(f"      MCP found {len(targeted_snippets)} chars using patterns: {', '.join(patterns_used)}")
        log_verbose(f"      Snippet size: {format_size(len(targeted_snippets))}")
    else:
        log_verbose(f"      MCP found no targeted snippets (will use full context)")

    # Create targeted refinement task
    refined_task = SubAgentTask(
        task_id=f"{original_result.task_id}_refinement",
        question=original_result.task_id,  # Will be mapped to original question
        context_urls=[p.url for p in pages_list],
        is_refinement=True,
        previous_findings=original_result.findings[:1000] + "...",  # Truncated preview
        gap_to_address=gap_description,
        targeted_snippets=targeted_snippets if targeted_snippets else None,  # V2.8
        search_patterns_used=patterns_used  # V2.8
    )

    return refined_task


def merge_findings(original: str, refined: str) -> str:
    """Merge original and refined findings.

    Args:
        original: Original findings
        refined: Refined findings

    Returns:
        Merged findings text
    """
    return f"""{original}

---
**REFINEMENT ADDENDUM:**

{refined}
"""


def refinement_node(state: ResearchState) -> Dict[str, Any]:
    """Execute refinement with targeted follow-up research.

    This node:
    1. Analyzes sub-agent reflections to identify gaps
    2. Creates targeted follow-up tasks for low-confidence results
    3. Re-runs specific sub-agents with focused prompts
    4. Merges refined findings with original findings
    5. Updates notes and increments refinement counter

    Args:
        state: Current research state

    Returns:
        Dictionary with updated sub_agent_results, notes, and refinement_iteration
    """
    log_phase(2.5, "TARGETED REFINEMENT")

    log_step(f"{Colors.SEARCH} [1/3] Analyzing reflections for gaps...", emoji="")
    log_verbose(f"   Reviewing {len(state.sub_agent_results)} sub-agent results...")

    # Identify tasks that need refinement
    tasks_to_refine = []
    for task_id, result in state.sub_agent_results.items():
        if should_refine_task(result):
            tasks_to_refine.append((task_id, result))
            log_verbose(f"      {task_id}: confidence={result.reflection.confidence}, complete={result.reflection.is_complete}")

    if not tasks_to_refine:
        log_success("All sub-agents report high confidence - skipping refinement", indent=1)
        state.refinement_iteration = 1  # Mark as done
        return {
            "refinement_iteration": 1
        }

    log_success(f"Identified {len(tasks_to_refine)} tasks for refinement", indent=1)

    # Step 2: Create refinement tasks
    log_step(f"\n{Colors.TARGET} [2/3] Creating targeted follow-up tasks...", emoji="")

    pages_list = list(state.pages.values())
    refinement_tasks = []
    original_questions = {}  # Map refinement task_id to original question

    for task_id, original_result in tasks_to_refine:
        # Find original question from brief
        original_question_idx = int(task_id.split('_')[1])  # Extract index from "q_0", "q_1", etc.
        original_question = state.brief.sub_questions[original_question_idx]

        # Create refinement task with MCP search
        ref_task = create_refinement_task(
            original_result,
            pages_list,
            state.brief.company_name,
            original_question  # V2.8: Pass for MCP search
        )
        refinement_tasks.append(ref_task)
        original_questions[ref_task.task_id] = original_question

        # Log task details
        short_gap = ref_task.gap_to_address[:80] + "..." if len(ref_task.gap_to_address) > 80 else ref_task.gap_to_address
        print(f"   {Colors.DIM}Refinement for {task_id}:{Colors.RESET}")
        print(f"      {Colors.DIM}Gap: {short_gap}{Colors.RESET}")
        if ref_task.search_patterns_used:
            print(f"      {Colors.DIM}MCP Patterns: {', '.join(ref_task.search_patterns_used)}{Colors.RESET}")
        if len(ref_task.gap_to_address) > 80:
            log_verbose(f"         Full gap: {ref_task.gap_to_address}")

    # Step 3: Execute refinement tasks in parallel
    log_step(f"\n{Colors.ROBOT} [3/3] Executing {len(refinement_tasks)} refinement tasks in parallel...", emoji="")
    log_verbose(f"   ThreadPoolExecutor configured with max_workers=2 (refinement)")

    refined_results = {}

    with Timer("Refinement Execution") as refinement_timer:
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit refinement tasks
            future_to_task = {
                executor.submit(
                    execute_sub_agent,
                    task,
                    pages_list,
                    state.brief.company_name,
                    original_question=original_questions[task.task_id]
                ): task
                for task in refinement_tasks
            }

            log_verbose(f"   Submitted {len(future_to_task)} refinement tasks")

            # Collect results
            completed_count = 0
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    refined_results[task.task_id] = result
                    completed_count += 1
                    log_verbose(f"   ✓ {completed_count}/{len(refinement_tasks)} complete: {task.task_id}")
                except Exception as e:
                    log_warning(f"Refinement task {task.task_id} failed: {str(e)}", indent=1)

    log_success(f"Completed {len(refined_results)}/{len(refinement_tasks)} refinements in {refinement_timer.elapsed():.1f}s", indent=1)

    # Step 4: Merge refined findings with originals
    print(f"\n   {Colors.WRITE} Merging refined findings with originals...")

    for ref_task_id, refined_result in refined_results.items():
        # Extract original task_id from refinement task_id
        original_task_id = ref_task_id.replace("_refinement", "")

        if original_task_id in state.sub_agent_results:
            original_result = state.sub_agent_results[original_task_id]

            # Merge findings
            merged_findings = merge_findings(
                original_result.findings,
                refined_result.findings
            )

            # Update result with merged findings
            original_result.findings = merged_findings

            # Update reflection (use the more optimistic one)
            if refined_result.reflection.confidence == "high":
                original_result.reflection = refined_result.reflection

            # Update note
            if original_task_id in state.notes:
                state.notes[original_task_id].content = merged_findings

            log_verbose(f"   Merged {ref_task_id} → {original_task_id}")

    # Increment refinement counter
    state.refinement_iteration = 1

    print(f"\n✓ Targeted refinement complete")
    print("="*80 + "\n")

    return {
        "sub_agent_results": state.sub_agent_results,
        "notes": state.notes,
        "refinement_iteration": 1
    }
