from pathlib import Path

import pytest

from elena.settings import SaveSettingsRequest, SettingsService


class MemoryCredentials:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, name: str) -> str | None:
        return self.values.get(name)

    def set(self, name: str, value: str | None) -> None:
        if value is None:
            self.values.pop(name, None)
        else:
            self.values[name] = value


def test_settings_keep_secrets_out_of_json_and_preserve_blank_edits(
    tmp_path: Path,
) -> None:
    credentials = MemoryCredentials()
    service = SettingsService(tmp_path, credentials)

    saved = service.save(
        SaveSettingsRequest(
            selected_provider="copilot",
            copilot_model="gpt-test",
            github_token="secret-token",
        )
    )

    assert saved.has_github_token is True
    assert "secret-token" not in (tmp_path / "settings.json").read_text(encoding="utf-8")

    service.save(
        SaveSettingsRequest(
            selected_provider="lmstudio",
            lmstudio_model="local-model",
            github_token=None,
        )
    )

    assert credentials.get("github_token") == "secret-token"


def test_selected_provider_requires_a_model(tmp_path: Path) -> None:
    service = SettingsService(tmp_path, MemoryCredentials())

    with pytest.raises(ValueError, match="LM Studio model"):
        service.save(SaveSettingsRequest(selected_provider="lmstudio"))