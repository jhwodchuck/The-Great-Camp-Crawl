"""Router-level integration tests for the research-ui backend."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Point to the backend directory
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "apps", "research-ui", "backend")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

# Use temp filesystem locations so tests never touch repo state.
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
_tmp_export_dir = tempfile.TemporaryDirectory()

os.environ["RESEARCH_UI_DB"] = _tmp_db.name
os.environ["RESEARCH_UI_EXPORT_DIR"] = _tmp_export_dir.name

import pytest
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm

import models
import schemas
from auth import get_current_user, require_parent
from database import Base, SessionLocal, engine
from main import health
from routers import answers as answers_router
from routers import auth as auth_router
from routers import camps as camps_router
from routers import contributions as contributions_router
from routers import evidence as evidence_router
from routers import export as export_router
from routers import missions as missions_router
from routers import reviews as reviews_router


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    export_dir = Path(_tmp_export_dir.name)
    for artifact in export_dir.glob("*"):
        artifact.unlink()

    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def register_user(
    db,
    username: str,
    password: str = "testpass123",
    role: models.UserRole = models.UserRole.parent,
    parent_invite_code: str | None = None,
):
    return auth_router.register(
        schemas.UserCreate(
            username=username,
            display_name=f"User {username}",
            password=password,
            role=role,
            parent_invite_code=parent_invite_code,
        ),
        db,
    )


def login_user(db, username: str, password: str):
    form = OAuth2PasswordRequestForm(
        grant_type="password",
        username=username,
        password=password,
        scope="",
        client_id=None,
        client_secret=None,
    )
    return auth_router.login(form, db)


def token_user(db, token):
    return get_current_user(token.access_token, db)


def test_health():
    assert health() == {"status": "ok"}


def test_register_and_login(db):
    token = register_user(db, "parent_user_1")
    assert token.access_token

    with pytest.raises(HTTPException) as exc:
        register_user(db, "parent_user_1")
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        register_user(db, "parent_user_2", role=models.UserRole.parent)
    assert exc.value.status_code == 403

    login_token = login_user(db, "parent_user_1", "testpass123")
    assert login_token.user.username == "parent_user_1"


def test_register_options_reflect_parent_bootstrap_rules(db):
    initial = auth_router.register_options(db)
    assert initial.parent_self_signup_enabled is True
    assert initial.bootstrap_parent_configured is False

    register_user(db, "options_parent")

    after_parent = auth_router.register_options(db)
    assert after_parent.parent_self_signup_enabled is False
    assert after_parent.bootstrap_parent_configured is False


def test_me_endpoint(db):
    token = register_user(db, "parent_me_user")
    current_user = token_user(db, token)
    me = auth_router.me(current_user)
    assert me.username == "parent_me_user"
    assert me.role == models.UserRole.parent


def test_login_bad_password(db):
    register_user(db, "login_test_user")

    with pytest.raises(HTTPException) as exc:
        login_user(db, "login_test_user", "wrong")
    assert exc.value.status_code == 401


def test_missions_crud(db):
    parent = token_user(db, register_user(db, "mission_parent"))
    child = token_user(db, register_user(db, "mission_child", role=models.UserRole.child))

    mission = missions_router.create_mission(
        schemas.MissionCreate(
            title="Find Maine Camps",
            description="Research overnight camps in Maine",
            region="ME",
            country="US",
        ),
        db,
        parent,
    )
    assert mission.title == "Find Maine Camps"

    missions = missions_router.list_missions(db, child)
    assert any(item.id == mission.id for item in missions)

    with pytest.raises(HTTPException) as exc:
        require_parent(child)
    assert exc.value.status_code == 403

    updated = missions_router.update_mission(
        mission.id,
        schemas.MissionUpdate(title="Updated Maine Camps"),
        db,
        parent,
    )
    assert updated.title == "Updated Maine Camps"

    missions_router.delete_mission(mission.id, db, parent)
    assert missions_router.list_missions(db, parent) == []


def test_contribution_lifecycle(db):
    parent = token_user(db, register_user(db, "contrib_parent"))
    child = token_user(db, register_user(db, "contrib_child", role=models.UserRole.child))

    mission = missions_router.create_mission(
        schemas.MissionCreate(title="Test Mission", description="desc"),
        db,
        parent,
    )

    contribution = contributions_router.create_contribution(
        schemas.ContributionCreate(
            mission_id=mission.id,
            camp_name="Camp Happy Trails",
            website_url="https://camphappytrails.example.com",
            country="US",
            region="VT",
            city="Stowe",
            overnight_confirmed="yes",
            notes="Looks great!",
        ),
        db,
        child,
    )
    assert contribution.status == models.ContributionStatus.draft

    updated = contributions_router.update_contribution(
        contribution.id,
        schemas.ContributionUpdate(city="Burlington"),
        db,
        child,
    )
    assert updated.city == "Burlington"

    evidence = evidence_router.add_evidence(
        contribution.id,
        schemas.EvidenceCreate(
            url="https://camphappytrails.example.com/about",
            snippet="Campers sleep in cabins under the stars every night.",
            capture_notes="From the About page",
        ),
        db,
        child,
    )
    assert evidence.id

    answers = answers_router.upsert_answers(
        contribution.id,
        [
            schemas.AnswerUpsert(
                question_key="overnight_evidence",
                answer_text="Campers sleep in cabins every night.",
            ),
            schemas.AnswerUpsert(
                question_key="why_interesting",
                answer_text="They have a lake and waterslide!",
            ),
        ],
        db,
        child,
    )
    assert len(answers) == 2

    submitted = contributions_router.submit_contribution(contribution.id, db, child)
    assert submitted.status == models.ContributionStatus.submitted

    with pytest.raises(HTTPException) as exc:
        contributions_router.update_contribution(
            contribution.id,
            schemas.ContributionUpdate(city="Montpelier"),
            db,
            child,
        )
    assert exc.value.status_code == 409

    queue = reviews_router.review_queue(db, parent)
    assert any(item.id == contribution.id for item in queue)

    review = reviews_router.post_review(
        contribution.id,
        schemas.ReviewCreate(
            action=models.ReviewAction.approve,
            notes="Great find! Well documented.",
        ),
        db,
        parent,
    )
    assert review.action == models.ReviewAction.approve

    approved = contributions_router.get_contribution(contribution.id, db, parent)
    assert approved.status == models.ContributionStatus.approved

    export_result = export_router.promote_contribution(contribution.id, db, parent)
    assert "contrib-" in export_result.artifact_path
    assert export_result.storage_kind == "database+file"
    assert export_result.exported_at


def test_contribution_changes_requested_flow(db):
    parent = token_user(db, register_user(db, "cr_parent"))
    child = token_user(db, register_user(db, "cr_child", role=models.UserRole.child))

    mission = missions_router.create_mission(
        schemas.MissionCreate(title="CR Mission"),
        db,
        parent,
    )
    contribution = contributions_router.create_contribution(
        schemas.ContributionCreate(mission_id=mission.id, camp_name="Camp Needs Work"),
        db,
        child,
    )

    contributions_router.submit_contribution(contribution.id, db, child)

    review = reviews_router.post_review(
        contribution.id,
        schemas.ReviewCreate(
            action=models.ReviewAction.request_changes,
            notes="Please add more evidence of overnight stays.",
        ),
        db,
        parent,
    )
    assert review.action == models.ReviewAction.request_changes

    reloaded = contributions_router.get_contribution(contribution.id, db, child)
    assert reloaded.status == models.ContributionStatus.changes_requested

    updated = contributions_router.update_contribution(
        contribution.id,
        schemas.ContributionUpdate(notes="Added more evidence."),
        db,
        child,
    )
    assert updated.notes == "Added more evidence."

    resubmitted = contributions_router.submit_contribution(contribution.id, db, child)
    assert resubmitted.status == models.ContributionStatus.submitted


def test_child_cannot_access_other_childs_contribution(db):
    parent = token_user(db, register_user(db, "iso_parent"))
    child1 = token_user(db, register_user(db, "iso_child1", role=models.UserRole.child))
    child2 = token_user(db, register_user(db, "iso_child2", role=models.UserRole.child))

    mission = missions_router.create_mission(
        schemas.MissionCreate(title="Iso Mission"),
        db,
        parent,
    )
    contribution = contributions_router.create_contribution(
        schemas.ContributionCreate(mission_id=mission.id, camp_name="Child1 Camp"),
        db,
        child1,
    )

    with pytest.raises(HTTPException) as exc:
        contributions_router.get_contribution(contribution.id, db, child2)
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        contributions_router.update_contribution(
            contribution.id,
            schemas.ContributionUpdate(notes="hacked"),
            db,
            child2,
        )
    assert exc.value.status_code == 403


def test_only_parent_can_review(db):
    parent = token_user(db, register_user(db, "rev_parent"))
    child = token_user(db, register_user(db, "rev_child", role=models.UserRole.child))

    mission = missions_router.create_mission(
        schemas.MissionCreate(title="Rev Mission"),
        db,
        parent,
    )
    contribution = contributions_router.create_contribution(
        schemas.ContributionCreate(mission_id=mission.id, camp_name="Camp to Review"),
        db,
        child,
    )
    contributions_router.submit_contribution(contribution.id, db, child)

    with pytest.raises(HTTPException) as exc:
        require_parent(child)
    assert exc.value.status_code == 403


def test_guided_questions_list(db):
    child = token_user(db, register_user(db, "q_child", role=models.UserRole.child))
    questions = answers_router.get_questions(child)
    assert len(questions) >= 6
    keys = [question["key"] for question in questions]
    assert "overnight_evidence" in keys
    assert "why_interesting" in keys


def test_camp_moderation_hides_excluded_records_from_public_reads(db):
    parent = token_user(db, register_user(db, "camp_parent"))

    camp = models.Camp(
        record_id="cand-us-test-not-a-camp",
        name="Medical Dosage Page",
        website_url="https://example.com/medical-dosage",
        draft_status="candidate_pending",
        source=models.CampSource.discovery_pipeline,
    )
    db.add(camp)
    db.commit()

    public_before = camps_router.list_camps(page=1, page_size=25, db=db)
    assert public_before.total == 1

    moderated = camps_router.moderate_camp(
        camp.record_id,
        schemas.CampModerationUpdate(
            is_excluded=True,
            reason="not_a_camp",
            notes="Clearly a medical article, not a youth camp.",
        ),
        db,
        parent,
    )
    assert moderated.is_excluded is True
    assert moderated.exclusion_reason == "not_a_camp"

    public_after = camps_router.list_camps(page=1, page_size=25, db=db)
    assert public_after.total == 0

    with pytest.raises(HTTPException) as exc:
        camps_router.get_camp(camp.record_id, db, None)
    assert exc.value.status_code == 404

    parent_view = camps_router.get_camp(camp.record_id, db, parent)
    assert parent_view.is_excluded is True

    restored = camps_router.moderate_camp(
        camp.record_id,
        schemas.CampModerationUpdate(is_excluded=False),
        db,
        parent,
    )
    assert restored.is_excluded is False
    assert camps_router.list_camps(page=1, page_size=25, db=db).total == 1
