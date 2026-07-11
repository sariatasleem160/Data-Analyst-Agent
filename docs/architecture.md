# Architecture — Data Analyst Agent

## System overview

```mermaid
flowchart TB
    subgraph UserLayer["User Layer"]
        UI["Streamlit UI<br/>(app.py)"]
        CSV["CSV Upload / Sample Data"]
    end

    subgraph AgentLayer["Agent Layer"]
        PLAN["Planner<br/>(planner.py)"]
        AGENT["Data Analyst Agent<br/>(agent.py)"]
        MEM["Memory Store<br/>(memory.py)"]
        CLAUDE["Anthropic Claude API<br/>claude-sonnet-4-6"]
    end

    subgraph SafetyLayer["Safety Layer"]
        SCHEMAS["Tool Schemas<br/>(tool_schemas.py)"]
        VALID["Input Sanitization<br/>+ Tool Allowlist"]
        LIMITS["Step & Token Limits"]
    end

    subgraph ExecutionLayer["Execution Layer"]
        TOOLS["Safe Tools<br/>(tools.py)"]
        PANDAS["Pandas DataFrame"]
        CHARTS["Charts → results/charts/"]
    end

    subgraph ExternalLayer["External Interfaces"]
        MCP["MCP Server<br/>(mcp_server.py)"]
        EVAL["Evaluation Suite<br/>(evaluate.py)"]
        INJ["Injection Tests<br/>(injection_tests.py)"]
    end

    CSV --> UI
    UI --> AGENT
    AGENT --> PLAN
    PLAN --> CLAUDE
    AGENT --> MEM
    AGENT --> CLAUDE
    CLAUDE -->|"tool_use request"| AGENT
    AGENT --> VALID
    VALID --> SCHEMAS
    SCHEMAS --> TOOLS
    TOOLS --> PANDAS
    TOOLS --> CHARTS
    TOOLS -->|"JSON result"| AGENT
    AGENT -->|"trace steps"| UI
    AGENT --> LIMITS
    MCP --> TOOLS
    EVAL --> AGENT
    INJ --> TOOLS
```

## Data flow (single question)

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Streamlit UI
    participant A as Agent
    participant P as Planner
    participant C as Claude API
    participant T as Safe Tools
    participant D as DataFrame

    U->>UI: Ask question + CSV
    UI->>A: run(question)
    A->>P: Create plan
    P->>C: Plan prompt
    C-->>P: 2-5 step plan
    A->>C: System prompt + tools + question
    C-->>A: tool_use (e.g. get_schema)
    A->>T: validate & execute
    T->>D: pandas operation
    D-->>T: result
    T-->>A: JSON-safe result
    A->>C: tool_result
    C-->>A: tool_use or final answer
    A-->>UI: answer + trace
    UI-->>U: Display answer & steps
```

## Safety model

```mermaid
flowchart LR
    Q["User Question"] --> M["Claude Model<br/>(decides only)"]
    M --> TC["Tool Call Request"]
    TC --> V{"Validation"}
    V -->|"Unknown tool / bad args"| X["Rejected"]
    V -->|"Pass"| E["Your Python Code<br/>(executes only)"]
    E --> R["Structured JSON Result"]
    R --> M
    M --> A["Final Answer"]

    style M fill:#e8f4fd
    style E fill:#e8fde8
    style X fill:#fde8e8
```

## Component map

| File | Role |
|------|------|
| `app.py` | Streamlit UI, trace viewer, file upload |
| `agent.py` | Tool-calling loop, step/token limits |
| `planner.py` | Pre-plan before tool execution |
| `memory.py` | Embedding-based Q&A recall |
| `tools.py` | 8 safe pandas tools + JSON sanitization |
| `tool_schemas.py` | Anthropic tool JSON schemas |
| `mcp_server.py` | MCP server exposing 5 tools |
| `evaluate.py` | 10-task success rate benchmark |
| `injection_tests.py` | Prompt-injection defense tests |

## 8 safe tools

```mermaid
mindmap
  root((Safe Tools))
    Inspect
      get_schema
      profile_dataset
      describe_column
    Transform
      filter_rows
      group_and_aggregate
      top_n
      compare_periods
    Visualize
      make_chart
```
