from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Protocol

import httpx

from elena.contracts import Message, Role
from elena.settings import ConnectionTestResult, ProviderSettings, SettingsService


def deny_copilot_permission(request: object, invocation: dict[str, str]) -> object:
    del request, invocation
    from copilot.generated.rpc import PermissionDecisionUserNotAvailable

    return PermissionDecisionUserNotAvailable()


class ChatProvider(Protocol):
    name: str

    async def stream(self, messages: Sequence[Message]) -> AsyncIterator[str]: ...


class FakeProvider:
    """Deterministic provider used for local development and CI."""

    name = "fake"

    async def stream(self, messages: Sequence[Message]) -> AsyncIterator[str]:
        latest = next(
            message for message in reversed(messages) if message.role == Role.USER
        )
        response = (
            "Certainly. I have recorded your request: "
            f'"{latest.content.strip()}" '
            "The development provider is active, so no external model was contacted."
        )
        for word in response.split():
            yield f"{word} "


class LMStudioProvider:
    name = "lmstudio"

    def __init__(self, base_url: str, model: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.token = token

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @classmethod
    async def test_connection(
        cls, base_url: str, token: str | None = None
    ) -> ConnectionTestResult:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(
                    f"{base_url.rstrip('/')}/models",
                    headers={"Authorization": f"Bearer {token}"} if token else {},
                )
                response.raise_for_status()
                models = sorted(
                    item["id"]
                    for item in response.json().get("data", [])
                    if item.get("id") and "embed" not in item["id"].lower()
                )
            return ConnectionTestResult(ok=True, models=models)
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            return ConnectionTestResult(ok=False, error=str(error))

    async def stream(self, messages: Sequence[Message]) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Elena, a concise and capable personal assistant. Return "
                        "only the final user-facing answer. Never include analysis, planning, "
                        "or hidden reasoning in content."
                    ),
                },
                *[
                    {"role": message.role.value, "content": message.content}
                    for message in messages
                ],
            ],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", headers=self.headers, json=payload
            )
            response.raise_for_status()
            choice = response.json()["choices"][0]["message"]
            content = choice.get("content") or ""
        if not content.strip():
            if choice.get("reasoning_content") or choice.get("reasoning"):
                raise RuntimeError(
                    "The model used its response budget for private reasoning and returned "
                    "no answer. Increase the model output limit in LM Studio or choose a "
                    "model that completed Elena's capability probe."
                )
            raise RuntimeError("The model returned no assistant text")
        yield content


class CopilotProvider:
    name = "copilot"

    def __init__(
        self, model: str, token: str | None, data_dir: Path
    ) -> None:
        self.model = model
        self.token = token
        self.data_dir = data_dir

    @classmethod
    async def test_connection(
        cls, token: str | None, data_dir: Path
    ) -> ConnectionTestResult:
        try:
            from copilot import CopilotClient

            client = CopilotClient(
                github_token=token or None,
                base_directory=str(data_dir / "copilot"),
            )
            await client.start()
            try:
                models = await client.list_models()
                model_ids = sorted(
                    str(getattr(model, "id", None) or getattr(model, "name", ""))
                    for model in models
                )
            finally:
                await client.stop()
            return ConnectionTestResult(ok=True, models=[item for item in model_ids if item])
        except (ImportError, OSError, RuntimeError, TimeoutError) as error:
            return ConnectionTestResult(ok=False, error=str(error))

    async def stream(self, messages: Sequence[Message]) -> AsyncIterator[str]:
        try:
            from agent_framework.github import GitHubCopilotAgent, GitHubCopilotOptions
            from copilot import CopilotClient
        except ImportError as error:
            raise RuntimeError(
                "GitHub Copilot support is not installed. Run setup again."
            ) from error

        client = CopilotClient(
            github_token=self.token or None,
            base_directory=str(self.data_dir / "copilot"),
        )
        agent = GitHubCopilotAgent(
            instructions=(
                "You are Elena, a concise and capable personal assistant. "
                "Return only the response intended for the user."
            ),
            client=client,
            tools=[],
            default_options=GitHubCopilotOptions(
                model=self.model,
                timeout=120,
                on_permission_request=deny_copilot_permission,
            ),
        )
        prompt = "\n".join(
            f"{message.role.value}: {message.content}" for message in messages
        )
        async with agent:
            async for chunk in agent.run(prompt, stream=True):
                if chunk.text:
                    yield chunk.text


class ProviderRegistry:
    def __init__(self, settings: SettingsService) -> None:
        self.settings = settings

    def selected_name(self) -> str:
        return self.settings.load().selected_provider

    def resolve(self, name: str) -> ChatProvider:
        if name == "fake":
            return FakeProvider()
        config: ProviderSettings = self.settings.load()
        if name == "lmstudio" and config.lmstudio_model:
            return LMStudioProvider(
                config.lmstudio_url,
                config.lmstudio_model,
                self.settings.secret("lmstudio_token"),
            )
        if name == "copilot" and config.copilot_model:
            return CopilotProvider(
                config.copilot_model,
                self.settings.secret("github_token"),
                self.settings.data_dir,
            )
        raise ValueError(f"Provider is not configured: {name}")
