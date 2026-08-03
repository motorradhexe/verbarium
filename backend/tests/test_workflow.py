"""Status workflow tests. → D1, D5, D6, D19

The workflow is what makes an "Approved" badge mean anything, so these lean
on what must be refused.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Language, TermStatus
from app.models.enums import Role
from tests.conftest import patch_term


@pytest.fixture
def languages(db: Session) -> list[Language]:
    configured = [
        Language(code="de", name="German", position=0),
        Language(code="en", name="English", position=1),
    ]
    db.add_all(configured)
    db.commit()
    return configured


def make_concept(client: TestClient, term: str = "Espresso", **term_fields) -> dict:
    response = client.post(
        "/api/concepts",
        json={"terms": [{"language_code": "de", "term": term, **term_fields}]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def first_term(concept: dict) -> str:
    return concept["term_entries"][0]["id"]


def transition(client: TestClient, term_id: str, action: str, comment: str | None = None):
    return client.post(
        f"/api/terms/{term_id}/transition",
        json={"action": action, "comment": comment},
    )


def advance_to_review(client: TestClient, as_role, term_id: str) -> None:
    as_role(Role.EDITOR)
    assert transition(client, term_id, "submit").status_code == 200
    as_role(Role.REVIEWER)
    assert transition(client, term_id, "start_review").status_code == 200


class TestCreation:
    def test_an_entry_starts_as_a_draft(self, client: TestClient, as_role, languages):
        as_role(Role.EDITOR)

        concept = make_concept(client)

        assert concept["term_entries"][0]["status"] == TermStatus.DRAFT

    def test_a_contributor_may_create_a_proposal(self, client: TestClient, as_role, languages):
        """Submitting proposals is a Contributor's whole purpose."""
        as_role(Role.CONTRIBUTOR)

        assert client.post(
            "/api/concepts", json={"terms": [{"language_code": "de", "term": "Crema"}]}
        ).status_code == 201

    def test_a_viewer_may_not(self, client: TestClient, as_role, languages):
        as_role(Role.VIEWER)

        assert client.post("/api/concepts", json={}).status_code == 403

    def test_an_unconfigured_language_is_refused(self, client: TestClient, as_role, languages):
        as_role(Role.EDITOR)

        response = client.post(
            "/api/concepts", json={"terms": [{"language_code": "fr", "term": "Café"}]}
        )

        assert response.status_code == 422

    def test_a_failed_entry_leaves_no_concept_behind(
        self, client: TestClient, as_role, languages
    ):
        """The concept and its entries are created in one transaction."""
        as_role(Role.EDITOR)
        client.post("/api/concepts", json={"terms": [{"language_code": "fr", "term": "Café"}]})

        assert client.get("/api/concepts").json()["total"] == 0


class TestTransitions:
    def test_the_full_path_to_approved(self, client: TestClient, as_role, languages):
        as_role(Role.EDITOR)
        term_id = first_term(make_concept(client, definition="A short, strong coffee."))

        assert transition(client, term_id, "submit").json()["status"] == TermStatus.PROPOSED
        as_role(Role.REVIEWER)
        assert transition(client, term_id, "start_review").json()["status"] == TermStatus.IN_REVIEW
        as_role(Role.APPROVER)
        assert transition(client, term_id, "approve").json()["status"] == TermStatus.APPROVED

    def test_a_reviewer_cannot_approve(self, client: TestClient, as_role, languages):
        as_role(Role.EDITOR)
        term_id = first_term(make_concept(client, definition="A short, strong coffee."))
        advance_to_review(client, as_role, term_id)

        as_role(Role.REVIEWER)
        response = transition(client, term_id, "approve")

        assert response.status_code == 403

    def test_a_contributor_cannot_start_a_review(self, client: TestClient, as_role, languages):
        as_role(Role.CONTRIBUTOR)
        term_id = first_term(make_concept(client))
        transition(client, term_id, "submit")

        assert transition(client, term_id, "start_review").status_code == 403

    def test_a_draft_cannot_be_approved_directly(self, client: TestClient, as_role, languages):
        """No skipping the queue."""
        as_role(Role.EDITOR)
        term_id = first_term(make_concept(client, definition="A short, strong coffee."))

        as_role(Role.APPROVER)
        response = transition(client, term_id, "approve")

        assert response.status_code == 409

    def test_approval_requires_a_definition(self, client: TestClient, as_role, languages):
        """Optional to create, required to approve. → D5"""
        as_role(Role.EDITOR)
        term_id = first_term(make_concept(client))
        advance_to_review(client, as_role, term_id)

        as_role(Role.APPROVER)
        response = transition(client, term_id, "approve")

        assert response.status_code == 422
        assert "definition" in response.json()["detail"]

    def test_rejection_requires_a_reason(self, client: TestClient, as_role, languages):
        """→ D6"""
        as_role(Role.EDITOR)
        term_id = first_term(make_concept(client, definition="A short, strong coffee."))
        advance_to_review(client, as_role, term_id)

        as_role(Role.APPROVER)
        assert transition(client, term_id, "reject").status_code == 422
        assert transition(client, term_id, "reject", "Duplicate of Ristretto.").status_code == 200

    def test_requesting_changes_returns_the_entry_to_draft(
        self, client: TestClient, as_role, languages
    ):
        """The rework loop the original workflow lacked. → D6"""
        as_role(Role.EDITOR)
        term_id = first_term(make_concept(client, definition="A short, strong coffee."))
        advance_to_review(client, as_role, term_id)

        as_role(Role.REVIEWER)
        response = transition(client, term_id, "request_changes", "Definition covers the drink.")

        assert response.json()["status"] == TermStatus.DRAFT

    def test_the_reason_is_kept_as_a_comment(self, client: TestClient, as_role, languages):
        as_role(Role.EDITOR)
        term_id = first_term(make_concept(client, definition="A short, strong coffee."))
        advance_to_review(client, as_role, term_id)
        as_role(Role.REVIEWER)
        transition(client, term_id, "request_changes", "Definition covers the drink.")

        comments = client.get(f"/api/terms/{term_id}/comments").json()

        assert len(comments) == 1
        assert comments[0]["body"] == "Definition covers the drink."
        assert comments[0]["transition"] == "changes_requested"

    def test_whitespace_does_not_count_as_a_reason(self, client: TestClient, as_role, languages):
        as_role(Role.EDITOR)
        term_id = first_term(make_concept(client, definition="A short, strong coffee."))
        advance_to_review(client, as_role, term_id)

        as_role(Role.APPROVER)
        assert transition(client, term_id, "reject", "   ").status_code == 422

    def test_status_cannot_be_set_through_a_plain_update(
        self, client: TestClient, as_role, languages
    ):
        """The workflow is the only way in, so its rules cannot be bypassed."""
        as_role(Role.EDITOR)
        term_id = first_term(make_concept(client))

        patch_term(client, term_id, status="approved")

        assert client.get(f"/api/terms/{term_id}").json()["status"] == TermStatus.DRAFT


class TestReapproval:
    def test_a_substantive_edit_undoes_approval(self, client: TestClient, as_role, languages):
        """An "Approved" badge must refer to the wording it was given for. → D19"""
        as_role(Role.EDITOR)
        term_id = first_term(make_concept(client, definition="A short, strong coffee."))
        advance_to_review(client, as_role, term_id)
        as_role(Role.APPROVER)
        transition(client, term_id, "approve")

        as_role(Role.EDITOR)
        response = patch_term(client, term_id, definition="Something else.")

        assert response.json()["status"] == TermStatus.DRAFT

    def test_a_cosmetic_edit_does_not(self, client: TestClient, as_role, languages):
        as_role(Role.EDITOR)
        term_id = first_term(make_concept(client, definition="A short, strong coffee."))
        advance_to_review(client, as_role, term_id)
        as_role(Role.APPROVER)
        transition(client, term_id, "approve")

        as_role(Role.EDITOR)
        response = patch_term(client, term_id, source="ISO 3103")

        assert response.json()["status"] == TermStatus.APPROVED


class TestPerLanguageStatus:
    def test_languages_advance_independently(self, client: TestClient, as_role, languages):
        """The point of D1."""
        as_role(Role.EDITOR)
        concept = make_concept(client, definition="Ein kurzer, starker Kaffee.")
        client.post(
            f"/api/concepts/{concept['id']}/terms",
            json={"language_code": "en", "term": "Espresso", "definition": "Short strong coffee."},
        )
        german = first_term(concept)

        advance_to_review(client, as_role, german)
        as_role(Role.APPROVER)
        transition(client, german, "approve")

        entries = {
            entry["language_code"]: entry["status"]
            for entry in client.get(f"/api/concepts/{concept['id']}").json()["term_entries"]
        }
        assert entries == {"de": TermStatus.APPROVED, "en": TermStatus.DRAFT}

    def test_the_concept_shows_the_least_advanced_language(
        self, client: TestClient, as_role, languages
    ):
        """Rollup = lowest status, so "not finished" finds everything. → D17"""
        as_role(Role.EDITOR)
        concept = make_concept(client, definition="Ein kurzer, starker Kaffee.")
        client.post(
            f"/api/concepts/{concept['id']}/terms",
            json={"language_code": "en", "term": "Espresso", "definition": "Short strong coffee."},
        )
        german = first_term(concept)

        advance_to_review(client, as_role, german)
        as_role(Role.APPROVER)
        transition(client, german, "approve")

        assert client.get(f"/api/concepts/{concept['id']}").json()["status"] == TermStatus.DRAFT

    def test_a_concept_without_entries_has_no_status(self, client: TestClient, as_role, languages):
        as_role(Role.EDITOR)
        concept = client.post("/api/concepts", json={}).json()

        assert concept["status"] is None

    def test_one_rejected_language_does_not_sink_the_concept(
        self, client: TestClient, as_role, languages
    ):
        as_role(Role.EDITOR)
        concept = make_concept(client, definition="Ein kurzer, starker Kaffee.")
        english = client.post(
            f"/api/concepts/{concept['id']}/terms",
            json={"language_code": "en", "term": "Espresso", "definition": "Short strong coffee."},
        ).json()["id"]

        advance_to_review(client, as_role, english)
        as_role(Role.APPROVER)
        transition(client, english, "reject", "Wrong concept.")

        assert client.get(f"/api/concepts/{concept['id']}").json()["status"] == TermStatus.DRAFT
