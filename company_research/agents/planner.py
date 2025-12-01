"""Planning agent for the Scope phase."""

from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from ..config import get_llm
from ..schema import ClarifyWithUser, ResearchState, ResearchQuestion, AdaptiveQuestions
from ..logger import (
    log_phase, log_step, log_llm_call, log_verbose, log_tree,
    log_success, Colors, Timer
)


# Clarifier model and prompt
clarify_model = get_llm().with_structured_output(ClarifyWithUser)

CLARIFY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an AI research coordinator deciding whether a research request "
        "needs clarification before starting.\n\n"
        "CURRENT DATE: November 27, 2025\n\n"
        "The user wants a deep research report about a specific company.\n"
        "You must:\n"
        "1. Decide if clarification is needed.\n"
        "2. If needed, ask ONE clear question.\n"
        "3. Provide a short confirmation message that research will begin after "
        "the user answers.\n\n"
        "IMPORTANT:\n"
        "- In most cases, if the request clearly specifies company and focus "
        "(e.g., 'COMPANY private markets report'), set need_clarification = false.\n"
        "- Research will be restricted to a set of seed URLs and their domains."
    ),
    ("user", "{request}"),
])


# Research brief model and prompt
research_brief_model = get_llm().with_structured_output(ResearchQuestion)

BRIEF_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a senior research strategist. Your job is to turn a user "
        "request into a single, clear research brief that will guide a "
        "multi-agent deep research system.\n\n"
        "CURRENT DATE: November 27, 2025\n\n"
        "The system will:\n"
        "- Run many scraping / reading steps over the provided URLs\n"
        "- Organize findings\n"
        "- Then write a structured report.\n\n"
        "All research is restricted to the provided seed URLs and any additional "
        "pages on the same domains."
    ),
    (
        "user",
        "Company name: {company_name}\n\n"
        "User request:\n{request}\n\n"
        "Assume any follow-up questions have already been resolved. "
        "Produce a single research_brief that the research system should focus on."
    ),
])


# V2.9: Adaptive questions generator
adaptive_model = get_llm().with_structured_output(AdaptiveQuestions)

ADAPTIVE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a research strategist generating ADAPTIVE sub-questions.\n\n"
        "CURRENT DATE: November 27, 2025\n\n"
        "Context: A research system already has 6 CORE questions covering:\n"
        "1. Key decision makers/leadership\n"
        "2. Regions and sectors\n"
        "3. AUM/metrics\n"
        "4. Strategies/funds\n"
        "5. Portfolio companies\n"
        "6. News/announcements\n\n"
        "Your job: Generate 2-3 ADDITIONAL adaptive questions based on the specific user request.\n\n"
        "Guidelines:\n"
        "- Focus on aspects NOT covered by the 6 core questions\n"
        "- Look for specific keywords in the request (ESG, returns, LP relations, value creation, etc.)\n"
        "- Make questions specific and actionable\n"
        "- Each question should target extraction of concrete details\n"
        "- Keep questions focused on private markets/investing context"
    ),
    (
        "user",
        "Company: {company_name}\n"
        "User Request:\n{request}\n\n"
        "Generate 2-3 adaptive sub-questions that complement the 6 core questions."
    ),
])


def planning_node(state: ResearchState) -> Dict[str, Any]:
    """Execute the planning phase.

    This node:
    1. Checks if clarification is needed (non-interactive in this implementation)
    2. Generates a research brief
    3. Creates sub-questions for the research phase

    Args:
        state: Current research state

    Returns:
        Dictionary with updated brief
    """
    log_phase(1, "PLANNING")

    request = state.brief.main_question

    # Clarification step (non-interactive in this implementation)
    log_step(f"{Colors.THINKING} Checking if clarification needed...", emoji="")
    log_verbose(f"   Request: {request[:200]}...", indent=0)

    with Timer("Clarification check"):
        _clarify = (CLARIFY_PROMPT | clarify_model).invoke({"request": request})

    # Get clarifier prompt for logging
    clarify_prompt_text = CLARIFY_PROMPT.format(request=request)
    log_llm_call(
        purpose="Clarification Decision",
        prompt_preview=clarify_prompt_text,
        response_preview=f"need_clarification: {_clarify.need_clarification}",
        truncate=300
    )

    if _clarify.need_clarification:
        log_verbose(f"   Would ask: {_clarify.question}")
    else:
        log_success("No clarification needed", indent=1)

    # Generate research brief
    log_step(f"\n{Colors.WRITE} Generating research sub-questions...", emoji="")

    with Timer("Brief generation"):
        rq = (BRIEF_PROMPT | research_brief_model).invoke({
            "request": request,
            "company_name": state.brief.company_name,
        })

    # Get brief prompt for logging
    brief_prompt_text = BRIEF_PROMPT.format(
        request=request,
        company_name=state.brief.company_name
    )
    log_llm_call(
        purpose="Research Brief Generation",
        prompt_preview=brief_prompt_text,
        response_preview=rq.research_brief,
        truncate=500
    )

    state.brief.main_question = rq.research_brief

    # Sub-questions – 6 CORE generic private-markets prompts
    core_questions = [
        f"Identify all key decision makers and leadership roles in {state.brief.company_name}'s private investing / private markets activities.",
        f"Describe the regions and sectors in which {state.brief.company_name} is active in private markets.",
        f"Summarize any disclosed assets under management (AUM) or platform-level metrics for {state.brief.company_name}'s private markets business.",
        f"List the private investing strategies, funds, and programs and explain their focus.",
        f"Summarize the portfolio / current firms {state.brief.company_name} is invested in, as disclosed in the scoped URLs.",
        f"Extract EVERY single news item and announcement related to {state.brief.company_name}'s private markets activities. Include ALL fund closures, ALL portfolio company acquisitions/exits, ALL leadership appointments, ALL partnerships, ALL awards/recognitions, ALL press releases, and ALL other news items. Do not summarize - list each news item individually with its date and details.",
    ]

    # V2.9: Generate 2-3 ADAPTIVE questions based on request
    log_step(f"\n{Colors.TARGET} Generating adaptive sub-questions...", emoji="")
    with Timer("Adaptive questions generation"):
        adaptive_result = (ADAPTIVE_PROMPT | adaptive_model).invoke({
            "request": request,
            "company_name": state.brief.company_name,
        })

    adaptive_prompt_text = ADAPTIVE_PROMPT.format(
        request=request,
        company_name=state.brief.company_name
    )
    log_llm_call(
        purpose="Adaptive Questions Generation",
        prompt_preview=adaptive_prompt_text,
        response_preview=f"{len(adaptive_result.questions)} adaptive questions",
        truncate=400
    )

    # Combine: 6 core + 2-3 adaptive = 8-9 total
    state.brief.sub_questions = core_questions + adaptive_result.questions

    # Display all sub-questions
    print(f"\n   {Colors.BOLD}Generated {len(state.brief.sub_questions)} Sub-Questions:{Colors.RESET}")
    print(f"      {Colors.DIM}(6 core + {len(adaptive_result.questions)} adaptive){Colors.RESET}")
    for idx, q in enumerate(state.brief.sub_questions, 1):
        # Mark adaptive questions
        is_adaptive = idx > 6
        marker = f"{Colors.YELLOW}[ADAPTIVE]{Colors.RESET} " if is_adaptive else ""

        # Shorten for display
        short_q = q[:80] + "..." if len(q) > 80 else q
        print(f"      {Colors.DIM}{idx}. {marker}{short_q}{Colors.RESET}")
        # Full question in verbose mode
        if len(q) > 80:
            log_verbose(f"         Full: {q}", indent=0)

    log_success("\nPlanning Complete", indent=0)

    return {"brief": state.brief}
