"""Planning agent for the Scope phase."""

from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from ..config import get_llm
from ..schema import ClarifyWithUser, ResearchState, ResearchQuestion


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
    request = state.brief.main_question

    # Clarification step (non-interactive in this implementation)
    _clarify = (CLARIFY_PROMPT | clarify_model).invoke({"request": request})

    # Generate research brief
    rq = (BRIEF_PROMPT | research_brief_model).invoke({
        "request": request,
        "company_name": state.brief.company_name,
    })

    state.brief.main_question = rq.research_brief

    # Sub-questions – generic private-markets prompts
    state.brief.sub_questions = [
        f"Identify all key decision makers and leadership roles in {state.brief.company_name}'s private investing / private markets activities.",
        f"Describe the regions and sectors in which {state.brief.company_name} is active in private markets.",
        f"Summarize any disclosed assets under management (AUM) or platform-level metrics for {state.brief.company_name}'s private markets business.",
        f"List the private investing strategies, funds, and programs and explain their focus.",
        f"Summarize the portfolio / current firms {state.brief.company_name} is invested in, as disclosed in the scoped URLs.",
        f"Summarize recent news and announcements related to {state.brief.company_name}'s private markets activities.",
    ]

    return {"brief": state.brief}
