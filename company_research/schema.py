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


# V2.0: Supervisor + Sub-Agent models
class Reflection(BaseModel):
    """Self-critique and reflection from a sub-agent."""
    is_complete: bool = Field(
        description="Whether the research for this question is complete and thorough"
    )
    missing_aspects: List[str] = Field(
        description="List of aspects that might be missing or need more detail",
        default_factory=list
    )
    confidence: str = Field(
        description="Confidence level in the findings: high, medium, or low"
    )
    next_steps: Optional[str] = Field(
        description="What should be done next to improve the findings, if anything",
        default=None
    )


class SubAgentTask(BaseModel):
    """Task assignment for a sub-agent."""
    task_id: str                       # e.g. "decision_makers"
    question: str                      # The specific research question
    context_urls: List[HttpUrl]        # URLs this agent should focus on


class SubAgentResult(BaseModel):
    """Result from a sub-agent's research."""
    task_id: str
    findings: str                      # Detailed findings with citations
    reflection: Reflection             # Self-critique
    sources: List[HttpUrl]             # URLs used


class SupervisorReview(BaseModel):
    """Supervisor's review of all sub-agent findings."""
    overall_completeness: str = Field(
        description="Assessment of overall research completeness"
    )
    gaps_identified: List[str] = Field(
        description="Any gaps or missing information across all findings",
        default_factory=list
    )
    refinement_needed: bool = Field(
        description="Whether refinement iteration is needed",
        default=False
    )
    ready_for_writing: bool = Field(
        description="Whether findings are ready for report generation"
    )


class ResearchState(BaseModel):
    """Overall state of the research workflow."""
    brief: ResearchBrief
    pages: Dict[str, PageContent] = {} # key = URL string
    notes: Dict[str, Note] = {}        # key = question_id

    # V2.0: Supervisor coordination
    sub_agent_results: Dict[str, SubAgentResult] = {}  # key = task_id
    supervisor_review: Optional[SupervisorReview] = None

    report_markdown: Optional[str] = None
    report_json: Optional[Dict] = None


# Structured JSON Report Models
class KeyDecisionMaker(BaseModel):
    """Individual decision maker/leader."""
    name: str
    title: str
    location: Optional[str] = None


class PortfolioCompany(BaseModel):
    """Portfolio company information."""
    name: str
    sector: str
    stage: str  # e.g., "Unrealized", "Exited", "Public"
    details: Optional[str] = None


class Strategy(BaseModel):
    """Investment strategy/fund/program."""
    name: str
    description: str
    focus: Optional[str] = None


class NewsAnnouncement(BaseModel):
    """News or announcement item."""
    date: str
    headline: str
    description: str


class RegionsAndSectors(BaseModel):
    """Regions and sectors structure."""
    regions: List[str] = Field(default_factory=list)
    sectors: List[str] = Field(default_factory=list)


class AUMMetrics(BaseModel):
    """Assets under management metrics."""
    total_aum: Optional[str] = None
    details: Optional[str] = None


class StructuredReport(BaseModel):
    """Structured JSON format of the research report."""
    company_name: str
    report_date: str
    executive_summary: str
    overview: str
    key_decision_makers: List[KeyDecisionMaker]
    regions_and_sectors: RegionsAndSectors
    aum_metrics: AUMMetrics
    portfolio_companies: List[PortfolioCompany]
    strategies: List[Strategy]
    news_announcements: List[NewsAnnouncement]
    conclusion: str
    sources: List[str]
