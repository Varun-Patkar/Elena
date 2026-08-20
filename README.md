# Elena

Elena is a Windows-first, local personal agent built around an immutable harness and a
strictly bounded mutable workspace. The current implementation is an early vertical slice
with secure provider setup, LM Studio and GitHub Copilot model discovery, persistent
conversations, explicit task states, and a Windows tray host that opens a browser UI.

The complete implementation plan is in [plan.md](plan.md).

> [!IMPORTANT]
> This repository currently contains the first development slice, not the complete system
> described in the plan. Docker tool execution, live Kokoro/faster-whisper controls, memory,
> recall, skills, and subagents are not wired into conversations yet. One-time setup installs
> and warms the voice models so later voice integration needs no model download.

## Current Slice

- Persistent SQLite conversations and explicit task states
- LM Studio and GitHub Copilot providers with tested model discovery
- Credentials in Windows Credential Manager, never in repository settings files
- FastAPI conversation API and production UI hosting
- React chat UI with an audio-ready face and expandable activity
- PySide6 tray host, normal browser UI, `Ctrl+F4` open hotkey, and full exit
- One-time setup for Kokoro `af_heart` and faster-whisper `small.en`

## Backend Development

```powershell
uv sync --extra dev
uv run pytest
uv run elena-runtime
```

The runtime listens on `127.0.0.1:8765` by default. Set `ELENA_DATA_DIR` to choose where
local runtime state is stored. Personal data and model artifacts must never be committed.

## UI Development

Start the runtime, then run the Vite development server in another terminal:

```powershell
Set-Location apps/ui
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/health` and `/api` to the local runtime.

To create the production assets served directly by FastAPI:

```powershell
Set-Location apps/ui
npm run build
Set-Location ../..
uv run elena-runtime
```

The built interface is then available at `http://127.0.0.1:8765`.

## Desktop Shell

The desktop dependency is optional so the harness and CI remain lightweight:

```powershell
uv sync --extra dev --extra providers --extra desktop
uv run elena-desktop
```

The host opens Elena in your default browser and remains in the system tray. Right-click the
tray icon for **Open Elena** or **Close Elena**. `Ctrl+F4` opens another Elena tab. Closing
Elena stops the runtime and removes only Docker containers labeled as Elena-managed. Browser
security does not allow Elena to forcibly close existing tabs; those tabs show disconnected.

## Home Setup

Run the one-time setup from PowerShell:

```powershell
.\Setup-Elena.ps1
```

After it completes, double-click `Start-Elena.cmd`. First startup asks for LM Studio or
GitHub Copilot, tests the connection, and lists real models before confirmation. LM Studio
defaults to the local endpoint but accepts a remote endpoint and optional token. GitHub
Copilot can use an existing Copilot login or an explicit token. Setup does not prompt again
after confirmation; use **Settings** to reconnect or change providers.

See [docs/model-compatibility.md](docs/model-compatibility.md) for verified model behavior
and the command used to repeat LM Studio discovery.

## Test On A Home Windows PC

### 1. Install prerequisites

Install these before cloning:

- [Git](https://git-scm.com/download/win)
- [Python 3.12](https://www.python.org/downloads/)
- [Node.js 22 LTS](https://nodejs.org/)
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

Confirm they are available in a new PowerShell window:

```powershell
git --version
python --version
node --version
npm --version
uv --version
```

Python must report version 3.12 or newer. LM Studio and Docker are not required for the
current slice.

### 2. Clone and install

```powershell
git clone https://github.com/Varun-Patkar/Elena.git
Set-Location Elena
uv sync --extra dev --extra desktop

Set-Location apps/ui
npm ci
npm run build
Set-Location ../..
```

### 3. Run automated checks

```powershell
uv run pytest
uv run ruff check src tests

Set-Location apps/ui
npm run lint
npm run build
Set-Location ../..
```

Expected result: all Python tests pass and both frontend commands complete without errors.

### 4. Test the browser version

The production UI built in step 2 is served by the Python runtime:

```powershell
uv run elena-runtime
```

Open `http://127.0.0.1:8765` and send a message. Elena should answer with a deterministic
development response saying that no external model was contacted. Press `Ctrl+C` in
PowerShell when finished.

For frontend hot reload, use two PowerShell windows instead:

```powershell
# Window 1, from the repository root
uv run elena-runtime
```

```powershell
# Window 2
Set-Location apps/ui
npm run dev
```

Then open `http://127.0.0.1:5173`.

### 5. Test persistence

1. Send a message in the browser.
2. Stop and restart `uv run elena-runtime`.
3. The SQLite database should remain under `%LOCALAPPDATA%\Elena\elena.db`.
4. Existing API conversations remain persisted, although conversation-list/resume UI is not
   implemented yet.

To keep test data inside a disposable folder instead:

```powershell
$env:ELENA_DATA_DIR = "$PWD\runtime-data"
uv run elena-runtime
```

The `runtime-data` directory is ignored by Git.

### 6. Test the desktop and tray shell

Build the UI first, then run:

```powershell
uv run elena-desktop
```

Check the following:

- The Elena window opens and the chat accepts a message.
- Closing the window hides it instead of terminating Elena.
- Clicking the tray icon reopens the window.
- **Restart runtime** reconnects the interface.
- **Exit completely** removes the tray icon and terminates the runtime process.

### 7. Record home-PC findings

When reporting a problem, include:

```powershell
python --version
node --version
uv --version
git rev-parse HEAD
```

Also include the failing command and its output. Do not upload `%LOCALAPPDATA%\Elena`,
databases, transcripts, recordings, `.env` files, model files, or personal workspace data.

### Troubleshooting

- **`uv` is not recognized:** close and reopen PowerShell after installing it.
- **Port 8765 is busy:** stop the other Elena runtime before starting another one.
- **Blank desktop window:** run `npm ci` and `npm run build` in `apps/ui`, then restart Elena.
- **PySide6/WebEngine import error:** rerun `uv sync --extra desktop`.
- **Windows Firewall prompt:** Elena currently binds only to `127.0.0.1`; do not expose it to
  the public network.

## Current API

- `GET /health`
- `POST /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `POST /api/conversations/{conversation_id}/messages`

## Verification

```powershell
uv run pytest
Set-Location apps/ui
npm run lint
npm run build
```
