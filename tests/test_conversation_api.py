from pathlib import Path

from fastapi.testclient import TestClient

from elena.runtime import create_app, default_data_dir


def test_data_directory_can_be_overridden(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ELENA_DATA_DIR", str(tmp_path))

    assert default_data_dir() == tmp_path


def test_conversation_turn_persists_across_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "elena.db"
    with TestClient(create_app(database_path)) as client:
        created = client.post(
            "/api/conversations", json={"title": "First test", "provider": "fake"}
        )
        assert created.status_code == 201
        conversation_id = created.json()["id"]

        turn = client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "Please remember the architecture boundary."},
        )
        assert turn.status_code == 200
        assert turn.json()["conversation"]["state"] == "completed"
        assert "no external model was contacted" in turn.json()["reply"]["content"]

    with TestClient(create_app(database_path)) as reopened_client:
        persisted = reopened_client.get(f"/api/conversations/{conversation_id}")
        assert persisted.status_code == 200
        messages = persisted.json()["messages"]
        assert [message["role"] for message in messages] == ["user", "assistant"]
        assert messages[0]["content"] == "Please remember the architecture boundary."
        assert messages[1]["spoken"] is True


def test_unknown_conversation_returns_not_found(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "elena.db")) as client:
        response = client.get("/api/conversations/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


def test_runtime_serves_built_ui_without_shadowing_api(tmp_path: Path) -> None:
    ui_dir = tmp_path / "ui"
    ui_dir.mkdir()
    (ui_dir / "index.html").write_text("<h1>Elena</h1>", encoding="utf-8")

    with TestClient(create_app(tmp_path / "elena.db", ui_dir)) as client:
        page = client.get("/")
        health = client.get("/health")

    assert page.status_code == 200
    assert "<h1>Elena</h1>" in page.text
    assert health.json() == {"status": "ok", "provider": "fake"}
