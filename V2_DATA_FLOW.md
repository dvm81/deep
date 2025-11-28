# V2.0 Data Flow with Supervisor + Sub-Agents

## Complete V2.0 Research Phase Data Flow

```mermaid
flowchart TD
    Start([Supervisor Node Starts]) --> Fetch[Step 1: Fetch Seed URLs<br/>10 URLs → Markdown]

    Fetch --> Pages[state.pages<br/>Dict URL: PageContent]

    Pages --> CreateTasks[Step 2: Create Sub-Agent Tasks<br/>6 tasks from sub_questions]

    subgraph "Tasks Created"
        T0[Task 0: Decision Makers]
        T1[Task 1: Regions/Sectors]
        T2[Task 2: AUM/Metrics]
        T3[Task 3: Strategies]
        T4[Task 4: Portfolio]
        T5[Task 5: News]
    end

    CreateTasks --> T0
    CreateTasks --> T1
    CreateTasks --> T2
    CreateTasks --> T3
    CreateTasks --> T4
    CreateTasks --> T5

    subgraph "Step 3: Parallel Execution (ThreadPool)"
        T0 --> SA0[Sub-Agent 0<br/>execute_sub_agent]
        T1 --> SA1[Sub-Agent 1<br/>execute_sub_agent]
        T2 --> SA2[Sub-Agent 2<br/>execute_sub_agent]
        T3 --> SA3[Sub-Agent 3<br/>execute_sub_agent]
        T4 --> SA4[Sub-Agent 4<br/>execute_sub_agent]
        T5 --> SA5[Sub-Agent 5<br/>execute_sub_agent]

        SA0 --> R0[Reflection 0]
        SA1 --> R1[Reflection 1]
        SA2 --> R2[Reflection 2]
        SA3 --> R3[Reflection 3]
        SA4 --> R4[Reflection 4]
        SA5 --> R5[Reflection 5]

        R0 --> RES0[SubAgentResult 0]
        R1 --> RES1[SubAgentResult 1]
        R2 --> RES2[SubAgentResult 2]
        R3 --> RES3[SubAgentResult 3]
        R4 --> RES4[SubAgentResult 4]
        R5 --> RES5[SubAgentResult 5]
    end

    RES0 --> Collect[Step 4: Collect All Results<br/>state.sub_agent_results]
    RES1 --> Collect
    RES2 --> Collect
    RES3 --> Collect
    RES4 --> Collect
    RES5 --> Collect

    Collect --> Review[Supervisor Review<br/>GPT-4.1 Analysis]

    Review --> SuperRev[state.supervisor_review<br/>SupervisorReview object]

    SuperRev --> Convert[Convert to Notes<br/>state.notes]

    Convert --> End([Return Updated State])

    style Start fill:#e1f5ff
    style Fetch fill:#fff9c4
    style SA0 fill:#ffe0b2
    style SA1 fill:#ffe0b2
    style SA2 fill:#ffe0b2
    style SA3 fill:#ffe0b2
    style SA4 fill:#ffe0b2
    style SA5 fill:#ffe0b2
    style R0 fill:#f3e5f5
    style R1 fill:#f3e5f5
    style R2 fill:#f3e5f5
    style R3 fill:#f3e5f5
    style R4 fill:#f3e5f5
    style R5 fill:#f3e5f5
    style Review fill:#c5cae9
    style End fill:#c8e6c9
```

## Sub-Agent Internal Data Flow

```mermaid
flowchart TD
    Input[SubAgentTask<br/>- task_id<br/>- question<br/>- context_urls]

    BuildCtx[build_context<br/>Combine all PageContent]

    Context[Complete Context String<br/>No truncation]

    Prompt1[SUB_AGENT_PROMPT<br/>System + Human]

    Variables{Prompt Variables}
    V1[question]
    V2[company_name]
    V3[context]

    LLM1[GPT-4.1 API Call<br/>temperature=0]

    Findings[LLM Response<br/>Findings with citations]

    PromptRef[REFLECTION_PROMPT<br/>System + Human]

    VarsRef{Reflection Variables}
    VR1[question]
    VR2[findings]
    VR3[context_sample 2000 chars]

    LLM2[GPT-4.1 API Call<br/>with_structured_output<br/>Reflection]

    ReflectionOut[Reflection Object<br/>- is_complete<br/>- missing_aspects<br/>- confidence<br/>- next_steps]

    Result[SubAgentResult<br/>- task_id<br/>- findings<br/>- reflection<br/>- sources]

    Input --> BuildCtx
    BuildCtx --> Context

    Context --> Prompt1
    Prompt1 --> Variables
    Variables --> V1
    Variables --> V2
    Variables --> V3

    V1 --> LLM1
    V2 --> LLM1
    V3 --> LLM1

    LLM1 --> Findings

    Findings --> PromptRef
    PromptRef --> VarsRef
    VarsRef --> VR1
    VarsRef --> VR2
    VarsRef --> VR3

    VR1 --> LLM2
    VR2 --> LLM2
    VR3 --> LLM2

    LLM2 --> ReflectionOut

    Findings --> Result
    ReflectionOut --> Result
    Context --> Result

    style Input fill:#e1f5ff
    style LLM1 fill:#4285f4,color:#fff
    style LLM2 fill:#4285f4,color:#fff
    style ReflectionOut fill:#f3e5f5
    style Result fill:#c8e6c9
```

## State Evolution Through V2.0 Research Phase

```mermaid
stateDiagram-v2
    [*] --> StateIn: Supervisor receives

    state StateIn {
        [*] --> brief
        [*] --> pages_empty
        [*] --> notes_empty
        [*] --> sub_results_empty
        [*] --> review_none
    }

    StateIn --> Fetching: Fetch URLs

    state Fetching {
        [*] --> scrape_url1
        [*] --> scrape_url2
        [*] --> scrape_urlN
        scrape_url1 --> pages_dict
        scrape_url2 --> pages_dict
        scrape_urlN --> pages_dict
    }

    Fetching --> TaskCreation: Create tasks

    state TaskCreation {
        [*] --> task0
        [*] --> task1
        [*] --> task2
        [*] --> task3
        [*] --> task4
        [*] --> task5
    }

    TaskCreation --> ParallelExec: Execute parallel

    state ParallelExec {
        [*] --> thread1
        [*] --> thread2
        [*] --> thread3
        thread1 --> results
        thread2 --> results
        thread3 --> results
    }

    ParallelExec --> Review: Supervisor review

    state Review {
        [*] --> analyze
        analyze --> supervisor_review_obj
    }

    Review --> Conversion: Convert to notes

    state Conversion {
        [*] --> note0
        [*] --> note1
        [*] --> note2
        [*] --> note3
        [*] --> note4
        [*] --> note5
    }

    Conversion --> StateOut

    state StateOut {
        [*] --> brief_unchanged
        [*] --> pages_filled
        [*] --> notes_filled
        [*] --> sub_results_filled
        [*] --> review_complete
    }

    StateOut --> [*]: Return to graph

    note right of StateIn
        ResearchState:
        - brief: ResearchBrief
        - pages: {}
        - notes: {}
        - sub_agent_results: {}
        - supervisor_review: None
    end note

    note right of StateOut
        ResearchState:
        - brief: ResearchBrief
        - pages: {10 URLs}
        - notes: {6 notes}
        - sub_agent_results: {6 results}
        - supervisor_review: SupervisorReview
    end note
```

## Parallel Execution Timeline

```mermaid
gantt
    title V2.0 Sub-Agent Parallel Execution
    dateFormat ss
    axisFormat %S

    section Supervisor
    Fetch URLs           :00, 10s
    Create Tasks         :10, 2s
    Review Results       :50, 5s
    Convert to Notes     :55, 2s

    section Thread 1
    Sub-Agent 0 Research :12, 15s
    Sub-Agent 0 Reflect  :27, 5s
    Sub-Agent 3 Research :32, 10s
    Sub-Agent 3 Reflect  :42, 3s

    section Thread 2
    Sub-Agent 1 Research :12, 18s
    Sub-Agent 1 Reflect  :30, 4s
    Sub-Agent 4 Research :34, 12s
    Sub-Agent 4 Reflect  :46, 4s

    section Thread 3
    Sub-Agent 2 Research :12, 12s
    Sub-Agent 2 Reflect  :24, 3s
    Sub-Agent 5 Research :27, 14s
    Sub-Agent 5 Reflect  :41, 5s
```

## Data Size Evolution in V2.0

```mermaid
graph LR
    subgraph "Input (Config)"
        Config[config.json<br/>~1 KB]
    end

    subgraph "Scraping"
        HTML[Raw HTML<br/>10 URLs<br/>1-5 MB total]
        MD[Markdown<br/>10 URLs<br/>300 KB - 1 MB]
    end

    subgraph "Context Building"
        Context[Combined Context<br/>All 10 pages<br/>300 KB - 1 MB<br/>NO TRUNCATION]
    end

    subgraph "Sub-Agent Results"
        SA1R[Result 1: 10-20 KB]
        SA2R[Result 2: 10-20 KB]
        SA3R[Result 3: 10-20 KB]
        SA4R[Result 4: 10-20 KB]
        SA5R[Result 5: 10-20 KB]
        SA6R[Result 6: 10-20 KB]
        Total[Total: 60-120 KB]
    end

    subgraph "Reflections"
        Ref[6 Reflections<br/>~1 KB each<br/>~6 KB total]
    end

    subgraph "Supervisor Review"
        Review[SupervisorReview<br/>~2 KB]
    end

    subgraph "Notes"
        Notes[6 Notes<br/>60-120 KB]
    end

    subgraph "Final Report"
        Report[Markdown Report<br/>49 KB<br/>447 lines]
    end

    subgraph "State File"
        State[state.json<br/>~4 MB<br/>includes all data]
    end

    Config --> HTML
    HTML --> MD
    MD --> Context
    Context --> SA1R
    Context --> SA2R
    Context --> SA3R
    Context --> SA4R
    Context --> SA5R
    Context --> SA6R
    SA1R --> Total
    SA2R --> Total
    SA3R --> Total
    SA4R --> Total
    SA5R --> Total
    SA6R --> Total
    Total --> Ref
    Total --> Review
    Ref --> Review
    Review --> Notes
    Notes --> Report
    MD --> State
    Total --> State
    Ref --> State
    Review --> State
    Notes --> State
```

## ThreadPoolExecutor Flow

```mermaid
sequenceDiagram
    participant Supervisor
    participant Executor as ThreadPoolExecutor<br/>(max_workers=3)
    participant F0 as Future 0
    participant F1 as Future 1
    participant F2 as Future 2
    participant F3 as Future 3
    participant F4 as Future 4
    participant F5 as Future 5
    participant Collector

    Supervisor->>Executor: Submit 6 tasks

    activate Executor
    Executor->>F0: execute_sub_agent(task_0)
    Executor->>F1: execute_sub_agent(task_1)
    Executor->>F2: execute_sub_agent(task_2)

    Note over Executor: Workers full (3/3)<br/>Tasks 3-5 queued

    F0-->>Collector: Result 0 complete
    Note over Executor: Worker free (2/3)

    Executor->>F3: execute_sub_agent(task_3)

    F2-->>Collector: Result 2 complete
    Note over Executor: Worker free (2/3)

    Executor->>F4: execute_sub_agent(task_4)

    F1-->>Collector: Result 1 complete
    Note over Executor: Worker free (2/3)

    Executor->>F5: execute_sub_agent(task_5)

    F3-->>Collector: Result 3 complete
    F5-->>Collector: Result 5 complete
    F4-->>Collector: Result 4 complete

    deactivate Executor

    Collector-->>Supervisor: All 6 results ready
```

## V2.1 Date Extraction Enhancement Flow

```mermaid
flowchart TD
    Source[Source Markdown<br/>Contains dates in multiple formats]

    Search[Sub-Agent searches for:]
    ISO["ISO: 2025-06-25"]
    Written["Written: June 25, 2025"]
    MonthYear["Month+Year: June 2025"]
    Quarter["Quarter: Q4 2025"]
    Year["Year: 2025"]

    Source --> Search
    Search --> ISO
    Search --> Written
    Search --> MonthYear
    Search --> Quarter
    Search --> Year

    Prioritize{Prioritization Rule:<br/>Use MOST PRECISE}

    ISO --> Prioritize
    Written --> Prioritize
    MonthYear --> Prioritize
    Quarter --> Prioritize
    Year --> Prioritize

    Prioritize -->|ISO or Written found| Precise[Use "June 25, 2025"]
    Prioritize -->|Only Month+Year| Medium[Use "June 2025"]
    Prioritize -->|Only Quarter| Vague[Use "Q4 2025"]
    Prioritize -->|Only Year| Last[Use "2025"]

    Precise --> Reflection
    Medium --> Reflection
    Vague --> Reflection
    Last --> Reflection

    Reflection{Self-Critique:<br/>Are dates precise?}

    Reflection -->|Yes| Accept[Accept findings]
    Reflection -->|No| Flag[Flag in reflection:<br/>missing_aspects]

    Accept --> Output[SubAgentResult<br/>with precise dates]
    Flag --> Output

    Output --> Supervisor[Supervisor Review<br/>checks date precision]

    style Source fill:#fff9c4
    style Precise fill:#c8e6c9
    style Medium fill:#fff9c4
    style Vague fill:#ffecb3
    style Last fill:#ffcdd2
    style Reflection fill:#f3e5f5
```

## Citation Tracking in V2.0

```mermaid
flowchart TD
    Pages[10 PageContent objects<br/>with URLs]

    SubAgent[Sub-Agent processes<br/>complete context]

    Extract[Extract facts with<br/>inline citations]

    Inline["Findings text:<br/>'Company has $385M fund [1]<br/>Announced June 25, 2025 [1]<br/>Led by Greg Wasserman [2]'"]

    Sources[Sources list:<br/>[url1, url2, ...]]

    Result[SubAgentResult<br/>- findings<br/>- sources]

    Notes[Convert to Note<br/>- content<br/>- sources]

    Writer[Writer receives<br/>all notes]

    Map[Map citations<br/>across all notes]

    Report["Final Report:<br/>[1] url1<br/>[2] url2<br/>...<br/>[10] url10"]

    Pages --> SubAgent
    SubAgent --> Extract
    Extract --> Inline
    Extract --> Sources
    Inline --> Result
    Sources --> Result
    Result --> Notes
    Notes --> Writer
    Writer --> Map
    Map --> Report

    style Pages fill:#e1f5ff
    style Inline fill:#fff9c4
    style Report fill:#c8e6c9
```

## Summary: V2.0 Data Flow Advantages

| Aspect | V1.0 | V2.0 | Benefit |
|--------|------|------|---------|
| **Context per LLM call** | Full context × 6 (sequential) | Full context × 6 (parallel) | Faster |
| **Specialization** | Generic research | Focused per question | Deeper |
| **Self-Critique** | None | 6 reflections | Quality |
| **Coordination** | None | Supervisor review | Gaps found |
| **Result tracking** | Simple notes | SubAgentResult + Reflection | Transparency |
| **State richness** | Basic | Full audit trail | Debuggable |
| **Citation precision** | Per note | Per note + per agent | Maintained |
| **Date precision** | Good | Enhanced (V2.1) | Better |

## Key Data Transformations

1. **URL → PageContent**: HTML → Markdown (html2text)
2. **PageContent → Context**: Concatenate all pages (no truncation)
3. **Context + Question → Findings**: GPT-4.1 research
4. **Findings → Reflection**: GPT-4.1 self-critique
5. **Findings + Reflection → SubAgentResult**: Structured result
6. **All SubAgentResults → SupervisorReview**: Gap analysis
7. **SubAgentResults → Notes**: Writer-ready format
8. **Notes → Report**: Final markdown with citations
