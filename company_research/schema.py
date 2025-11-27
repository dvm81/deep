"""Pydantic models for the research system."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field, HttpUrl


# Scope-phase models (mirroring deep_research_from_scratch)
class ClarifyWithUser(BaseModel):
    """Decision + question for user clarification."""
    need_clarification: bool = Field(
        description="Whether the agent must ask the user a clarifying question "
                    "before starting the research."
    )
    question: str = Field(
        description="If clarification is needed, the question to ask the user "
                    "to better scope the research."
    )
    verification: str = Field(
        description="A confirmation message telling the user research will start "
                    "after they answer the clarification question."
    )


class ResearchQuestion(BaseModel):
    """Research question and brief for guiding research."""
    research_brief: str = Field(
        description="A single, clear research question/brief that will guide the research."
    )


# Research-state models
class ResearchBrief(BaseModel):
    """Configuration and scope for the research project."""
    company_name: str
    main_question: str                 # from ResearchQuestion.research_brief
    sub_questions: List[str]
    seed_urls: List[HttpUrl]
    allowed_domains: List[str]
    constraints: List[str]


class PageContent(BaseModel):
    """Content from a scraped web page."""
    url: HttpUrl
    title: str
    text: str                          # cleaned text
    raw_html: Optional[str] = None     # may be omitted later


class Note(BaseModel):
    """Research note for a specific sub-question."""
    question_id: str                   # e.g. "decision_makers"
    content: str                       # LLM-written analysis with citations
    sources: List[HttpUrl]             # URLs used in that note


class ResearchState(BaseModel):
    """Overall state of the research workflow."""
    brief: ResearchBrief
    pages: Dict[str, PageContent] = {} # key = URL string
    notes: Dict[str, Note] = {}        # key = question_id
    report_markdown: Optional[str] = None
