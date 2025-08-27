Here are two concise UML-style diagrams in Mermaid that Cursor should render fine: a **sequence diagram** for the app/site attempt + appeals, and a **flow/activity diagram** for the Distraction Guardian’s decision logic (strictness, nudge vs block).

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Device as Android Device
    participant DRF as DRF Gateway<br/>(Auth/Policy/Manifests)
    participant RMQ as RabbitMQ (vhosts)
    participant Worker as LangChain Worker<br/>(public|sensitive)
    participant Agents as Agents:<br/>ContextAssembler,DistractionGuardian,AppealsMediator
    participant Tools as Tools:<br/>PolicyStore,MemoryAPI,AppClassifier,DeviceController,Notifier,RateLimiter
    participant Redis as Redis (short-term state)

    User->>Device: Tap app / open URL
    Device->>DRF: POST /api/device/attempt {app,url,policy,state}
    DRF->>DRF: Resolve user/role → build Capability Manifest
    DRF->>Redis: Write run/event stub (pending)
    DRF->>RMQ: Enqueue run (vhost: public|sensitive)
    DRF-->>Device: SSE start (/api/runs/{id}/events)

    RMQ-->>Worker: run_graph(manifest, attempt)
    Worker->>Agents: ContextAssembler()
    Agents->>Tools: MemoryAPI.read(allowed namespaces)
    Agents->>Tools: PolicyStore.read(blocks, rules)
    Agents->>Tools: AppClassifier.categorize(app/url)
    Agents->>Tools: RateLimiter.peek()
    Agents-->>Worker: context bundle

    Worker->>Agents: DistractionGuardian.decide(context)
    alt Allow
        Worker-->>DRF: event {decision: allow}
        DRF-->>Device: SSE {allow}
        Device-->>User: Open app/site
    else Nudge
        Worker-->>DRF: event {decision: nudge, ttl: 2m}
        DRF-->>Device: SSE {nudge offer}
        Device->>DRF: POST /api/device/permit (accept 2m)
        DRF->>Tools: DeviceController.grant(permit token)
        DRF-->>Device: SSE {permit issued}
    else Block
        Worker-->>DRF: event {decision: block}
        DRF-->>Device: SSE {block + appeal_available}
        Device->>DRF: WebSocket /ws/appeals/{id}
        DRF->>Agents: AppealsMediator.start()
        Agents->>Tools: MemoryAPI.read(only policy_view)
        Agents-->>DRF: outcome {grant 3m | uphold}
        DRF->>Tools: DeviceController.apply(outcome)
        DRF-->>Device: WS {outcome}
    end

    Worker->>Tools: PolicyStore.update(counters,cooldowns)
    Worker->>Redis: Update run status
    Worker-->>DRF: event {complete}
    DRF-->>Device: SSE {complete}
```

```mermaid
flowchart TD
    A[Start: Attempt arrives<br/>app/url + current policy] --> B[Assemble Context<br/>blocks, goals policy_view,<br/>strictness, history, category]
    B --> C{Category allowed<br/>by current block?}
    C -- Yes --> ALLOW[ALLOW<br/>Return allow decision]
    C -- No --> D{Strictness threshold<br/>reached?}
    D -- Low/Moderate --> NUDGE[NUDGE<br/>Offer micro-permit (e.g., 2m)]
    D -- High --> E{Recent compliance good?<br/>(few overrides, obeyed nudges)}
    E -- Yes --> NUDGE
    E -- No --> F{Appeal allowed?<br/>(timebox, cooldown)}
    F -- No --> BLOCK[BLOCK<br/>Short, firm message]
    F -- Yes --> APPEAL[APPEAL<br/>Open WS chat]
    APPEAL --> G{User rationale acceptable?<br/>(goal-aligned, brief, rare)}
    G -- Yes --> PERMIT[Grant temporary permit<br/>(2–5m), log]
    G -- No --> BLOCK
    NUDGE --> PERMIT?{User accepts nudge?}
    PERMIT? -- Yes --> PERMIT
    PERMIT? -- No --> BLOCK
    ALLOW --> H[Update counters/cooldowns<br/>smooth strictness adjust]
    PERMIT --> H
    BLOCK --> H
    H --> I[Emit audit + events]
    I --> J[End]
```

If you want a quick **component diagram** too (how services fit together):

```mermaid
graph LR
  subgraph Client
    React[React Web App]
    Android[Android App]
  end

  subgraph Server
    DRF[DRF Gateway<br/>Auth, RBAC, Manifests, SSE/WS]
    Redis[(Redis<br/>short-term state)]
    RMQ[(RabbitMQ<br/>vhosts: public, sensitive)]
  end

  subgraph Workers
    PublicW[LangChain Worker - Public]
    SensitiveW[LangChain Worker - Sensitive]
  end

  subgraph LC[LangChain Graph]
    Context[Context Assembler]
    Guardian[Distraction Guardian]
    Mediator[Appeals Mediator]
    Planner[Schedule Planner]
  end

  subgraph Tools
    PolicyStore[PolicyStore]
    MemoryAPI[Memory API<br/>namespaced]
    AppClass[AppClassifier]
    DeviceCtl[DeviceController]
    Notifier[Notifier (FCM/VAPID)]
    RateLimiter[RateLimiter]
  end

  React -- SSE/WS --> DRF
  Android -- SSE/WS + FCM --> DRF
  Android -- Device intents --> DRF
  DRF <---> Redis
  DRF -- enqueue --> RMQ
  RMQ -- public --> PublicW
  RMQ -- sensitive --> SensitiveW
  PublicW --> LC
  SensitiveW --> LC
  LC --> Tools
  Tools --> Redis
```

These mirror the behavior we discussed: DRF builds a capability manifest, routes to the correct worker via RabbitMQ vhosts, Distraction Guardian makes a fast decision (allow/nudge/block/appeal), and—if needed—Appeals Mediator runs a short WebSocket dialogue before granting a temporary permit or upholding the block.
