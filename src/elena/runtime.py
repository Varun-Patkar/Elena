import asyncio
import os
from pathlib import Path
from uuid import UUID

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles

from elena.contracts import (
    Conversation,
    CreateConversationRequest,
    SendMessageRequest,
    TurnResponse,
)
from elena.providers import CopilotProvider, LMStudioProvider, ProviderRegistry
from elena.service import ConversationNotFoundError, ConversationService
from elena.settings import (
    ConnectionTestResult,
    PublicSettings,
    SaveSettingsRequest,
    SettingsService,
    TestProviderRequest,
)
from elena.storage import ConversationStore


def default_data_dir() -> Path:
    configured = os.getenv("ELENA_DATA_DIR")
    if configured:
        return Path(configured)
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Elena"
    return Path.home() / ".elena"


def default_ui_dir() -> Path:
    configured = os.getenv("ELENA_UI_DIR")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "apps" / "ui" / "dist"


def create_app(
    database_path: Path | None = None,
    ui_dir: Path | None = None,
    settings_service: SettingsService | None = None,
) -> FastAPI:
    path = database_path or default_data_dir() / "elena.db"
    settings = settings_service or SettingsService(path.parent)
    providers = ProviderRegistry(settings)
    service = ConversationService(ConversationStore(path), providers)
    app = FastAPI(title="Elena Runtime", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "provider": providers.selected_name()}

    @app.get("/api/settings", response_model=PublicSettings)
    async def get_settings() -> PublicSettings:
        return settings.public()

    @app.post("/api/settings/test", response_model=ConnectionTestResult)
    async def test_provider(request: TestProviderRequest) -> ConnectionTestResult:
        if request.provider == "lmstudio":
            endpoint = request.endpoint or "http://127.0.0.1:1234/v1"
            token = request.token or settings.secret("lmstudio_token")
            return await LMStudioProvider.test_connection(endpoint, token)
        if request.provider == "copilot":
            token = request.token or settings.secret("github_token")
            try:
                return await asyncio.wait_for(
                    CopilotProvider.test_connection(token, settings.data_dir), timeout=30
                )
            except TimeoutError:
                return ConnectionTestResult(
                    ok=False, error="GitHub Copilot did not respond within 30 seconds"
                )
        raise HTTPException(status_code=400, detail="Unknown provider")

    @app.put("/api/settings", response_model=PublicSettings)
    async def save_settings(request: SaveSettingsRequest) -> PublicSettings:
        try:
            return settings.save(request)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.post(
        "/api/conversations",
        response_model=Conversation,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_conversation(request: CreateConversationRequest) -> Conversation:
        provider = (
            providers.selected_name() if request.provider == "selected" else request.provider
        )
        try:
            return service.create_conversation(request.title, provider)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.get("/api/conversations/{conversation_id}", response_model=Conversation)
    async def get_conversation(conversation_id: UUID) -> Conversation:
        try:
            return service.get_conversation(conversation_id)
        except ConversationNotFoundError as error:
            raise HTTPException(
                status_code=404, detail="Conversation not found"
            ) from error

    @app.post(
        "/api/conversations/{conversation_id}/messages", response_model=TurnResponse
    )
    async def send_message(
        conversation_id: UUID, request: SendMessageRequest
    ) -> TurnResponse:
        try:
            return await service.send_message(conversation_id, request.content)
        except ConversationNotFoundError as error:
            raise HTTPException(
                status_code=404, detail="Conversation not found"
            ) from error

    static_dir = ui_dir or default_ui_dir()
    if (static_dir / "index.html").is_file():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="ui")

    return app


app = create_app()


def main() -> None:
    uvicorn.run("elena.runtime:app", host="127.0.0.1", port=8765, reload=False)


if __name__ == "__main__":
    main()
