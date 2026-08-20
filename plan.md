## Plan: Elena V1 Local Agent

Build Elena as a Windows-first, local personal agent with a small immutable Python harness, a mutable but strictly isolated Elena workspace, a PySide6 desktop/tray host, and a React UI. Development on the work laptop uses deterministic fake providers and disabled optional ML components; the same repository is cloned at home for LM Studio, Kokoro, faster-whisper, Docker, browser, microphone, GPU, and packaging validation. V1 is breadth-first: every major capability discussed has a real end-to-end implementation, while depth and autonomy remain gated, reversible, and observable.

### Product Contract

- Elena is an American-butler-style personal assistant: concise, capable, persistent, and in character in all human-facing text and speech.
- The harness is immutable to Elena. It owns orchestration, permissions, context budgets, approvals, persistence contracts, recovery, scheduling, provider selection, and shutdown.
- Elena may modify only her configured workspace data: memories, declarative skills, proposed tools, scripts, project files, and profiles.
- Built-in tools are sealed, typed harness code. Elena-generated code and third-party tools are untrusted and can execute only through the Docker executor.
- No capability is loaded into model context unless currently relevant. Large results are persisted externally and represented in context by compact summaries and stable references.
- Memory means curated notes; recall means exact conversation history. Every derived memory keeps provenance back to exact messages or tool artifacts.
- Ambiguity is a first-class state. Risky, irreversible, or underspecified actions enter `WAITING_FOR_USER` through the native clarification tool.
- Failure never disappears behind a generic error. Each task reaches complete, cancelled, or an actionable blocked state containing diagnosis, attempts, and the next decision needed.
- The UI exposes concise rationale and activity summaries, never private chain-of-thought. Only Elena's top-level answer is spoken by default.

### Chosen Stack

- Python 3.12, `uv`, Pydantic v2, asyncio, FastAPI, Uvicorn, HTTPX, SQLAlchemy/Alembic, SQLite WAL/FTS5, structlog, APScheduler, pytest, Ruff, Pyright.
- PySide6 tray host that opens the React UI in the default browser; React + TypeScript + Vite frontend with a restrained, work-focused design and an attractive 2D face driven by Web Audio amplitude.
- Deterministic fake model, TTS, STT, browser, and clock adapters for work-laptop development and CI.
- LM Studio through its OpenAI-compatible local endpoint as the first real model provider at home. A provider is selected when a conversation starts and remains pinned for that conversation and its subagents.
- Kokoro `af_heart` TTS and faster-whisper STT as optional, lazy-loaded home-PC adapters. Text chat remains fully usable when either is unavailable.
- Docker Desktop/WSL2 as the mandatory executor for generated scripts, third-party tool code, and sandboxed MCP servers. No Docker means those capabilities are disabled, not run unsafely.
- SQLite is the V1 source of truth. FTS5 handles exact/lexical recall; an edge table represents graph relationships; a pluggable local embedding index can add semantic candidates. Separate graph/vector services are deferred until benchmarked need exists.

### Process And Trust Topology

1. The PySide6 host is the sole top-level process. It owns tray actions, window show/hide, runtime supervision, single-instance locking, startup health checks, restart policy, and full exit.
2. The runtime runs as a supervised child on `127.0.0.1` using an ephemeral port and per-launch authentication token. It owns conversations, the agent state machine, context, tools, skills, tasks, voice adapters, storage, and WebSocket events.
3. React is built into static assets and displayed by `QWebEngineView`; development mode may use Vite, but production does not require a separate browser or Node process.
4. Untrusted workers run in short-lived Docker containers. The repository, application-data directory, credentials, Docker socket, and host home directory are never mounted.
5. User data lives outside the public repository under `%LOCALAPPDATA%/Elena/` plus the separately selected Elena workspace. Secrets use Windows Credential Manager through `keyring`, not files or environment committed to disk.
6. The runtime uses explicit states: `IDLE`, `THINKING`, `RUNNING_TOOL`, `WAITING_FOR_USER`, `WAITING_FOR_APPROVAL`, `DELEGATED`, `RECOVERING`, `COMPLETED`, `BLOCKED_ACTIONABLE`, and `CANCELLED`.

### Planned Repository

- `src/elena/desktop.py` - PySide6 tray host, browser launch, global hotkey, lifecycle supervision, packaging entry point.
- `apps/ui/` - React/TypeScript UI, chat, face, activity drawers, approvals, tasks/subagents, memory/skills/settings views.
- `src/elena/harness/` - immutable orchestrator, state machine, policy engine, context builder, approval service, scheduler, checkpoints, event contracts.
- `src/elena/providers/` - fake provider and LM Studio adapter; optional provider SPI and a non-blocking Copilot feasibility spike.
- `src/elena/storage/` - SQLite models, Alembic migrations, repositories, FTS5 index, artifact store, provenance and edge graph.
- `src/elena/tools/` - sealed native tools, capability retrieval, registry, result compaction, MCP adapter, hot reload events.
- `src/elena/skills/` - declarative skill schema, matching, execution planner, candidate detection, versioning and rollback.
- `src/elena/agents/` - delegated task contexts, progress events, cancellation, timeout and parent/child checkpoint links.
- `src/elena/sandbox/` - Docker profiles, image definitions, mount policy, path/reparse-point checks, resource limits, audit records and cleanup.
- `src/elena/voice/` - fake, Kokoro and faster-whisper adapters, audio cache and speech-only response projection.
- `workspace-template/` - initial mutable directories and example declarative skill/tool manifests, with no personal data.
- `tests/` - unit, contract, integration, security, UI and home-hardware smoke suites.
- `docs/` - architecture laws, threat model, data model, extension contracts, development, home setup, security, privacy and release runbooks.
- `.github/workflows/` - public-repository CI, dependency review, secret scanning, Python/Node tests and Windows desktop smoke build.

## Steps

### Phase 0: Lock Contracts And Threat Model

1. Write architecture decision records for the immutable/mutable boundary, process topology, session-pinned providers, SQLite-first retrieval, Docker-only untrusted execution, and public-repository data policy.
2. Define versioned Pydantic/JSON contracts before implementations: `Conversation`, `Message`, `Task`, `TaskCheckpoint`, `ActivityEvent`, `ToolManifest`, `ToolCall`, `ToolResultRef`, `SkillManifest`, `Memory`, `EvidenceRef`, `ApprovalRequest`, `ClarificationRequest`, `SubagentTask`, and `Schedule`.
3. Define the policy matrix by capability, risk, reversibility, network access, filesystem access, approval requirement, and executor. Native host subprocess execution is absent by design.
4. Define measurable V1 budgets: maximum prompt tokens by section, active tool count, tool-result inline size, subagent concurrency, execution time/resources, WebSocket event retention, startup memory, and archive growth.

### Phase 1: Scaffold And Continuous Verification

5. Scaffold the Python package, React app, PySide6 host, configuration loader, local app-data layout, structured logging, database migrations, fake adapters, and public-safe `.gitignore`/sample configuration. Initialize Git only after confirming `conv.txt` and personal artifacts are excluded or intentionally retained.
6. Add GitHub Actions for Ruff, Pyright, pytest, frontend lint/typecheck/tests, dependency review, secret scanning, and Windows packaging smoke tests. CI must never require LM Studio, Docker, microphone, GPU, Kokoro, Whisper, or Copilot credentials.
7. Add a one-command developer path that launches desktop + runtime + built frontend with fake adapters, and a diagnostics screen that reports optional dependency availability without treating absence as failure.

### Phase 2: First Persistent Conversation Slice

8. Implement the supervised runtime lifecycle and local authenticated REST/WebSocket transport. Full exit must stop audio work, cancel tasks, terminate containers, flush SQLite/logs, stop the runtime child, remove locks, and then exit the tray process.
9. Implement the agent state machine using the deterministic fake provider first: user message, provider stream, structured action request, tool result, final Elena response, cancellation, timeout, and actionable failure.
10. Implement append-only message/event persistence and checkpoints before external effects. On restart, recover incomplete tasks into a visible resumable or actionable state rather than silently replaying effects.
11. Build the initial React chat and activity UI: streaming answer, concise working status, expandable action summaries, cancel/intervene controls, reconnect/state resync, and strict separation between spoken response and technical activity.

### Phase 3: Context, Memory, And Exact Recall

12. Implement the context builder as a deterministic budget allocator for immutable instructions, current goal/state, recent dialogue, relevant memories, active skill, selected tool schemas, recent decisions, and compact tool-event summaries.
13. Persist large tool outputs as content-addressed artifacts. Replace them in active context with a summary, artifact ID, tool-call ID, provenance, and retrieval hint; support exact re-read without repeating the tool call.
14. Implement curated memories with type, confidence, importance, freshness policy, status, source evidence, access history, and supersession links. Contradictions create historical/current relationships rather than destructive overwrites.
15. Implement `conversation.search` and `conversation.read` as native harness tools. Search uses metadata + FTS5 to return tiny ranked candidates; read returns bounded message slices with neighboring context and source IDs.
16. Add optional local semantic retrieval behind an `EmbeddingIndex` interface and a relational `entity_edges` projection for graph expansion. Fuse exact, FTS, semantic, recency, importance, and graph-neighborhood scores; benchmark against a labeled recall corpus before enabling semantic retrieval by default.
17. Build recall evaluation fixtures from paraphrases, vague references, dates, names, and deliberately similar conversations. Measure candidate recall, correct-slice ranking, tokens injected, and false-positive rate.

### Phase 4: Clarification, Approvals, And Native Tools

18. Implement native `ask_user` with options plus free text and the `WAITING_FOR_USER` state. The model proposes uncertainty/risk metadata; deterministic policy decides whether clarification or approval is mandatory.
19. Implement risk-based approvals with preview, requested capability, exact scope, side effects, network policy, artifact hash, expiry, approve-once/reject/edit, and audit history. Destructive actions never gain blanket approval in V1.
20. Add the sealed minimum tool set: bounded workspace list/search/read/write/move/copy/create-directory, artifact read, memory CRUD, recall search/read, task status/cancel, schedule CRUD, and `ask_user`. Every path operation resolves canonical paths and rejects paths, symlinks, junctions, or reparse points escaping the workspace.
21. Implement capability retrieval so the model receives only the top relevant approved tool schemas plus native always-available cognitive tools. Remove unused tool schemas on the next turn while retaining compact call records.

### Phase 5: Docker Sandbox, Browser, And Hot-Loaded Tools

22. Build two explicit Docker profiles. `compute` has no network and mounts only a per-run staging directory plus approved workspace paths. `browser` has controlled outbound network and mounts only a dedicated downloads/exchange directory. Both use non-root users, read-only root filesystems, dropped capabilities, `no-new-privileges`, PID/CPU/memory/time limits, bounded tmpfs, output limits, immutable image digests, and no Docker socket or secrets.
23. Preflight Docker availability, image digest, Windows path sharing, workspace root identity, ACLs, and reparse points. Revalidate requested paths immediately before staging/mounting; copy inputs into run-specific staging where practical to reduce time-of-check/time-of-use races.
24. Implement execution preview, approval, script/content hash binding, container creation, structured stdout/stderr streaming, user stop, timeout/kill, orphan cleanup, post-run artifact inventory, and immutable audit record. If Docker is unavailable, return a clear disabled capability and continue in text/native-tool mode.
25. Run an automated containment suite covering path traversal, mount injection, symlink/junction escape, repo/app-data/credential access, network denial, Docker socket access, fork bomb, CPU/memory/disk/log exhaustion, timeout, orphan cleanup, and attempts to alter the harness.
26. Integrate Playwright MCP through the network-enabled browser container with an ephemeral browser profile. Browser output is captured as bounded snapshots/extractions; downloads enter the exchange directory and require a brokered move into the workspace.
27. Implement proposed-tool lifecycle: discover or author manifest, keep `PROPOSED`, show source/code/permissions, run schema and security checks, test in Docker, request approval, activate an immutable version, emit `TOOL_ADDED`, and make it available to the current conversation without restarting. Rollback and disable remain harness operations.

### Phase 6: Skills And Delegated Agents

28. Define skills as non-executable declarative workflows referencing approved tools, constraints, examples, expected outcomes, and recovery/clarification steps. Skill changes are versioned and hot-reloaded; executable helper code remains a sandboxed tool, never an imported host plugin.
29. Record normalized successful task traces and detect repeated patterns offline. A candidate skill requires multiple materially similar successful traces, a generated draft, replay tests, and user approval; Elena cannot silently activate a learned behavior.
30. Implement subagents as child task contexts under the same session-pinned provider, each with a scoped prompt, token budget, allowed tools, deadline, checkpoint stream, and cancellation token. They do not receive the parent transcript wholesale.
31. Stream subagent summaries and progress to the UI. Support inspect, interrupt with a new instruction, cancel, timeout, retry from checkpoint, and parent synthesis; cap concurrency and queue excess work.

### Phase 7: Desktop, Voice, And Face

32. Finish the PySide6 tray shell: first-run setup in the browser UI, two-action tray menu, `Ctrl+F4` open hotkey, runtime supervision, labeled-container cleanup, and complete exit. Do not register Windows auto-start until explicitly enabled.
33. Add provider setup and health UX. LM Studio setup discovers local or remote endpoints and models; GitHub Copilot uses the official Microsoft Agent Framework connector and Copilot SDK. Both test model discovery before confirmation and pin the selection to each new conversation.
34. Add the Kokoro adapter with `af_heart`, lazy model loading, sentence-sized synthesis, cancellation, bounded cache, and a projection that speaks only top-level Elena text. Add faster-whisper push-to-talk/batched transcription with editable transcript before submission.
35. Drive the 2D face from actual audio amplitude and explicit listening/thinking/speaking/error states. Keep stable dimensions, accessible reduced-motion behavior, keyboard operation, readable activity drawers, and no technical log narration through TTS.
36. Test microphone denial, missing models, CPU-only inference, audio device changes, interrupted playback, voice cancellation, and text-only degradation without blocking the conversation runtime.

### Phase 8: Maintenance And World Refresh

37. Implement daily maintenance as a scheduled, transactional, reversible job: snapshot metadata, find duplicate/superseded/stale candidates, propose memory merges with provenance, compact completed task events into summaries, demote unused skills/tools, rebuild retrieval indexes, validate invariants, then commit or roll back.
38. V1 never automatically purges raw conversations, high-importance memories, evidence, approvals, or tool versions. Archival changes retrieval tier only; purge requires a separate explicit retention policy and user approval.
39. Implement opt-in world refresh by followed topic, source allowlist, cadence, and resource budget. Browser research produces dated source-backed candidates; it does not silently become personal memory or model context. Elena reports only material changes and allows dismiss/save/follow-up.
40. Add maintenance metrics: database/artifact size, active/dormant counts, duplicate candidates, index health, retrieval quality sample, prompt-budget distribution, job duration, and rollback count.

### Phase 9: Home-PC Integration And V1 Release

41. Push the public repository only after a clean-history secret/privacy scan. Clone fresh at home and follow the documented bootstrap without copying work-laptop caches or personal data.
42. Validate Docker Desktop/WSL2 containment and Playwright image first, then LM Studio streaming/tool-call compatibility, then Kokoro/Whisper/audio, and finally the packaged desktop/tray lifecycle. Record hardware, model, quantization, context limit, latency, memory, and failures in a local diagnostic bundle with redaction.
43. Run end-to-end acceptance scenarios: persistent chat/restart, compact context after large tool output, vague historical recall, clarification before an ambiguous destructive request, approved tool creation and same-conversation activation, contained script escape attempts, subagent intervention, crash/checkpoint recovery, voice/face cancellation, maintenance rollback, world-refresh review, and complete tray exit.
44. Fix integration defects in small branches with regression tests, produce a signed/tagged V1 build, publish checksums and setup/security limitations, and keep real-model/hardware tests as an explicit home release gate rather than unreliable GitHub CI jobs.

## Verification

1. Unit and property tests for canonical path policy, state transitions, prompt budget allocation, artifact references, ranking fusion, provenance/supersession, approval expiry/hash binding, event ordering, and maintenance invariants.
2. Contract tests run every provider/tool/voice/storage adapter against the same interfaces; fake adapters produce deterministic streams, failures, malformed tool calls, timeouts, and cancellations.
3. Integration tests exercise runtime restart, SQLite WAL concurrency, WebSocket reconnect/state sync, exact-once effect IDs, task resume, hot tool/skill reload, subagent interruption, and scheduler idempotency.
4. Security tests run only untrusted code in Docker and assert no access to repository, app data, credentials, host paths, Docker socket, or disallowed network. Test Windows junctions and shared-drive configuration explicitly at home.
5. Frontend tests cover chat, approvals, clarification, activity collapse, task intervention, settings/diagnostics, accessibility and speech projection; Playwright screenshots cover common desktop dimensions and the face/audio states.
6. Performance benchmarks track cold/warm startup, idle RAM, prompt tokens per turn, tool schema count, recall quality/latency over growing archives, event/artifact growth, Docker startup, first-token latency, TTS first audio, and STT completion.
7. Public-release checks include secret scanning, dependency/license review, generated-artifact scan, config/log redaction tests, clean-clone setup, Windows package smoke test, and confirmation that `conv.txt`, local databases, transcripts, recordings, workspace files and model artifacts are absent from release assets.

## Relevant Files

- `pyproject.toml` - Python workspace, dependencies, Ruff/Pyright/pytest configuration and package entry points.
- `apps/desktop/` - PySide6 lifecycle, tray, web view and packaging.
- `apps/ui/` - React application and UI tests.
- `src/elena/harness/` - immutable core and policy contracts.
- `src/elena/storage/` - SQLite schema, FTS recall, graph edges, artifacts and provenance.
- `src/elena/sandbox/` and `sandbox/` - Docker executor, profiles, images and containment tests.
- `src/elena/providers/` - fake and LM Studio adapters plus optional Copilot spike boundary.
- `src/elena/tools/`, `src/elena/skills/`, `src/elena/agents/` - controlled extension and delegation surfaces.
- `src/elena/voice/` - optional TTS/STT adapters and fakes.
- `.github/workflows/` - public CI and security checks.
- `docs/architecture.md`, `docs/threat-model.md`, `docs/home-setup.md`, `docs/privacy.md` - implementation and operating contracts.

## Decisions

- Chosen desktop stack: PySide6 host + embedded React/Vite UI + supervised Python runtime.
- Chosen untrusted execution policy: Docker is mandatory; without Docker, generated code and third-party tools are disabled.
- Chosen repository visibility: public. All personal state and secrets live outside the repository and are ignored/redacted by default.
- V1 is breadth-first but capability-gated. Every major concept has a working path; dangerous autonomy remains approval-bound and reversible.
- LM Studio is the primary real provider and is integrated/tested at home. The work laptop and CI use deterministic fakes.
- GitHub Copilot is a supported V1 provider through `agent-framework-github-copilot`; its provider-owned shell, file, URL, and MCP capabilities remain denied so Elena's harness and Docker policy stay authoritative.
- Provider selection is conversation-scoped and pinned; subagents inherit it unless a future explicit cross-provider policy is approved.
- SQLite is the authoritative local store. FTS5, relational graph edges, and optional local embeddings avoid premature standalone database services.
- Raw conversations are append-only ground truth in V1. Maintenance compacts derived working representations, not source history.
- Playwright/browser access is sandboxed separately from offline compute because internet access and filesystem access require different threat profiles.

## Deliberately Excluded From V1

- Elena modifying the harness, policy engine, supervisor, source repository, Docker profiles, or security configuration.
- Host-native execution of generated scripts, imported Python skills, arbitrary shell access, blanket approvals, or mounting the Docker socket.
- Automatic deletion of source conversations or important memories.
- Autonomous installation of system software, opening inbound ports, changing filesystem scope, changing providers mid-conversation, or silently routing data to cloud services.
- A production GitHub Copilot provider until an official supported integration and its containment/data implications are proven.
- Dedicated graph-database/vector-database services, continuous always-listening STT, fully autonomous web crawling, and unrestricted self-improvement.
