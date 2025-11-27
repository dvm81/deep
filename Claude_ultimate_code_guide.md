````markdown
# Company Private Investing – Local Deep Research Agent (Python Plan)

## 1. Goal

Build a **local Python deep-research agent** that:

- Scrapes and analyzes **only** a user-provided set of URLs (typically the pages of a single firm such as Wellington, BlackRock, etc.).
- Uses a **3-phase architecture matching LangChain’s `deep_research_from_scratch`**:
  1. **Scope** – Clarify request, generate research brief  
  2. **Research** – Supervisor + sub-agents gather findings  
  3. **Write** – One-shot report generation
- Produces a **professional financial-style markdown report** that (for a generic private markets / private investing brief):

  - Identifies **key decision makers** (names + positions).
  - Describes **regions and sectors** where the firm is active.
  - Extracts **assets under management / platform statistics** if available.
  - Provides **tables** of:
    - Current firms they are invested in (as far as the site reveals).
    - Recent news and announcements relevant to the topic.
  - Describes **funds / strategies / programs**.
  - Uses **citations for every factual statement**, based **only on content from the supplied URLs and (optionally) same-domain pages the agent is allowed to visit.**

The architecture and **prompt roles** should mirror those in  
[`langchain-ai/deep_research_from_scratch`](https://github.com/langchain-ai/deep_research_from_scratch), with domain/scope adapted at runtime from:

- A **company name** (e.g., “Wellington Management”, “BlackRock”).  
- A **user research query**.  
- A **set of seed URLs** that define the allowed content scope.


## 2. Input Specification

### 2.1 Runtime Inputs

The system should accept **runtime configuration**, either via:

- A JSON/YAML config file, or
- CLI arguments/env variables.

Minimum inputs:

```jsonc
{
  "company_name": "Wellington Management",
  "request": "I want to create a report on Wellington Management related to private markets...",
  "seed_urls": [
    "https://www.wellington.com/en/capabilities/private-investing",
    "https://www.wellington.com/en/capabilities/private-investing/our-team",
    "... etc ..."
  ]
}
````

Where:

* `company_name`: used in prompts (“this research is about COMPANY_NAME”).
* `request`: the full natural language research brief from the user.
* `seed_urls`: list of URLs the agent is allowed to scrape (plus, optionally, further URLs on the same domains if we choose to enable limited expansion).

### 2.2 Derived Values

From `seed_urls`, compute:

* `allowed_domains` – e.g., `{urlparse(u).netloc for u in seed_urls}`, so the agent can be restricted to those domains.

### 2.3 Constraints

* **Scope constraint**:

  * The agent must restrict itself to **content reachable from the provided seed URLs on their allowed domains**.
  * It must **not** use arbitrary web search or external knowledge.

* **Knowledge constraint**:

  * No external sources (news sites, databases, prior model knowledge) beyond the scoped URLs/domains.
  * If a requested data point does not appear in the content, the system must say:

    > “Not disclosed on the company’s website within the scoped URLs.”

* **Citation constraint**:

  * Every factual statement in notes and the final report should have a citation.
  * Use inline markers `[1]`, `[2]`, etc., with a **Sources** section mapping numbers to URLs.

## 3. Project Structure

Create a Python package `company_research/` (name flexible) with this layout:

```text
company_research/
  __init__.py
  config.py        # LLM config and constants
  schema.py        # Pydantic models for scope + research state
  scraping.py      # Simple HTTP+BS4 scraper for allowed URLs
  storage.py       # Local file storage helpers (JSON + markdown)
  main.py          # CLI entry point to run the full pipeline

  agents/
    __init__.py
    planner.py     # Scope phase: Clarifier + Brief generation
    researcher.py  # Research phase: supervisor + sub-agent loop (simplified)
    writer.py      # Write phase: final report generation
    graph.py       # LangGraph wiring
```

Also create:

* `PLAN.md` (this file).
* `requirements.txt` or `pyproject.toml`.
* `artifacts/` directory (auto-created) for output JSON/MD files.
* Optionally `config.example.json` showing an example company instantiation (see Section 15).

## 4. Dependencies

Example `requirements.txt`:

```text
langchain>=0.3.0
langgraph>=0.2.0
langchain-openai>=0.2.0
requests>=2.32.0
beautifulsoup4>=4.12.0
pydantic>=2.0.0
python-dotenv>=1.0.0
```

Implementation tasks:

1. Install these dependencies.
2. Use `OPENAI_API_KEY` (or similar) via environment variables for LLM access.

## 5. Core Data Models (`schema.py`)

### 5.1 Scope-phase models (mirroring `deep_research_from_scratch`)

```python
from pydantic import BaseModel, Field

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
```

### 5.2 Research-state models

```python
from typing import List, Dict, Optional
from pydantic import BaseModel, HttpUrl


class ResearchBrief(BaseModel):
    company_name: str
    main_question: str                 # from ResearchQuestion.research_brief
    sub_questions: List[str]
    seed_urls: List[HttpUrl]
    allowed_domains: List[str]
    constraints: List[str]


class PageContent(BaseModel):
    url: HttpUrl
    title: str
    text: str                          # cleaned text
    raw_html: Optional[str] = None     # may be omitted later


class Note(BaseModel):
    question_id: str                   # e.g. "decision_makers"
    content: str                       # LLM-written analysis with citations
    sources: List[HttpUrl]             # URLs used in that note


class ResearchState(BaseModel):
    brief: ResearchBrief
    pages: Dict[str, PageContent] = {} # key = URL string
    notes: Dict[str, Note] = {}        # key = question_id
    report_markdown: Optional[str] = None
```

The **LangGraph state** will carry a `ResearchState` instance through the workflow.

## 6. Scraper Implementation (`scraping.py`)

We intentionally **do not** use Playwright; simple `requests + BeautifulSoup` is sufficient.

### 6.1 Domain Validation

Restrict to the configured `allowed_domains` from the brief.

```python
from dataclasses import dataclass
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from .schema import PageContent, ResearchBrief


@dataclass
class CompanyScraper:
    brief: ResearchBrief
    timeout: int = 20

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.netloc not in self.brief.allowed_domains:
            raise ValueError(f"URL not in allowed domains: {url}")

    def fetch(self, url: str) -> PageContent:
        self._validate_url(url)
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()

        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        title = (soup.title.string or "").strip() if soup.title else ""
        main = soup.find("main") or soup.body or soup
        text = main.get_text("\n", strip=True)

        return PageContent(url=url, title=title, text=text, raw_html=html)
```

### 6.2 Future Special Parsers (optional)

Later, add parser helpers such as:

* `parse_team(page)` → list of `{name, role, location}`.
* `parse_strategies(page)` → list of `{strategy_name, stage, sectors}`.
* `parse_news(page)` → list of `{date, headline, summary, url}`.
* `parse_investments(page)` → list of portfolio companies.

These are optional enhancements feeding structured data into the writer.

## 7. Storage Helpers (`storage.py`)

Same as before, but now company-agnostic.

```python
import json
from pathlib import Path
from typing import Dict
from .schema import PageContent, Note, ResearchState

BASE_DIR = Path("artifacts")


def save_page(page: PageContent) -> None:
    url_slug = page.url.replace("https://", "").replace("http://", "").replace("/", "_").replace("#", "_")
    out = BASE_DIR / "pages" / f"{url_slug}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page.model_dump_json(indent=2), encoding="utf-8")


def save_notes(notes: Dict[str, Note]) -> None:
    out = BASE_DIR / "notes.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {k: v.model_dump() for k, v in notes.items()}
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_report(report_md: str, company_name: str) -> Path:
    safe_name = company_name.lower().replace(" ", "_")
    out = BASE_DIR / f"{safe_name}_private_investing_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report_md, encoding="utf-8")
    return out


def save_state(state: ResearchState) -> None:
    out = BASE_DIR / "state.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(state.model_dump_json(indent=2), encoding="utf-8")
```

## 8. LLM Configuration (`config.py`)

Model factory:

```python
import os
from langchain_openai import ChatOpenAI  # or another provider


def get_llm():
    # Assumes OPENAI_API_KEY is set in environment
    return ChatOpenAI(
        model="gpt-4.1-mini",   # can be upgraded to stronger model
        temperature=0.2,
    )
```

## 9. Scope Phase Prompts (`agents/planner.py`)

The Scope phase mirrors the repo:

1. **Clarifier** (`ClarifyWithUser`)
2. **Research brief generator** (`ResearchQuestion`)
3. (Optionally) a sub-question decomposition step.

### 9.1 Clarifier (User Clarification)

```python
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from ..config import get_llm
from ..schema import ClarifyWithUser, ResearchState, ResearchQuestion, ResearchBrief


clarify_model = get_llm().with_structured_output(ClarifyWithUser)

CLARIFY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an AI research coordinator deciding whether a research request "
        "needs clarification before starting.\n\n"
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

research_brief_model = get_llm().with_structured_output(ResearchQuestion)

BRIEF_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a senior research strategist. Your job is to turn a user "
        "request into a single, clear research brief that will guide a "
        "multi-agent deep research system.\n\n"
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
```

### 9.2 Planning node

```python
def planning_node(state: ResearchState) -> Dict[str, Any]:
    request = state.brief.main_question

    # Clarification step (non-interactive in this implementation)
    _clarify = clarify_model.invoke({"request": request})

    # Generate research brief
    rq = research_brief_model.invoke({
        "request": request,
        "company_name": state.brief.company_name,
    })

    state.brief.main_question = rq.research_brief

    # Sub-questions – can be generic private-markets prompts
    state.brief.sub_questions = [
        f"Identify all key decision makers and leadership roles in {state.brief.company_name}'s private investing / private markets activities.",
        f"Describe the regions and sectors in which {state.brief.company_name} is active in private markets.",
        f"Summarize any disclosed assets under management (AUM) or platform-level metrics for {state.brief.company_name}'s private markets business.",
        f"List the private investing strategies, funds, and programs and explain their focus.",
        f"Summarize the portfolio / current firms {state.brief.company_name} is invested in, as disclosed in the scoped URLs.",
        f"Summarize recent news and announcements related to {state.brief.company_name}'s private markets activities.",
    ]

    return {"brief": state.brief}
```

## 10. Research Phase (`agents/researcher.py`)

The **research phase** mirrors the repo’s **research sub-agents** + **compression** but simplified to one agent over the pre-fetched pages.

### 10.1 Research agent prompts (ReAct-style, scoped to URLs)

```python
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from ..config import get_llm
from ..schema import ResearchState, Note
from ..scraping import CompanyScraper
from ..storage import save_page


RESEARCH_AGENT_SYSTEM = """
You are a research agent in a multi-agent deep research system.

Your job:
- Answer a specific sub-question of a larger research request about a company.
- Use only the provided web pages and any additional pages you conceptually
  fetch from the allowed seed URL domains.
- Work step by step, thinking carefully about what to read next.
- Track which URLs support each part of your answer.

TOOLS:
- You conceptually have tools that fetch and summarize pages from the seed URL
  domains. In this implementation, all seed URLs are fetched up front.

BEHAVIOR GUIDELINES:
- Plan what information you need before reading.
- When reading content, focus on details relevant to your sub-question.
- If information is missing from the website, explicitly say it is not
  disclosed.
- Always provide inline citations like [1], [2] linked to URLs at the end.
"""

RESEARCH_AGENT_HUMAN = """
Sub-question you must answer:

{question}

Company: {company_name}

Existing notes on this topic (if any):
{existing_notes}

Available context excerpts from seed URLs:
{context}

Instructions:
1. Decide what you still need to know to answer the sub-question.
2. Use the provided context (seed URL content).
3. Write a focused research note (3–8 paragraphs) that:
   - Answers the sub-question as completely as possible
   - Uses only information from the scoped URLs
   - Includes inline citations like [1], [2] after claims
4. At the end, list the URLs you used as:
   [1] <url>
   [2] <url>
   ...

If the website does not provide enough detail to fully answer the question,
say so clearly.
"""

RESEARCH_PROMPT = ChatPromptTemplate.from_messages([
    ("system", RESEARCH_AGENT_SYSTEM),
    ("user", RESEARCH_AGENT_HUMAN),
])
```

### 10.2 Context builder and research node

```python
def build_context(pages: List) -> str:
    chunks = []
    for i, p in enumerate(pages, start=1):
        chunks.append(f"[{i}] {p.url}\n{p.text[:4000]}")
    return "\n\n".join(chunks)


def research_node(state: ResearchState) -> Dict[str, Any]:
    llm = get_llm()
    scraper = CompanyScraper(brief=state.brief)

    # 1) Fetch all seed URLs
    for url in state.brief.seed_urls:
        url_str = str(url)
        if url_str not in state.pages:
            page = scraper.fetch(url_str)
            state.pages[url_str] = page
            save_page(page)

    pages_list = list(state.pages.values())
    context = build_context(pages_list)
    notes = state.notes.copy()

    # 2) For each sub-question, write a research note
    for idx, q in enumerate(state.brief.sub_questions):
        q_id = f"q_{idx}"
        if q_id in notes:
            continue

        existing_notes = ""  # can aggregate related notes if needed

        resp = (RESEARCH_PROMPT | llm).invoke({
            "question": q,
            "company_name": state.brief.company_name,
            "existing_notes": existing_notes,
            "context": context,
        })

        content = resp.content
        sources = [p.url for p in pages_list]  # simple initial heuristic

        notes[q_id] = Note(
            question_id=q_id,
            content=content,
            sources=sources,
        )

    state.notes = notes
    return {"notes": state.notes, "pages": state.pages}
```

### 10.3 Optional compression node

Add a compression step similar to the repo’s `compress_research` pattern, with system & human prompts that:

* Take multiple raw notes.
* Output a shorter, consolidated note, preserving citations and website-only constraint.

This can be implemented later and inserted between `research` and `write` in the graph.

## 11. Write Phase Prompts (`agents/writer.py`)

Final writer mirrors `deep_research_from_scratch`’s **one-shot report**.

```python
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from ..config import get_llm
from ..schema import ResearchState
from ..storage import save_report

FINAL_REPORT_SYSTEM = """
You are a professional financial analyst and report writer.

You will receive:
- A research brief that defines the question to answer
- Edited research notes that summarize findings from web research

Your job is to write a clear, structured markdown report that fully answers
the research brief.

IMPORTANT CONSTRAINTS:
- Use ONLY the information in the provided notes.
- Do NOT add outside knowledge or speculate.
- Every factual claim must be supported by a citation like [1], [2], etc.
- If the notes do not contain enough information for a specific detail,
  say 'not disclosed on the company's website within the scoped URLs.'
"""

FINAL_REPORT_HUMAN = """
Company: {company_name}

Research brief:
{brief}

Edited research notes:
{notes}

Write a markdown report with the following sections:

1. Executive summary
2. Private investing / private markets overview
3. Key decision makers
4. Regions and sectors
5. Assets under management and platform metrics
6. Portfolio companies or deal examples (include at least one markdown table)
7. Strategies / funds / programs
8. Recent news & announcements (markdown table)
9. Conclusion

Requirements:
- Use inline citations like [1], [2] after claims.
- At the end of the report, include a 'Sources' section that maps each
  citation number to a URL.
- Write in a professional financial / institutional investor tone.
"""

WRITER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", FINAL_REPORT_SYSTEM),
    ("user", FINAL_REPORT_HUMAN),
])


def writer_node(state: ResearchState) -> Dict[str, Any]:
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
```

## 12. LangGraph Wiring (`agents/graph.py`)

Linear graph:

`plan -> research -> write -> END`

(Compression can be inserted later.)

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END
from ..schema import ResearchState
from .planner import planning_node
from .researcher import research_node
from .writer import writer_node


class GraphState(TypedDict):
    state: ResearchState


def planning_wrapper(state: ResearchState) -> ResearchState:
    updates = planning_node(state)
    for k, v in updates.items():
        setattr(state, k, v)
    return state


def research_wrapper(state: ResearchState) -> ResearchState:
    updates = research_node(state)
    for k, v in updates.items():
        setattr(state, k, v)
    return state


def writer_wrapper(state: ResearchState) -> ResearchState:
    updates = writer_node(state)
    for k, v in updates.items():
        setattr(state, k, v)
    return state


def build_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("plan", lambda s: {"state": planning_wrapper(s["state"])})
    workflow.add_node("research", lambda s: {"state": research_wrapper(s["state"])})
    workflow.add_node("write", lambda s: {"state": writer_wrapper(s["state"])})

    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "research")
    workflow.add_edge("research", "write")
    workflow.add_edge("write", END)

    app = workflow.compile()
    return app
```

## 13. Main Entry Point (`main.py`)

`main.py` reads config (company name, request, seed URLs), constructs the `ResearchBrief`, and runs the graph.

```python
import json
from pathlib import Path
from urllib.parse import urlparse
from typing import List
from pydantic import HttpUrl

from company_research.schema import ResearchBrief, ResearchState
from company_research.agents.graph import build_graph
from company_research.storage import save_state


def load_config(path: str = "config.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(config_path: str = "config.json"):
    cfg = load_config(config_path)

    company_name: str = cfg["company_name"]
    request: str = cfg["request"]
    seed_urls: List[HttpUrl] = cfg["seed_urls"]

    allowed_domains = sorted({urlparse(u).netloc for u in seed_urls})

    brief = ResearchBrief(
        company_name=company_name,
        main_question=request.strip(),
        sub_questions=[],  # filled by planning_node
        seed_urls=seed_urls,
        allowed_domains=allowed_domains,
        constraints=[
            "Only use content from the scoped URLs and their domains.",
            "Use citations for every factual statement.",
        ],
    )

    state = ResearchState(brief=brief)
    app = build_graph()

    final_state = app.invoke({"state": state})
    final_research_state: ResearchState = final_state["state"]

    save_state(final_research_state)
    print(
        f"Done. Report written to artifacts/{company_name.lower().replace(' ', '_')}_private_investing_report.md"
    )


if __name__ == "__main__":
    main()
```

## 14. Implementation Steps for a Coding Agent

1. Create the repo skeleton matching **Section 3**.
2. Add `requirements.txt` and install dependencies.
3. Implement `schema.py`, `scraping.py`, `storage.py`, `config.py`.
4. Implement Scope logic in `agents/planner.py` using `ClarifyWithUser` and `ResearchQuestion` prompts as in Section 9.
5. Implement Research logic in `agents/researcher.py` using the ReAct-style prompts in Section 10.
6. Implement Writer logic in `agents/writer.py` as in Section 11.
7. Implement LangGraph wiring in `agents/graph.py`.
8. Implement `main.py` that reads `config.json` and runs the graph.
9. Test with a **Wellington configuration** (Section 15).
10. Reuse the same code for other firms (e.g., BlackRock) by changing `company_name`, `request`, and `seed_urls` in the config file.

## 15. Example Instantiation: Wellington Private Investing

Example `config.wellington.json`:

```json
{
  "company_name": "Wellington Management",
  "request": "I want to create a report on Wellington Management related to private markets. The research should focus on analyzing who are the key decision makers (full list, names and positions), what regions and sectors the company is active in, the assets under management, a tabular list of current firms they are invested in (what they acquired), what are the funds/strategies, and all recent news and announcements in tabular form. Please use ONLY information from their website and no outside knowledge. Use citations for everything you write. The study should result in a well-supported professional financial report.",
  "seed_urls": [
    "https://www.wellington.com/en/capabilities/private-investing",
    "https://www.wellington.com/en/capabilities/private-investing/our-team",
    "https://www.wellington.com/en/capabilities/private-investing/early-stage-venture",
    "https://www.wellington.com/en/capabilities/private-investing/climate-growth",
    "https://www.wellington.com/en/capabilities/private-investing/late-stage-biotechnology#accordion-e6d946989a-item-d2db1cee14",
    "https://www.wellington.com/en/capabilities/private-investing/late-stage-biotechnology/case-study",
    "https://www.wellington.com/en/capabilities/private-investing/late-stage-growth",
    "https://www.wellington.com/en/capabilities/private-investing/late-stage-growth/case-study",
    "https://www.wellington.com/en/capabilities/private-investing/private-credit",
    "https://www.wellington.com/en/capabilities/private-investing/value-creation"
  ]
}
```

To run:

```bash
python -m company_research.main config.wellington.json
```

To target another private markets firm (e.g., BlackRock), create a similar config with:

* `"company_name": "BlackRock"`
* A BlackRock-specific `"request"`
* BlackRock private markets / alternatives URLs under `"seed_urls"`.

The **same agent** and architecture apply; only the config changes.

---

```
::contentReference[oaicite:0]{index=0}
```
