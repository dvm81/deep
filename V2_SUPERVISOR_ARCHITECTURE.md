# V2.0 Supervisor + Sub-Agent Architecture

## V2.0 Innovation: Multi-Agent Coordination

V2.0 introduces a **supervisor architecture** inspired by LangChain's `deep_research_from_scratch`, where a supervisor coordinates multiple specialized sub-agents that work in parallel with self-reflection capabilities.

## Supervisor Architecture Overview

```mermaid
graph TB
    subgraph "Research Phase - Supervisor Coordination"
        Supervisor[Research Supervisor<br/>supervisor.py]

        subgraph "Parallel Sub-Agents (ThreadPool)"
            SA1[Sub-Agent 1<br/>Decision Makers]
            SA2[Sub-Agent 2<br/>Regions/Sectors]
            SA3[Sub-Agent 3<br/>AUM/Metrics]
            SA4[Sub-Agent 4<br/>Strategies/Funds]
            SA5[Sub-Agent 5<br/>Portfolio Companies]
            SA6[Sub-Agent 6<br/>News/Announcements]
        end

        subgraph "Reflection System"
            R1[Reflection 1<br/>Completeness?]
            R2[Reflection 2<br/>Completeness?]
            R3[Reflection 3<br/>Completeness?]
            R4[Reflection 4<br/>Completeness?]
            R5[Reflection 5<br/>Completeness?]
            R6[Reflection 6<br/>Completeness?]
        end

        Review[Supervisor Review<br/>Identify Gaps<br/>Assess Readiness]
    end

    Supervisor -->|assigns tasks| SA1
    Supervisor -->|assigns tasks| SA2
    Supervisor -->|assigns tasks| SA3
    Supervisor -->|assigns tasks| SA4
    Supervisor -->|assigns tasks| SA5
    Supervisor -->|assigns tasks| SA6

    SA1 -->|findings| R1
    SA2 -->|findings| R2
    SA3 -->|findings| R3
    SA4 -->|findings| R4
    SA5 -->|findings| R5
    SA6 -->|findings| R6

    R1 -->|results| Review
    R2 -->|results| Review
    R3 -->|results| Review
    R4 -->|results| Review
    R5 -->|results| Review
    R6 -->|results| Review

    Review -->|consolidated notes| Writer[Writer Agent]

    style Supervisor fill:#ff9800,color:#fff
    style SA1 fill:#ffe0b2
    style SA2 fill:#ffe0b2
    style SA3 fill:#ffe0b2
    style SA4 fill:#ffe0b2
    style SA5 fill:#ffe0b2
    style SA6 fill:#ffe0b2
    style R1 fill:#f3e5f5
    style R2 fill:#f3e5f5
    style R3 fill:#f3e5f5
    style R4 fill:#f3e5f5
    style R5 fill:#f3e5f5
    style R6 fill:#f3e5f5
    style Review fill:#c5cae9
```

## Sub-Agent Execution Flow

```mermaid
sequenceDiagram
    participant Supervisor
    participant SubAgent
    participant GPT41 as GPT-4.1
    participant ReflectionLLM as GPT-4.1<br/>(Reflection)

    Supervisor->>SubAgent: Assign Task<br/>(question, context, URLs)

    activate SubAgent
    Note over SubAgent: Step 1: Research
    SubAgent->>SubAgent: Read ALL context
    SubAgent->>SubAgent: Extract details<br/>(names, dates, companies)
    SubAgent->>GPT41: Research Prompt<br/>(temp=0)
    GPT41-->>SubAgent: Detailed findings<br/>with citations

    Note over SubAgent: Step 2: Reflection
    SubAgent->>SubAgent: Self-critique findings
    SubAgent->>ReflectionLLM: Reflection Prompt<br/>"Is this complete?"
    ReflectionLLM-->>SubAgent: Reflection Result<br/>- is_complete<br/>- missing_aspects<br/>- confidence<br/>- next_steps

    SubAgent-->>Supervisor: SubAgentResult<br/>(findings + reflection)
    deactivate SubAgent

    Note over Supervisor: Collect all results
    Supervisor->>Supervisor: Review all findings
    Supervisor->>Supervisor: Identify gaps
    Supervisor->>Supervisor: Assess readiness
```

## Parallel Execution Architecture

```mermaid
graph LR
    subgraph "ThreadPoolExecutor (max_workers=3)"
        T1[Thread 1] --> SA1[Sub-Agent 1]
        T1 --> SA4[Sub-Agent 4]

        T2[Thread 2] --> SA2[Sub-Agent 2]
        T2 --> SA5[Sub-Agent 5]

        T3[Thread 3] --> SA3[Sub-Agent 3]
        T3 --> SA6[Sub-Agent 6]
    end

    SA1 -->|Result 1| Collector[Result Collector]
    SA2 -->|Result 2| Collector
    SA3 -->|Result 3| Collector
    SA4 -->|Result 4| Collector
    SA5 -->|Result 5| Collector
    SA6 -->|Result 6| Collector

    Collector --> Supervisor[Supervisor Review]

    style T1 fill:#b3e5fc
    style T2 fill:#b3e5fc
    style T3 fill:#b3e5fc
```

## Reflection System (Thinking Tool)

```mermaid
graph TB
    subgraph "Sub-Agent Reflection Process"
        Findings[Research Findings<br/>with citations]

        Questions{Reflection Questions}

        Q1[Is research complete?]
        Q2[What's missing?]
        Q3[Are dates precise?<br/>ISO? Written dates?]
        Q4[Confidence level?]
        Q5[Next steps?]

        Output[Reflection Output<br/>Structured Pydantic Model]

        Complete[is_complete: bool]
        Missing[missing_aspects: List]
        Conf[confidence: str]
        Next[next_steps: Optional]
    end

    Findings --> Questions
    Questions --> Q1
    Questions --> Q2
    Questions --> Q3
    Questions --> Q4
    Questions --> Q5

    Q1 --> Output
    Q2 --> Output
    Q3 --> Output
    Q4 --> Output
    Q5 --> Output

    Output --> Complete
    Output --> Missing
    Output --> Conf
    Output --> Next

    style Findings fill:#fff9c4
    style Output fill:#f3e5f5
```

## Supervisor Review Logic

```mermaid
flowchart TD
    Start[Receive All<br/>Sub-Agent Results] --> Count{All 6 agents<br/>completed?}

    Count -->|No| Error[Log Error<br/>Continue with available]
    Count -->|Yes| Compile[Compile Findings<br/>+ Reflections]

    Error --> Compile

    Compile --> GPT[GPT-4.1 Review<br/>Supervisor Prompt]

    GPT --> Review[SupervisorReview<br/>Structured Output]

    Review --> Assess[Assess:<br/>- overall_completeness<br/>- gaps_identified<br/>- refinement_needed<br/>- ready_for_writing]

    Assess --> Ready{ready_for_writing?}

    Ready -->|True| Convert[Convert to Notes<br/>for Writer]
    Ready -->|False| Future[V2.2: Iterative<br/>Refinement]

    Convert --> Output[Output consolidated<br/>notes to Writer]

    style Start fill:#e1f5ff
    style Review fill:#c5cae9
    style Output fill:#c8e6c9
    style Future fill:#ffecb3
```

## Key V2.0 Features

### 1. Specialization
Each sub-agent focuses on **ONE research question**, enabling deeper analysis:
- Sub-Agent 1: Decision Makers (70+ people extracted)
- Sub-Agent 2: Regions & Sectors
- Sub-Agent 3: AUM & Metrics
- Sub-Agent 4: Strategies & Funds
- Sub-Agent 5: Portfolio Companies (240+ companies)
- Sub-Agent 6: News & Announcements (20+ items with precise dates)

### 2. Reflection (Thinking Tool)
Each sub-agent self-critiques before returning results:
```python
class Reflection(BaseModel):
    is_complete: bool  # "Did I get everything?"
    missing_aspects: List[str]  # "What did I miss?"
    confidence: str  # "high", "medium", or "low"
    next_steps: Optional[str]  # "What should I do next?"
```

### 3. Parallel Execution
- ThreadPoolExecutor with 3 workers
- 6 sub-agents run concurrently
- Faster execution compared to V1.0 sequential processing
- Results collected as they complete (`as_completed`)

### 4. Supervisor Coordination
- Reviews all findings and reflections
- Identifies gaps across all research
- Assesses overall completeness
- Prepares for iterative refinement (V2.2+)

## Data Models (schema.py)

### Sub-Agent Task
```python
class SubAgentTask(BaseModel):
    task_id: str  # "q_0", "q_1", etc.
    question: str  # Specific research question
    context_urls: List[HttpUrl]  # URLs to focus on
```

### Sub-Agent Result
```python
class SubAgentResult(BaseModel):
    task_id: str
    findings: str  # Detailed findings with citations
    reflection: Reflection  # Self-critique
    sources: List[HttpUrl]  # URLs used
```

### Supervisor Review
```python
class SupervisorReview(BaseModel):
    overall_completeness: str  # Assessment
    gaps_identified: List[str]  # What's missing
    refinement_needed: bool  # Need another iteration?
    ready_for_writing: bool  # Ready for report?
```

## Performance Comparison

| Metric | V1.0 (Single Agent) | V2.0 (Supervisor) | Improvement |
|--------|---------------------|-------------------|-------------|
| Architecture | Linear | Parallel | ✅ |
| Agents | 1 | 6 specialized | **6x specialization** |
| Self-Critique | None | Reflection per agent | ✅ Added |
| Coordination | None | Supervisor review | ✅ Added |
| Execution | Sequential | Concurrent (3 workers) | **Faster** |
| Report Lines | 298 | 447-521 | **+51-75%** |
| Decision Makers | 48 | 70+ | **+46%** |
| Portfolio Companies | 240 | 240+ | Maintained |
| Gaps Identified | None | 9-11 per run | **Quality check** |
| Confidence Tracking | None | Per agent | **Transparency** |

## Future Enhancements (V2.2+)

### Iterative Refinement
```mermaid
graph LR
    SubAgent[Sub-Agent Result] --> Review[Supervisor Review]
    Review --> Check{Gaps found?}
    Check -->|Yes| Refine[Re-run specific<br/>sub-agents]
    Check -->|No| Ready[Ready for writing]
    Refine --> SubAgent
```

### Dynamic Sub-Agent Spawning
```mermaid
graph TB
    Review[Supervisor Review] --> Gaps{New questions<br/>emerged?}
    Gaps -->|Yes| Spawn[Spawn additional<br/>sub-agent]
    Gaps -->|No| Continue[Continue]
    Spawn --> Execute[Execute new agent]
    Execute --> Review
```

### Confidence-Based Prioritization
- Focus refinement on low-confidence findings
- Skip re-running high-confidence agents
- Optimize iteration cycles

## Code Structure

```
company_research/agents/
  ├── supervisor.py          # NEW V2.0: Coordinates sub-agents
  ├── sub_agent.py           # NEW V2.0: Specialized research + reflection
  ├── planner.py             # Scope phase (unchanged)
  ├── writer.py              # Write phase (enhanced for V2.1 dates)
  └── graph.py               # Updated to use supervisor
```

## Configuration

```python
# ThreadPool configuration (supervisor.py)
ThreadPoolExecutor(max_workers=3)

# LLM configuration (config.py)
model="gpt-4.1"
temperature=0  # V2.1: Maximum factual consistency
```

## Monitoring & Logging

Sub-agent execution provides real-time feedback:
```
[3/4] Executing 6 sub-agents in parallel...
  → Sub-agent working on: q_0
  → Sub-agent working on: q_1
  → Sub-agent reflecting on: q_0
  ✓ Sub-agent completed: q_0 (confidence: medium)
  ...
  ✓ Completed 6/6 sub-agents
```

Supervisor review summary:
```
[4/4] Supervisor reviewing findings...
  Completeness: The research provides a solid foundation...
  Ready for writing: True
  Gaps identified: 11
```

## Summary

V2.0's supervisor architecture delivers:
- ✅ **Better Quality**: Specialized agents + reflection
- ✅ **Better Speed**: Parallel execution
- ✅ **Better Completeness**: Supervisor identifies gaps
- ✅ **Better Transparency**: Confidence tracking per finding
- ✅ **Better Scalability**: Easy to add more sub-agents or refinement loops
