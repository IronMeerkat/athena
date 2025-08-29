# Architecture Diagrams

This document illustrates several key flows and structures in the Athena Android app using [Mermaid](https://mermaid.js.org/) diagrams.  You can view these diagrams rendered in a Markdown viewer that supports Mermaid (e.g. GitHub, VS Code).

## App/URL Decision Flow

```mermaid
sequenceDiagram
    participant User
    participant OS as Android OS
    participant Acc as AccessibilityService
    participant PE as PolicyEngine
    participant LPS as LocalPolicyStore
    participant Cache as DecisionCache
    participant DRF as DRF
    participant Overlay as BlockOverlayActivity

    OS->>Acc: Foreground change (pkg, url)
    Acc->>PE: onForegroundChange(pkg, url)
    alt pause active or hardcode inactive
        PE-->>Acc: allow (no block)
    else
        PE->>LPS: isAllowed(pkg, url)
        alt allowed locally
            LPS-->>PE: allowed
            PE-->>Acc: allow
        else not in local rules
            LPS-->>PE: not allowed
            PE->>Cache: get(pkg,url)
            alt cached allow
                Cache-->>PE: allow
                PE-->>Acc: allow
            else cached block
                Cache-->>PE: block
                PE->>Overlay: showBlock(reason)
            else no cache
                Cache-->>PE: none
                PE->>DRF: POST /api/device/attempt
                DRF-->>PE: {run_id, decision: pending}
                PE->>DRF: GET /api/runs/{run_id}/events (SSE)
                DRF-->>PE: event "decision" {allow|block, message, ttl}
                alt decision=allow
                    PE-->>Acc: allow
                else decision=block
                    PE->>Cache: put(pkg,url,block,ttl)
                    PE->>Overlay: showBlock(message)
                end
            end
        end
    end
```

## PolicyEngine State Machine

```mermaid
stateDiagram-v2
    [*] --> Normal
    Normal --> Paused: user toggles pause
    Paused --> Normal: user resumes
    Normal --> Hardcode: commit(duration)
    Paused --> Hardcode: commit(duration)
    Hardcode --> Hardcode: cannot exit until expiry
    Hardcode --> [*]: expiry reached
```

## Android Components (Class Diagram)

```mermaid
classDiagram
    class AthenaApplication
    class MainActivity
    class SettingsActivity
    class BlockOverlayActivity
    class AccessibilityService
    class ForegroundMonitorService
    class PolicyEngine
    class LocalPolicyStore
    class DecisionCache
    class AthenaApiClient
    class AuthManager
    class SettingsRepository
    class HardcodeController
    class BlockOverlayController

    AthenaApplication --> PolicyEngine
    MainActivity --> PolicyEngine
    MainActivity --> BlockOverlayController
    SettingsActivity --> PolicyEngine
    SettingsActivity --> HardcodeController
    AccessibilityService --> PolicyEngine
    ForegroundMonitorService --> AthenaApplication
    PolicyEngine --> LocalPolicyStore
    PolicyEngine --> DecisionCache
    PolicyEngine --> AthenaApiClient
    PolicyEngine --> SettingsRepository
    PolicyEngine --> HardcodeController
    BlockOverlayController --> BlockOverlayActivity
    HardcodeController --> SettingsRepository
    AthenaApiClient --> AuthManager
    AthenaApiClient --> SettingsRepository
```

These diagrams are adapted from the original proposal and modified to match the simplified implementation present in this repository.