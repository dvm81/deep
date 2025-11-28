# System Architecture Diagram - V2.1

## Overview

The Company Private Investing Research Agent is built on a **3-phase LangGraph architecture with Supervisor + Sub-Agents** that orchestrates multiple specialized agents with reflection capabilities to produce comprehensive, high-quality research reports.

**Version History:**
- **V1.0**: Single research agent (linear)
- **V2.0**: Supervisor + Sub-Agents with reflection (parallel)
- **V2.1**: Enhanced date extraction precision

## High-Level Architecture (V2.1)

```mermaid
graph TB
    User[User] -->|config.json| CLI[CLI Entry Point<br/>main.py]
    CLI --> Graph[LangGraph Workflow<br/>agents/graph.py]

    Graph --> Phase1[Phase 1: SCOPE<br/>Planning Agent]
    Graph --> Phase2[Phase 2: RESEARCH<br/>SUPERVISOR<br/>+ Sub-Agents Parallel]
    Graph --> Phase3[Phase 3: WRITE<br/>Writer Agent]

    Phase1 --> Phase2
    Phase2 --> Phase3
    Phase3 --> Output[Markdown Report<br/>447 lines, 49KB]

    Phase2 -.->|spawns| SubAgents[6 Sub-Agents<br/>Running in Parallel]
    SubAgents -.->|Reflection| SelfCritique[Self-Critique<br/>Completeness Check]
    SelfCritique -.->|Results| Phase2

    style Phase1 fill:#e1f5ff
    style Phase2 fill:#fff4e1
    style Phase3 fill:#e8f5e9
    style SubAgents fill:#ffe0b2
    style SelfCritique fill:#f3e5f5
```

## Detailed Component Architecture

```mermaid
graph TB
    subgraph "Input Layer"
        Config[config.json<br/>- company_name<br/>- request<br/>- seed_urls]
        Env[.env<br/>OPENAI_API_KEY]
    end

    subgraph "Core Infrastructure"
        Schema[schema.py<br/>Pydantic Models]
        ConfigPy[config.py<br/>LLM Factory<br/>GPT-4.1, temp=0]
        Scraper[scraping.py<br/>CompanyScraper<br/>HTML→Markdown]
        Storage[storage.py<br/>File I/O Helpers]
    end

    subgraph "Agent Layer"
        Planner[planner.py<br/>Clarifier + Brief Generator]
        Researcher[researcher.py<br/>Content Analysis + Citation]
        Writer[writer.py<br/>Report Generation]
        GraphPy[graph.py<br/>LangGraph Orchestration]
    end

    subgraph "State Management"
        ResearchState[ResearchState<br/>- brief<br/>- pages<br/>- notes<br/>- report_markdown]
    end

    subgraph "Output Layer"
        Pages[artifacts/pages/<br/>*.json]
        Notes[artifacts/notes.json]
        Report[artifacts/<company>_report.md]
        State[artifacts/state.json]
    end

    Config --> Planner
    Env --> ConfigPy
    ConfigPy --> Planner
    ConfigPy --> Researcher
    ConfigPy --> Writer

    Schema --> ResearchState
    ResearchState --> GraphPy

    GraphPy --> Planner
    GraphPy --> Researcher
    GraphPy --> Writer

    Planner --> ResearchState
    Researcher --> Scraper
    Scraper --> ResearchState
    Researcher --> Storage
    Storage --> Pages
    Researcher --> ResearchState
    Writer --> ResearchState
    Writer --> Storage
    Storage --> Report
    Storage --> State
    Storage --> Notes

    style Config fill:#ffebee
    style Env fill:#ffebee
    style ResearchState fill:#fff9c4
    style Report fill:#c8e6c9
```

## Technology Stack

```mermaid
graph LR
    subgraph "AI/LLM Layer"
        GPT[GPT-4.1<br/>OpenAI API]
        LC[LangChain<br/>Prompts & Chains]
        LG[LangGraph<br/>Workflow Engine]
    end

    subgraph "Python Libraries"
        Pydantic[Pydantic<br/>Data Validation]
        Requests[Requests<br/>HTTP Client]
        BS4[BeautifulSoup4<br/>HTML Parsing]
        H2T[html2text<br/>Markdown Conversion]
    end

    subgraph "Data Storage"
        JSON[JSON Files<br/>Structured Data]
        MD[Markdown Files<br/>Reports]
    end

    LC --> GPT
    LG --> LC

    style GPT fill:#4285f4,color:#fff
    style LG fill:#34a853,color:#fff
```

## Module Relationships

```mermaid
classDiagram
    class main {
        +load_config()
        +main()
    }

    class config {
        +get_llm() ChatOpenAI
    }

    class schema {
        +ClarifyWithUser
        +ResearchQuestion
        +ResearchBrief
        +PageContent
        +Note
        +ResearchState
    }

    class scraping {
        +CompanyScraper
        +fetch() PageContent
    }

    class storage {
        +save_page()
        +save_notes()
        +save_report()
        +save_state()
    }

    class planner {
        +planning_node()
        +CLARIFY_PROMPT
        +BRIEF_PROMPT
    }

    class researcher {
        +research_node()
        +build_context()
        +RESEARCH_PROMPT
    }

    class writer {
        +writer_node()
        +WRITER_PROMPT
    }

    class graph {
        +build_graph()
        +planning_wrapper()
        +research_wrapper()
        +writer_wrapper()
    }

    main --> config
    main --> schema
    main --> graph

    graph --> planner
    graph --> researcher
    graph --> writer
    graph --> schema

    planner --> config
    planner --> schema

    researcher --> config
    researcher --> schema
    researcher --> scraping
    researcher --> storage

    writer --> config
    writer --> schema
    writer --> storage

    scraping --> schema
```

## Deployment View

```mermaid
graph TB
    subgraph "Local Environment"
        Python[Python 3.12+<br/>Virtual Env]
        Code[company_research/<br/>Package]
        Artifacts[artifacts/<br/>Output Directory]
    end

    subgraph "External Services"
        OpenAI[OpenAI API<br/>GPT-4.1]
        CompanyWebsite[Company Website<br/>Seed URLs]
    end

    Python --> Code
    Code --> OpenAI
    Code --> CompanyWebsite
    Code --> Artifacts

    style OpenAI fill:#10a37f,color:#fff
    style CompanyWebsite fill:#ff9800,color:#fff
```

## Key Design Patterns

1. **State Management**: Centralized `ResearchState` passed through workflow
2. **Strategy Pattern**: Different agents for different phases
3. **Factory Pattern**: `get_llm()` for LLM instantiation
4. **Data Models**: Pydantic for validation and serialization
5. **Chain of Responsibility**: LangGraph linear workflow
6. **Repository Pattern**: Storage layer abstracts file I/O

## Scalability Considerations

- **Modular agents**: Easy to add new research types
- **Configurable URLs**: Works for any company
- **LLM abstraction**: Easy to swap models
- **Storage abstraction**: Can switch to databases
- **Graph workflow**: Can add parallel processing

## Security Features

- **Domain validation**: Only scrapes allowed domains
- **Environment variables**: API keys in `.env`
- **No external knowledge**: Scoped to provided URLs
- **Citation tracking**: Transparency in data sources
