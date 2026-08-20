import json
from contextlib import suppress
from pathlib import Path
from typing import Protocol

import keyring
from pydantic import BaseModel, Field


class CredentialStore(Protocol):
    def get(self, name: str) -> str | None: ...

    def set(self, name: str, value: str | None) -> None: ...


class WindowsCredentialStore:
    service_name = "Elena"

    def get(self, name: str) -> str | None:
        return keyring.get_password(self.service_name, name)

    def set(self, name: str, value: str | None) -> None:
        if value:
            keyring.set_password(self.service_name, name, value)
            return
        with suppress(keyring.errors.PasswordDeleteError):
            keyring.delete_password(self.service_name, name)


class ProviderSettings(BaseModel):
    setup_complete: bool = False
    selected_provider: str = "fake"
    lmstudio_url: str = "http://127.0.0.1:1234/v1"
    lmstudio_model: str | None = None
    copilot_model: str | None = None


class PublicSettings(ProviderSettings):
    has_github_token: bool = False
    has_lmstudio_token: bool = False


class SaveSettingsRequest(BaseModel):
    selected_provider: str
    lmstudio_url: str = "http://127.0.0.1:1234/v1"
    lmstudio_model: str | None = None
    copilot_model: str | None = None
    github_token: str | None = None
    lmstudio_token: str | None = None


class TestProviderRequest(BaseModel):
    provider: str
    endpoint: str | None = None
    token: str | None = None


class ConnectionTestResult(BaseModel):
    ok: bool
    models: list[str] = Field(default_factory=list)
    error: str | None = None


class SettingsService:
    def __init__(
        self, data_dir: Path, credentials: CredentialStore | None = None
    ) -> None:
        self.data_dir = data_dir
        self.path = data_dir / "settings.json"
        self.credentials = credentials or WindowsCredentialStore()

    def load(self) -> ProviderSettings:
        if not self.path.is_file():
            return ProviderSettings()
        return ProviderSettings.model_validate_json(self.path.read_text(encoding="utf-8"))

    def public(self) -> PublicSettings:
        settings = self.load()
        return PublicSettings(
            **settings.model_dump(),
            has_github_token=bool(self.credentials.get("github_token")),
            has_lmstudio_token=bool(self.credentials.get("lmstudio_token")),
        )

    def save(self, request: SaveSettingsRequest) -> PublicSettings:
        if request.selected_provider not in {"lmstudio", "copilot"}:
            raise ValueError("Select LM Studio or GitHub Copilot")
        if request.selected_provider == "lmstudio" and not request.lmstudio_model:
            raise ValueError("Select an LM Studio model")
        if request.selected_provider == "copilot" and not request.copilot_model:
            raise ValueError("Select a GitHub Copilot model")

        self.data_dir.mkdir(parents=True, exist_ok=True)
        settings = ProviderSettings(
            setup_complete=True,
            selected_provider=request.selected_provider,
            lmstudio_url=request.lmstudio_url.rstrip("/"),
            lmstudio_model=request.lmstudio_model,
            copilot_model=request.copilot_model,
        )
        temporary_path = self.path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(settings.model_dump(), indent=2), encoding="utf-8"
        )
        temporary_path.replace(self.path)
        if request.github_token is not None:
            self.credentials.set("github_token", request.github_token.strip() or None)
        if request.lmstudio_token is not None:
            self.credentials.set("lmstudio_token", request.lmstudio_token.strip() or None)
        return self.public()

    def secret(self, name: str) -> str | None:
        return self.credentials.get(name)