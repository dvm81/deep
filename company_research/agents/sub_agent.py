"""Sub-agent for specialized research with reflection capabilities."""

from typing import List
from langchain_core.prompts import ChatPromptTemplate
from ..config import get_llm
from ..schema import SubAgentTask, SubAgentResult, Reflection, PageContent


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

DATE EXTRACTION:
- For news/announcements: Extract EXACT dates (e.g., "October 15, 2025", "Q4 2025")
- Look for date patterns in timestamps, publication dates, announcement dates
- Never write "Not Disclosed" if any date information exists

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
3. Organize findings clearly (use bullet points, lists, sections)
4. Include inline citation [1], [2] after EVERY fact
5. At the end, list the URLs you cited

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
