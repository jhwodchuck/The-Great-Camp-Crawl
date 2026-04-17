"""Tests for the research-ui backend API."""
from __future__ import annotations

import os
import sys
import tempfile

# Point to the backend directory
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "apps", "research-ui", "backend")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

# Use a temp file-based SQLite DB for tests (avoids per-connection isolation in :memory:)
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["RESEARCH_UI_DB"] = _tmp_db.name

import pytest
from fastapi.testclient import TestClient

from main import app
from database import Base, engine

Base.metadata.create_all(bind=engine)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def register_and_login(username: str, password: str = "testpass123", role: str = "parent") -> str:
    resp = client.post("/api/auth/register", json={
        "username": username,
        "display_name": f"User {username}",
        "password": password,
        "role": role,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_and_login():
    token = register_and_login("parent_user_1")
    assert token

    # duplicate username is rejected
    resp = client.post("/api/auth/register", json={
        "username": "parent_user_1",
        "display_name": "Dup",
        "password": "abc",
        "role": "parent",
    })
    assert resp.status_code == 400


def test_me_endpoint():
    token = register_and_login("parent_me_user")
    resp = client.get("/api/auth/me", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "parent_me_user"
    assert data["role"] == "parent"


def test_login_bad_password():
    register_and_login("login_test_user")
    resp = client.post("/api/auth/login", data={"username": "login_test_user", "password": "wrong"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Mission tests
# ---------------------------------------------------------------------------


def test_missions_crud():
    parent_token = register_and_login("mission_parent")
    child_token = register_and_login("mission_child", role="child")

    # Parent creates mission
    resp = client.post("/api/missions/", json={
        "title": "Find Maine Camps",
        "description": "Research overnight camps in Maine",
        "region": "ME",
        "country": "US",
    }, headers=auth_headers(parent_token))
    assert resp.status_code == 201
    mission = resp.json()
    mid = mission["id"]
    assert mission["title"] == "Find Maine Camps"

    # Child can list missions
    resp = client.get("/api/missions/", headers=auth_headers(child_token))
    assert resp.status_code == 200
    assert any(m["id"] == mid for m in resp.json())

    # Child cannot create missions
    resp = client.post("/api/missions/", json={
        "title": "Child attempt",
    }, headers=auth_headers(child_token))
    assert resp.status_code == 403

    # Parent can update
    resp = client.patch(f"/api/missions/{mid}", json={"title": "Updated Maine Camps"}, headers=auth_headers(parent_token))
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Maine Camps"

    # Parent can soft-delete
    resp = client.delete(f"/api/missions/{mid}", headers=auth_headers(parent_token))
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Contribution tests
# ---------------------------------------------------------------------------


def test_contribution_lifecycle():
    parent_token = register_and_login("contrib_parent")
    child_token = register_and_login("contrib_child", role="child")

    # Create mission
    mission_resp = client.post("/api/missions/", json={
        "title": "Test Mission",
        "description": "desc",
    }, headers=auth_headers(parent_token))
    mid = mission_resp.json()["id"]

    # Child creates a contribution
    resp = client.post("/api/contributions/", json={
        "mission_id": mid,
        "camp_name": "Camp Happy Trails",
        "website_url": "https://camphappytrails.example.com",
        "country": "US",
        "region": "VT",
        "city": "Stowe",
        "overnight_confirmed": "yes",
        "notes": "Looks great!",
    }, headers=auth_headers(child_token))
    assert resp.status_code == 201
    cid = resp.json()["id"]
    assert resp.json()["status"] == "draft"

    # Child can update the draft
    resp = client.patch(f"/api/contributions/{cid}", json={"city": "Burlington"}, headers=auth_headers(child_token))
    assert resp.status_code == 200
    assert resp.json()["city"] == "Burlington"

    # Child can add evidence
    resp = client.post(f"/api/contributions/{cid}/evidence/", json={
        "url": "https://camphappytrails.example.com/about",
        "snippet": "Campers sleep in cabins under the stars every night.",
        "capture_notes": "From the About page",
    }, headers=auth_headers(child_token))
    assert resp.status_code == 201
    ev_id = resp.json()["id"]

    # Child can answer guided questions
    resp = client.put(f"/api/contributions/{cid}/answers/", json=[
        {"question_key": "overnight_evidence", "answer_text": "Campers sleep in cabins every night."},
        {"question_key": "why_interesting", "answer_text": "They have a lake and waterslide!"},
    ], headers=auth_headers(child_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Child submits for review
    resp = client.post(f"/api/contributions/{cid}/submit", headers=auth_headers(child_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"

    # Child cannot edit after submission
    resp = client.patch(f"/api/contributions/{cid}", json={"city": "Montpelier"}, headers=auth_headers(child_token))
    assert resp.status_code == 409

    # Parent can see review queue
    resp = client.get("/api/reviews/queue", headers=auth_headers(parent_token))
    assert resp.status_code == 200
    assert any(c["id"] == cid for c in resp.json())

    # Parent approves
    resp = client.post(f"/api/reviews/{cid}", json={
        "action": "approve",
        "notes": "Great find! Well documented.",
    }, headers=auth_headers(parent_token))
    assert resp.status_code == 201
    assert resp.json()["action"] == "approve"

    # Contribution status is now approved
    resp = client.get(f"/api/contributions/{cid}", headers=auth_headers(parent_token))
    assert resp.json()["status"] == "approved"

    # Parent can promote to staging artifact
    resp = client.post(f"/api/export/{cid}", headers=auth_headers(parent_token))
    assert resp.status_code == 200
    result = resp.json()
    assert "contrib-" in result["artifact_path"]


def test_contribution_changes_requested_flow():
    parent_token = register_and_login("cr_parent")
    child_token = register_and_login("cr_child", role="child")

    mission_resp = client.post("/api/missions/", json={"title": "CR Mission"}, headers=auth_headers(parent_token))
    mid = mission_resp.json()["id"]

    contrib_resp = client.post("/api/contributions/", json={
        "mission_id": mid,
        "camp_name": "Camp Needs Work",
    }, headers=auth_headers(child_token))
    cid = contrib_resp.json()["id"]

    client.post(f"/api/contributions/{cid}/submit", headers=auth_headers(child_token))

    # Parent requests changes
    resp = client.post(f"/api/reviews/{cid}", json={
        "action": "request_changes",
        "notes": "Please add more evidence of overnight stays.",
    }, headers=auth_headers(parent_token))
    assert resp.status_code == 201

    # Contribution is back in changes_requested
    resp = client.get(f"/api/contributions/{cid}", headers=auth_headers(child_token))
    assert resp.json()["status"] == "changes_requested"

    # Child can now edit again
    resp = client.patch(f"/api/contributions/{cid}", json={"notes": "Added more evidence."}, headers=auth_headers(child_token))
    assert resp.status_code == 200

    # Child can resubmit
    resp = client.post(f"/api/contributions/{cid}/submit", headers=auth_headers(child_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"


def test_child_cannot_access_other_childs_contribution():
    parent_token = register_and_login("iso_parent")
    child1_token = register_and_login("iso_child1", role="child")
    child2_token = register_and_login("iso_child2", role="child")

    mission_resp = client.post("/api/missions/", json={"title": "Iso Mission"}, headers=auth_headers(parent_token))
    mid = mission_resp.json()["id"]

    contrib_resp = client.post("/api/contributions/", json={
        "mission_id": mid,
        "camp_name": "Child1 Camp",
    }, headers=auth_headers(child1_token))
    cid = contrib_resp.json()["id"]

    # child2 cannot read child1's contribution
    resp = client.get(f"/api/contributions/{cid}", headers=auth_headers(child2_token))
    assert resp.status_code == 403

    # child2 cannot update child1's contribution
    resp = client.patch(f"/api/contributions/{cid}", json={"notes": "hacked"}, headers=auth_headers(child2_token))
    assert resp.status_code == 403


def test_only_parent_can_review():
    parent_token = register_and_login("rev_parent")
    child_token = register_and_login("rev_child", role="child")

    mission_resp = client.post("/api/missions/", json={"title": "Rev Mission"}, headers=auth_headers(parent_token))
    mid = mission_resp.json()["id"]

    contrib_resp = client.post("/api/contributions/", json={
        "mission_id": mid,
        "camp_name": "Camp to Review",
    }, headers=auth_headers(child_token))
    cid = contrib_resp.json()["id"]
    client.post(f"/api/contributions/{cid}/submit", headers=auth_headers(child_token))

    # Child cannot post a review
    resp = client.post(f"/api/reviews/{cid}", json={"action": "approve"}, headers=auth_headers(child_token))
    assert resp.status_code == 403


def test_guided_questions_list():
    token = register_and_login("q_parent")
    parent_token = token
    child_token = register_and_login("q_child", role="child")

    mission_resp = client.post("/api/missions/", json={"title": "Q Mission"}, headers=auth_headers(parent_token))
    mid = mission_resp.json()["id"]
    contrib_resp = client.post("/api/contributions/", json={
        "mission_id": mid,
        "camp_name": "Q Camp",
    }, headers=auth_headers(child_token))
    cid = contrib_resp.json()["id"]

    resp = client.get(f"/api/contributions/{cid}/answers/questions", headers=auth_headers(child_token))
    assert resp.status_code == 200
    questions = resp.json()
    assert len(questions) >= 6
    keys = [q["key"] for q in questions]
    assert "overnight_evidence" in keys
    assert "why_interesting" in keys
