import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "test.db"))
    main.init_db()
    return TestClient(main.app)


def register_and_login(client, username, password="secret123"):
    client.post("/register", json={"username": username, "password": password})
    resp = client.post("/login", json={"username": username, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_register_duplicate_username(client):
    body = {"username": "alice", "password": "secret123"}
    assert client.post("/register", json=body).status_code == 201
    assert client.post("/register", json=body).status_code == 409


def test_login_wrong_password(client):
    client.post("/register", json={"username": "alice", "password": "secret123"})
    resp = client.post("/login", json={"username": "alice", "password": "wrong"})
    assert resp.status_code == 401


def test_notes_require_token(client):
    assert client.get("/notes").status_code in (401, 403)


def test_create_and_list_note(client):
    headers = register_and_login(client, "alice")
    resp = client.post(
        "/notes", json={"title": "T", "content": "C"}, headers=headers
    )
    assert resp.status_code == 201
    notes = client.get("/notes", headers=headers).json()
    assert len(notes) == 1
    assert notes[0]["title"] == "T"


def test_user_cannot_see_other_users_note(client):
    alice = register_and_login(client, "alice")
    bob = register_and_login(client, "bob")
    note = client.post(
        "/notes", json={"title": "T", "content": "C"}, headers=alice
    ).json()
    assert client.get("/notes", headers=bob).json() == []
    assert client.get(f"/notes/{note['id']}", headers=bob).status_code == 404


def test_update_and_delete_note(client):
    headers = register_and_login(client, "alice")
    note = client.post(
        "/notes", json={"title": "Old", "content": "C"}, headers=headers
    ).json()
    resp = client.put(
        f"/notes/{note['id']}",
        json={"title": "New", "content": "C"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"
    assert client.delete(f"/notes/{note['id']}", headers=headers).status_code == 204
    assert client.get(f"/notes/{note['id']}", headers=headers).status_code == 404


def test_missing_title_is_rejected(client):
    headers = register_and_login(client, "alice")
    resp = client.post("/notes", json={"content": "C"}, headers=headers)
    assert resp.status_code == 422
