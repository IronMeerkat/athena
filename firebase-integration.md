### 1) Fireside App — Top-level UI States

```mermaid
stateDiagram-v2
    [*] --> Home
    Home --> Chat: Open chat
    Home --> Blocks: Block screen shown
    Home --> Goals: Start Goals Session
    Home --> Journal: Open Pensive
    Home --> Settings: Open settings
    Home --> Notifications: Tap notification

    Chat --> Home: Back
    Goals --> Home: Save/Exit
    Journal --> Home: Back
    Settings --> Home: Back
    Notifications --> Home: Dismiss

    Blocks --> Appeals: Tap "Appeal"
    Appeals --> Blocks: Outcome = Uphold
    Appeals --> Permit: Outcome = Grant permit
    Permit --> Home: Auto-close on apply
```

---

### 2) App/Site Block → Appeals (Full UI Sequence)

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Fireside as Fireside UI
    participant Device as Device Policy Client
    participant DRF as DRF Gateway
    participant WS as WS /ws/appeals/{id}

    User->>Device: Attempt open app/site
    Device-->>Fireside: Show Block screen (decision: block)
    User->>Fireside: Tap "Appeal"
    Fireside->>DRF: Open WebSocket /ws/appeals/{id}
    DRF-->>Fireside: WS connected (Appeals session start)

    note over Fireside,DRF: Appeals chat UI (guided prompts)

    User->>WS: Rationale (e.g., “need 3m to send link”)
    DRF-->>Fireside: WS message (clarifying question)
    User->>WS: Confirmation
    DRF-->>Fireside: Outcome {grant 3m | uphold}

    alt Grant permit
        Fireside-->>Device: Apply permit (token + TTL)
        Fireside-->>User: Toast “3 minutes granted”
        Fireside-->>Fireside: Close Appeals → Home
    else Uphold
        Fireside-->>User: Message “Let’s do it after block”
        Fireside-->>Fireside: Return to Block screen
    end
```

---

### 3) Nudge Flow (Micro-break Offer)

```mermaid
flowchart TD
    A[User opens borderline app/site] --> B[Decision: NUDGE]
    B --> C[Fireside shows Nudge Card<br/>“2 minutes, then back?”]
    C -->|Accept| D[Request permit (TTL=2m)]
    D --> E[Apply permit token on device]
    E --> F[Show countdown in UI]
    C -->|Decline| G[Show soft block message]
    F -->|TTL ends| H[Auto-close app/site + toast]
    H --> I[Return to previous focus view]
```

---

### 4) Goals Session (Owner → Schedule/Policies)

```mermaid
flowchart LR
    A[Open Goals Session] --> B[Edit Objectives<br/>and weekly targets]
    B --> C[Pick Habits / Constraints]
    C --> D[Preview Schedule Blocks<br/>(focus/social/sleep)]
    D --> E[Policy Mapping<br/>block → policy_id]
    E --> F[Strictness Prefs<br/>(range + tone)]
    F --> G[Save]
    G --> H[Toast “Schedule updated”]
    H --> I[Back to Home]
```

---

### 5) Fireside Home Composition (Wireframe-ish Map)

```mermaid
graph TD
    Home[Home Screen]
    Chat[Chat Thread<br/>(Athena persona)]
    Cards[Context Cards<br/>(Today schedule, Active policy, Nudges)]
    Buttons[Quick Actions<br/>(Appeal, Pause 5m, Journal, Goals)]
    Feed[Notifications Feed]

    Home --> Chat
    Home --> Cards
    Home --> Buttons
    Home --> Feed
```

---

### 6) Notification Tap Flows

```mermaid
flowchart TD
    N1[Notification: Result ready] --> H1[Open Chat at run]
    N2[Notification: Nudge expiring] --> H2[Open Nudge Card]
    N3[Notification: Blocked attempt] --> H3[Open Block screen]
    N4[Notification: Partner social mode] --> H4[Show policy banner + TTL]
```

---

#### UI Notes (implementation cues)

* **Block screen**: large title, reason tag (“Deep Focus”), two buttons: **Appeal** and **Back to work**.
* **Nudge card**: primary button = **Accept 2m**, secondary = **Not now**; show small countdown if accepted.
* **Appeals chat**: 3–4 message max, with a visible **“time left”** indicator; outcome banner at top.
* **Policy banner**: non-modal; shows current policy + TTL; tap reveals details.
