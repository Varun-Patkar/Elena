import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from elena.contracts import Message, Role
from elena.providers import LMStudioProvider, deny_copilot_permission


def test_copilot_provider_denies_native_permission_requests() -> None:
    from copilot.generated.rpc import PermissionDecisionUserNotAvailable

    decision = deny_copilot_permission(object(), {})

    assert isinstance(decision, PermissionDecisionUserNotAvailable)


@pytest.mark.asyncio
async def test_lmstudio_discovery_excludes_embedding_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_class = httpx.AsyncClient

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        return httpx.Response(
            200,
            json={"data": [{"id": "chat-model"}, {"id": "text-embedding-model"}]},
        )

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: client_class(transport=httpx.MockTransport(handler), **kwargs),
    )

    result = await LMStudioProvider.test_connection("http://example.test/v1")

    assert result.ok is True
    assert result.models == ["chat-model"]


@pytest.mark.asyncio
async def test_lmstudio_does_not_expose_reasoning_as_the_answer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    del tmp_path
    client_class = httpx.AsyncClient

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        payload = json.loads(request.content)
        assert payload["messages"][0]["role"] == "system"
        assert "Never include analysis" in payload["messages"][0]["content"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "reasoning_content": "private reasoning",
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: client_class(transport=httpx.MockTransport(handler), **kwargs),
    )
    provider = LMStudioProvider("http://example.test/v1", "thinking-model")
    message = Message(conversation_id=uuid4(), role=Role.USER, content="Hello")

    with pytest.raises(RuntimeError, match="private reasoning"):
        _ = [chunk async for chunk in provider.stream([message])]