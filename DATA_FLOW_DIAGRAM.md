# Data Flow Diagram

## Overview

This document illustrates how data flows through the Company Private Investing Research Agent system, from configuration input to final report generation.

## Complete System Data Flow

```mermaid
flowchart TD
    Start([User runs CLI]) --> LoadConfig[Load config.json]
    LoadConfig --> ParseConfig{Parse Configuration}

    ParseConfig --> ExtractData[Extract:<br/>- company_name<br/>- request<br/>- seed_urls]
    ExtractData --> ComputeDomains[Compute allowed_domains<br/>from seed URLs]
    ComputeDomains --> CreateBrief[Create ResearchBrief]
    CreateBrief --> InitState[Initialize ResearchState]

    InitState --> BuildGraph[Build LangGraph Workflow]
    BuildGraph --> Phase1[PHASE 1: SCOPE]

    subgraph Phase1 [" PHASE 1: SCOPE "]
        P1Start[Receive: ResearchState] --> Clarify[Clarifier Agent<br/>GPT-4.1 call]
        Clarify --> GenBrief[Brief Generator<br/>GPT-4.1 call]
        GenBrief --> GenSub[Generate Sub-Questions<br/>6 research questions]
        GenSub --> UpdateBrief[Update ResearchBrief<br/>in state]
        UpdateBrief --> P1End[Return: Updated State]
    end

    Phase1 --> Phase2[PHASE 2: RESEARCH]

    subgraph Phase2 [" PHASE 2: RESEARCH "]
        P2Start[Receive: ResearchState] --> FetchLoop{For each seed URL}
        FetchLoop --> Validate[Validate domain]
        Validate --> HTTPReq[HTTP GET request<br/>with User-Agent]
        HTTPReq --> ParseHTML[Parse HTML<br/>BeautifulSoup]
        ParseHTML --> ConvertMD[Convert to Markdown<br/>html2text]
        ConvertMD --> CreatePage[Create PageContent]
        CreatePage --> SavePage[Save to artifacts/pages/]
        SavePage --> AddToState[Add to state.pages]
        AddToState --> FetchLoop

        FetchLoop --> BuildContext[Build context from<br/>all pages markdown]
        BuildContext --> SubQLoop{For each sub-question}
        SubQLoop --> ResearchAgent[Research Agent<br/>GPT-4.1 call<br/>Current date context]
        ResearchAgent --> ExtractInfo[Extract:<br/>- Names + titles<br/>- Companies<br/>- Funds<br/>- Dates<br/>- Citations]
        ExtractInfo --> CreateNote[Create Note<br/>with citations]
        CreateNote --> AddNote[Add to state.notes]
        AddNote --> SubQLoop

        SubQLoop --> SaveNotes[Save all notes<br/>to artifacts/notes.json]
        SaveNotes --> P2End[Return: Updated State]
    end

    Phase2 --> Phase3[PHASE 3: WRITE]

    subgraph Phase3 [" PHASE 3: WRITE "]
        P3Start[Receive: ResearchState] --> CompileNotes[Compile all research<br/>notes into text]
        CompileNotes --> WriterAgent[Writer Agent<br/>GPT-4.1 call<br/>Current date context]
        WriterAgent --> GenReport[Generate sections:<br/>1. Executive Summary<br/>2. Overview<br/>3. Decision Makers<br/>4. Regions/Sectors<br/>5. AUM/Metrics<br/>6. Portfolio Table<br/>7. Strategies<br/>8. News Table<br/>9. Conclusion<br/>10. Sources]
        GenReport --> FormatMD[Format as markdown<br/>with tables + citations]
        FormatMD --> AddToState2[Add to state.report_markdown]
        AddToState2 --> SaveReport[Save to artifacts/<br/>company_report.md]
        SaveReport --> P3End[Return: Final State]
    end

    Phase3 --> SaveState[Save complete state<br/>to artifacts/state.json]
    SaveState --> End([Report Complete])

    style Phase1 fill:#e1f5ff
    style Phase2 fill:#fff4e1
    style Phase3 fill:#e8f5e9
    style End fill:#c8e6c9
```

## Detailed Data Transformations

### 1. Configuration → ResearchBrief

```mermaid
flowchart LR
    subgraph Input
        CName[company_name:<br/>"Wellington Management"]
        CReq[request:<br/>"Create report on..."]
        CUrls[seed_urls:<br/>Array of URLs]
    end

    subgraph Processing
        Parse[Parse URLs]
        Extract[Extract domains]
        Create[Create constraints]
    end

    subgraph Output
        RB[ResearchBrief:<br/>- company_name<br/>- main_question<br/>- sub_questions: []<br/>- seed_urls<br/>- allowed_domains<br/>- constraints]
    end

    CName --> RB
    CReq --> RB
    CUrls --> Parse
    Parse --> Extract
    Extract --> Create
    Create --> RB
```

### 2. URL → PageContent

```mermaid
flowchart TD
    URL[URL String] --> Validate{Domain<br/>allowed?}
    Validate -->|No| Error[Raise ValueError]
    Validate -->|Yes| Fetch[HTTP GET]
    Fetch --> HTML[Raw HTML String]
    HTML --> Parse[BeautifulSoup<br/>Parse]
    Parse --> Clean[Remove:<br/>- scripts<br/>- styles<br/>- nav<br/>- footer<br/>- header]
    Clean --> Extract[Extract main/article/body]
    Extract --> Convert[html2text<br/>Conversion]
    Convert --> MD[Markdown String<br/>Complete content<br/>No truncation]

    HTML --> ExtractTitle[Extract title]
    ExtractTitle --> Title[Title String]

    URL --> PageURL[url]
    Title --> PageContent
    MD --> PageContent[PageContent:<br/>- url<br/>- title<br/>- text markdown<br/>- raw_html]
    PageURL --> PageContent
```

### 3. Pages → Research Notes

```mermaid
flowchart TD
    Pages[List of PageContent] --> BuildCtx[Build Context String]
    BuildCtx --> Format[Format as:<br/>SOURCE [1]<br/>URL: ...<br/>Title: ...<br/>markdown text]

    Format --> Context[Complete Context<br/>All pages concatenated]
    SubQ[Sub-Question] --> Prompt[Research Prompt]
    Context --> Prompt

    Prompt --> LLM[GPT-4.1 API Call<br/>temp=0]
    LLM --> Response[LLM Response:<br/>- Analysis<br/>- Citations [1][2]<br/>- URL list]

    Response --> Parse[Parse response]
    Parse --> Note[Note:<br/>- question_id<br/>- content with citations<br/>- sources list]

    Note --> StateNotes[state.notes dict<br/>key: question_id<br/>value: Note]
```

### 4. Notes → Final Report

```mermaid
flowchart TD
    Notes[Dictionary of Notes] --> Compile[Compile to text:<br/>### q_0<br/>content...<br/>### q_1<br/>content...]

    Compile --> NotesText[Complete notes text]
    Brief[Research Brief] --> ReportPrompt[Writer Prompt]
    NotesText --> ReportPrompt

    ReportPrompt --> LLM[GPT-4.1 API Call<br/>temp=0<br/>Current date context]
    LLM --> GenSections[Generate 10 sections:<br/>- Headers<br/>- Tables<br/>- Lists<br/>- Citations]

    GenSections --> Report[Markdown Report:<br/>34-56 KB<br/>300-450 lines]
    Report --> Save[Save to file]
    Report --> StateField[state.report_markdown]
```

## State Transitions

```mermaid
stateDiagram-v2
    [*] --> Empty: Initialize
    Empty --> Briefed: Planning adds brief + sub-questions
    Briefed --> Scraped: Research adds pages
    Scraped --> Analyzed: Research adds notes
    Analyzed --> Complete: Writer adds report_markdown
    Complete --> [*]: Save to disk

    note right of Empty
        ResearchState:
        - brief (minimal)
        - pages: {}
        - notes: {}
        - report_markdown: None
    end note

    note right of Briefed
        ResearchState:
        - brief (complete with sub-questions)
        - pages: {}
        - notes: {}
        - report_markdown: None
    end note

    note right of Scraped
        ResearchState:
        - brief
        - pages: {url: PageContent, ...}
        - notes: {}
        - report_markdown: None
    end note

    note right of Analyzed
        ResearchState:
        - brief
        - pages
        - notes: {q_id: Note, ...}
        - report_markdown: None
    end note

    note right of Complete
        ResearchState:
        - brief
        - pages
        - notes
        - report_markdown: "# Report..."
    end note
```

## Data Persistence Flow

```mermaid
flowchart TD
    subgraph "In-Memory State"
        RS[ResearchState<br/>Pydantic Model]
    end

    subgraph "Disk Storage"
        P1[artifacts/pages/<br/>page1.json]
        P2[artifacts/pages/<br/>page2.json]
        PN[artifacts/pages/<br/>pageN.json]

        Notes[artifacts/<br/>notes.json]
        Report[artifacts/<br/>company_report.md]
        State[artifacts/<br/>state.json]
    end

    RS -->|Each page| SavePage[save_page]
    SavePage --> P1
    SavePage --> P2
    SavePage --> PN

    RS -->|All notes| SaveNotes[save_notes]
    SaveNotes --> Notes

    RS -->|Report markdown| SaveReport[save_report]
    SaveReport --> Report

    RS -->|Complete state| SaveState[save_state]
    SaveState --> State

    style RS fill:#fff9c4
```

## API Call Flow

```mermaid
sequenceDiagram
    participant User
    participant Main
    participant Graph
    participant Planner
    participant Researcher
    participant Writer
    participant GPT41 as GPT-4.1 API
    participant Web as Company Website

    User->>Main: python -m company_research.main config.json
    Main->>Graph: invoke({"state": ResearchState})

    Graph->>Planner: planning_node(state)
    Planner->>GPT41: Clarify request (temp=0)
    GPT41-->>Planner: ClarifyWithUser
    Planner->>GPT41: Generate brief (temp=0)
    GPT41-->>Planner: ResearchQuestion
    Planner-->>Graph: Updated state

    Graph->>Researcher: research_node(state)
    loop For each seed URL
        Researcher->>Web: HTTP GET
        Web-->>Researcher: HTML
        Researcher->>Researcher: Convert to markdown
    end

    loop For each sub-question
        Researcher->>GPT41: Research agent (temp=0, date context)
        GPT41-->>Researcher: Research note with citations
    end
    Researcher-->>Graph: Updated state

    Graph->>Writer: writer_node(state)
    Writer->>GPT41: Generate report (temp=0, date context)
    GPT41-->>Writer: Complete markdown report
    Writer-->>Graph: Final state

    Graph-->>Main: Final state
    Main-->>User: Report saved to artifacts/
```

## Error Handling Flow

```mermaid
flowchart TD
    Start[Operation Start] --> Try{Try}
    Try -->|Success| Success[Continue]
    Try -->|HTTP Error| HTTPErr[Log warning<br/>Skip URL<br/>Continue]
    Try -->|Parse Error| ParseErr[Log warning<br/>Skip page<br/>Continue]
    Try -->|Domain Error| DomErr[Raise ValueError<br/>Stop]
    Try -->|LLM Error| LLMErr[Raise Exception<br/>Stop]

    HTTPErr --> CheckPages{Any pages<br/>fetched?}
    ParseErr --> CheckPages
    CheckPages -->|Yes| Continue[Continue with<br/>available pages]
    CheckPages -->|No| Fail[Report generation<br/>may be incomplete]

    style Success fill:#c8e6c9
    style DomErr fill:#ffcdd2
    style LLMErr fill:#ffcdd2
    style Continue fill:#fff9c4
```

## Data Size Evolution

```mermaid
graph LR
    subgraph "Input"
        Config[config.json<br/>~1 KB]
    end

    subgraph "Intermediate"
        HTML[Raw HTML<br/>10 URLs × 100-500 KB<br/>= 1-5 MB]
        Markdown[Markdown Pages<br/>10 URLs × 30-100 KB<br/>= 300 KB - 1 MB]
        Context[Combined Context<br/>300 KB - 1 MB]
    end

    subgraph "Processing"
        Notes[6 Research Notes<br/>~50-200 KB total]
    end

    subgraph "Output"
        Report[Final Report<br/>34-56 KB]
        StateFile[state.json<br/>~4 MB compressed]
    end

    Config --> HTML
    HTML --> Markdown
    Markdown --> Context
    Context --> Notes
    Notes --> Report
    Notes --> StateFile
    Markdown --> StateFile
```

## Citation Tracking Flow

```mermaid
flowchart TD
    Source[Source Page URL] --> Extract[Extract info with citation]
    Extract --> Inline[Add inline citation [1]]
    Inline --> NoteContent[Note content:<br/>"Company has $385M fund [1]"]

    Source --> SourceList[Note sources list:<br/>[url1, url2, ...]]

    NoteContent --> Compile[Compile all notes]
    SourceList --> Compile

    Compile --> Writer[Writer receives notes]
    Writer --> Map[Map citations to URLs]
    Map --> ReportCite[Report inline: [1]]
    Map --> ReportSources[Report Sources section:<br/>[1] url<br/>[2] url]

    ReportCite --> FinalReport[Final Report]
    ReportSources --> FinalReport
```

## Key Data Characteristics

### Data Formats
- **Input**: JSON (config)
- **Intermediate**: Pydantic models (in-memory), HTML, Markdown
- **Output**: Markdown (report), JSON (state, pages, notes)

### Data Volume
- **Configuration**: ~1 KB
- **Scraped HTML**: 1-5 MB total
- **Markdown content**: 300 KB - 1 MB
- **Research notes**: 50-200 KB
- **Final report**: 34-56 KB
- **Complete state**: ~4 MB

### Data Retention
- **Artifacts persisted**: All scraped pages, notes, report, state
- **In-memory only**: LLM responses during processing
- **Reusable**: State can be reloaded for analysis
