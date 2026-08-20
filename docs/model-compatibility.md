# Provider Compatibility

Verified on the home PC on 2026-08-20. These are observations, not model-name
assumptions. Re-run `uv run elena-discover-models` after changing a model, quantization,
prompt template, or LM Studio version. The detailed local report is written to
`%LOCALAPPDATA%\Elena\model-capabilities.json` and is not committed.

## GitHub Copilot

- Integration: `agent-framework-github-copilot` 1.0.2 with the official Copilot SDK.
- Authentication: existing Copilot CLI login successfully listed 23 models without a PAT.
  A supplied token is supported and stored in Windows Credential Manager.
- Live turn: `gpt-5-mini` returned the exact expected response through
  `GitHubCopilotAgent`.
- Safety: Elena passes no tools and rejects every provider-owned permission request with
  `PermissionDecisionUserNotAvailable`. Copilot's shell, files, URLs, and MCP execution do
  not bypass Elena's harness or Docker boundary.

## LM Studio

Endpoint: `http://127.0.0.1:1234/v1`. Five generative models were tested with deterministic
text, structured-tool, and one-pixel image probes.

| Model | Text | Structured tool call | Image | Reasoning metadata |
| --- | --- | --- | --- | --- |
| `openai/gpt-oss-20b` | Pass | Pass | Rejected | Separate |
| `qwen/qwen3.5-9b` | Reasoning-only at 96 tokens | Pass | Accepted, reasoning-only at 96 tokens | Separate |
| `qwen3.5-9b-uncensored-hauhaucs-aggressive` | Reasoning-only at 96 tokens | Pass | Rejected | Separate |
| `qwen/qwen2.5-coder-14b` | Pass | Text-form tool markup only | Rejected | None |
| `thedrummer_cydonia-24b-v4.3` | Pass | Did not call tool | Rejected | None |

`openai/gpt-oss-20b` is the best currently verified default for Elena's text/tool path.
`qwen/qwen3.5-9b` is the only installed model that accepted image input, but its output
budget must be high enough to finish reasoning and produce user-visible content. Elena
never substitutes private reasoning text for a missing final answer; it returns an
actionable model-configuration error instead.
