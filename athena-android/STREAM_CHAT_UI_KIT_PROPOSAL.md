# Stream Chat UI Kit integration proposal for athena-android

---

## Fork-based integration (selected)

We will fork Stream’s Android UI kit and adapt it to work with Athena’s own backend, without Stream’s APIs.

### Goals

- Reuse Stream’s polished chat UI/UX while removing dependency on `ChatClient` and Stream services.
- Introduce a clean data-layer abstraction to plug in Athena’s DRF/WS backend.
- Preserve future maintainability by isolating our changes and minimizing divergence where possible.

### Approach overview

1. Fork `stream-chat-android` and import only the UI packages (Compose preferred). Remove client/backend bindings.
2. Define Athena chat domain models and repository interfaces that the UI will consume.
3. Replace Stream ViewModels with Athena ViewModels backed by repositories using our REST/WebSocket services.
4. Provide adapters/mappers between wire DTOs and UI state models; expose state via Kotlin Flows.
5. Add real-time updates via WebSockets (Django Channels) and FCM for push wake-ups.

### Steps

1. Fork and vendor UI modules

   - Fork the repo: `GetStream/stream-chat-android`.
   - Vendor the needed modules into the monorepo under `athena-android/external/stream-chat-android` using git submodule or subtree.
   - Start with Compose: `stream-chat-android-compose` and its minimal UI dependencies. Avoid importing `chat-client` and `offline` plugins initially to reduce coupling.

2. Strip SDK client dependencies

   - Identify usages of `ChatClient`, `ChannelClient`, `ChannelListViewModel`, `MessageListViewModel`, `MessageComposerViewModel`, etc.
   - Create interfaces the UI can depend on, e.g., `ChannelRepository`, `MessageRepository`, `UserPresenceRepository`, with functions returning `Flow<...>` for reactive updates.
   - Replace direct SDK calls with calls to these interfaces, injected via constructor parameters or a simple DI provider.

3. Define Athena domain models and mappers

   - Domain: `AthenaUser`, `AthenaChannel`, `AthenaMessage`, `ReadState`, `TypingEvent`, `Reaction`, `Attachment`.
   - Create mapper utilities to convert backend DTOs into domain models and then into UI state models expected by the components.

4. Implement ViewModels backed by repositories

   - Recreate minimal equivalents of Stream’s list/detail ViewModels but backed by our repositories.
   - Expose `StateFlow` for lists (channels/messages), selection, pagination, typing indicators, and error states.

5. Networking and realtime

   - REST (DRF): endpoints for channels, messages, reactions, members, read states, uploads.
   - WebSockets: subscribe to channel/user events (new message, edit/delete, read, typing, reaction, membership).
   - Reconnect/backoff, message de‑duplication, and idempotent sends handled client-side.

6. Optional: offline cache (defer)

   - Start online-only. Add Room-based cache later if needed (messages, channels, users) with simple staleness rules.

7. Theming and UI integration

   - Keep Stream Compose components where possible; wrap with Athena theming.
   - For components that are too coupled, copy into `athena-android` and simplify props to use our interfaces.

8. Packaging and Gradle setup

   - Include the fork as a composite build or local modules referenced in `settings.gradle.kts`.
   - Expose only the UI module(s) to the `app` module; exclude Stream’s client artifacts.

9. QA scope

   - Channel list, empty states, unread counts, message list/compose, typing, reactions, attachments (images/files), pagination, thread replies (optional), read receipts, error/offline banners.

### DRF/Channels backend requirements (summary)

- Auth: existing Athena auth issues a JWT/session used for REST and WS.
- REST endpoints (class-based views): `/channels`, `/channels/{id}`, `/messages`, `/messages/{id}`, `/reactions`, `/typing`, `/reads`, `/attachments`.
- WebSocket events: `message.new`, `message.updated`, `message.deleted`, `typing.start`, `typing.stop`, `reaction.new`, `read.updated`, `channel.updated`, `member.added/removed`.
- Message IDs generated server-side; client sends a temporary ID for de‑duplication.

### Milestones and estimates

1. Spike (2–3 days): import UI modules, compile without Stream SDK; stub repositories.
2. Channels + messages MVP (1.5–2 weeks): list, view, send, receive (WS), basic pagination.
3. Core extras (1–1.5 weeks): typing, reactions, read receipts, attachments upload.
4. Nice-to-haves (1–2 weeks): threads, message edit/delete, offline cache, push deep links.

### Risks

- Hidden coupling inside UI modules that expects Stream types; mitigated by copying and pruning select components.
- Maintenance burden tracking upstream UI fixes; mitigated by vendoring via subtree and periodic merges.
- Realtime edge cases (reconnect, ordering) need careful testing.

### License and attribution

- Verify license in upstream repo and keep license/NOTICE files with vendored code.

### Next steps (actionable)

- [ ] Fork `stream-chat-android` and vendor Compose UI modules into `athena-android/external`.
- [ ] Create repository interfaces and domain models in a new `digipaws-core` chat package.
- [ ] Replace UI dependencies on Stream ViewModels with our interfaces via DI.
- [ ] Implement REST clients and WS client to back repositories.
- [ ] Wire Channel list → Message list → Composer flows end-to-end.
- [ ] Add reactions, typing, read receipts; defer threads/offline if timeline-bound.

---

### Option B — Reuse the UI without Stream’s backend (not recommended; significant effort)

Stream’s UI libraries are tightly coupled to Stream models (`User`, `Channel`, `Message`) and the `ChatClient`/view-models from the Stream SDK. Running the UI against a different backend means you must remove or replace these dependencies.

Two realistic paths:

1. Fork Stream’s UI modules and swap the data layer

- Clone Stream’s Android SDK repo and import the UI module(s) into `athena-android` as local modules.
- Replace usages of `ChatClient`, `ChannelListViewModel`, `MessageListViewModel`, etc., with your own repositories/view-models that fetch from your backend.
- Provide internal model adapters to feed the UI states the components expect.


1. Emulate the look-and-feel with custom Compose

- Build chat UIs in Compose using Material 3 and copy UX patterns from Stream’s components.
- Full control, no vendor tie-in, but you implement everything: pagination, read states, typing, attachments, threads, offline, push.

What you cannot do: point Stream’s `ChatClient` at an arbitrary backend. It talks to Stream’s APIs (hosted or on-prem). Without a Stream account/API key, you cannot connect real users/channels/messages using their SDK.

---

### Using athena-DRF as the token service (for Option A)

In `athena-DRF`, add a class-based view that returns a user token for the authenticated user. Pseudocode outline:

```python
class StreamTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # server-side: use STREAM_API_KEY + STREAM_API_SECRET (env vars)
        # create or upsert Stream user, then mint a token for request.user
        token = stream_server_client.create_token(user_id=str(request.user.id))
        return Response({"token": token})
```

Android flow:

1. App authenticates user with your backend.
2. App requests `/api/stream/token`.
3. App calls `ChatClient.connectUser(user, token)`.

Security: never ship Stream’s secret in the Android app.

---

### Recommendation & next steps

- For fastest delivery, proceed with Option A (Stream account) and wire `athena-DRF` to mint tokens.
- If vendor-free is a hard requirement, plan a fork of the UI modules or a custom Compose build (Option B) with the above estimates.

Checklist to implement Option A:

- [ ] Add Stream dependencies to `app`.
- [ ] Initialize `ChatClient` in your `Application`.
- [ ] Implement token endpoint in `athena-DRF` (class-based view).
- [ ] Connect user and build Channel list → Message screens.
- [ ] Style/theme to match Athena.
- [ ] (Optional) Push notifications via FCM.

### References

- Stream Chat Android docs: [UI overview](https://getstream.io/chat/docs/sdk/android/ui/overview/)
- Stream Compose UI docs: [Compose](https://getstream.io/chat/docs/sdk/android/compose/overview/)
- Stream server tokens: [Tokens](https://getstream.io/chat/docs/react/token_generator/)
