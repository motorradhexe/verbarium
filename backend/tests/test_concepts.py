"""Term list, filters, visibility, deprecation, and change history.

→ D7, D9, D10, D12, D16, D18
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


@pytest.fixture
def termbase(client: TestClient, as_role, languages) -> dict:
    """A small termbase: two concepts, one bilingual, one German only."""
    as_role(Role.EDITOR)
    marketing = client.post("/api/domains", json={"name": "Marketing"}).json()
    legal = client.post("/api/domains", json={"name": "Legal"}).json()

    espresso = client.post(
        "/api/concepts",
        json={
            "domain_ids": [marketing["id"], legal["id"]],
            "terms": [
                {
                    "language_code": "de",
                    "term": "Espresso",
                    "definition": "Ein kurzer, starker Kaffee.",
                    "synonyms": ["Kaffee Crème"],
                    "nogo_alternatives": ["Expresso"],
                    "notes": "Nicht mit Ristretto verwechseln.",
                },
                {"language_code": "en", "term": "Espresso", "definition": "Short strong coffee."},
            ],
        },
    ).json()

    crema = client.post(
        "/api/concepts",
        json={
            "domain_ids": [marketing["id"]],
            "terms": [
                {"language_code": "de", "term": "Crema", "definition": "Die Schaumschicht."}
            ],
        },
    ).json()

    return {"espresso": espresso, "crema": crema, "marketing": marketing, "legal": legal}


class TestTermList:
    def test_a_row_per_concept_with_a_column_per_language(
        self, client: TestClient, termbase, as_role
    ):
        """→ D12"""
        as_role(Role.VIEWER)

        page = client.get("/api/concepts").json()

        assert page["total"] == 2
        by_id = {item["id"]: item for item in page["items"]}
        assert set(by_id[termbase["espresso"]["id"]]["languages"]) == {"de", "en"}
        assert set(by_id[termbase["crema"]["id"]]["languages"]) == {"de"}

    def test_the_cell_carries_term_and_status(self, client: TestClient, termbase, as_role):
        as_role(Role.VIEWER)

        page = client.get("/api/concepts").json()
        crema = next(item for item in page["items"] if item["id"] == termbase["crema"]["id"])

        assert crema["languages"]["de"] == {"term": "Crema", "status": TermStatus.DRAFT}

    def test_the_gap_filter_finds_what_is_missing(self, client: TestClient, termbase, as_role):
        """Ordinary filters work on what exists. → D12"""
        as_role(Role.VIEWER)

        page = client.get("/api/concepts", params={"missing_language": "en"}).json()

        assert [item["id"] for item in page["items"]] == [termbase["crema"]["id"]]

    def test_filtering_by_language(self, client: TestClient, termbase, as_role):
        as_role(Role.VIEWER)

        page = client.get("/api/concepts", params={"language": "en"}).json()

        assert [item["id"] for item in page["items"]] == [termbase["espresso"]["id"]]

    def test_filtering_by_domain(self, client: TestClient, termbase, as_role):
        """→ D9"""
        as_role(Role.VIEWER)

        page = client.get("/api/concepts", params={"domain_id": termbase["legal"]["id"]}).json()

        assert [item["id"] for item in page["items"]] == [termbase["espresso"]["id"]]

    def test_a_concept_can_carry_several_domains(self, client: TestClient, termbase, as_role):
        as_role(Role.VIEWER)

        concept = client.get(f"/api/concepts/{termbase['espresso']['id']}").json()

        assert {domain["name"] for domain in concept["domains"]} == {"Marketing", "Legal"}

    def test_paging_reports_the_total(self, client: TestClient, termbase, as_role):
        as_role(Role.VIEWER)

        page = client.get("/api/concepts", params={"limit": 1}).json()

        assert len(page["items"]) == 1
        assert page["total"] == 2


class TestSearch:
    def test_it_finds_a_term(self, client: TestClient, termbase, as_role):
        as_role(Role.VIEWER)

        page = client.get("/api/concepts", params={"query": "crema"}).json()

        assert page["total"] == 1

    def test_it_searches_definitions(self, client: TestClient, termbase, as_role):
        as_role(Role.VIEWER)

        page = client.get("/api/concepts", params={"query": "Schaumschicht"}).json()

        assert page["total"] == 1

    def test_it_searches_synonyms_and_nogo_alternatives(
        self, client: TestClient, termbase, as_role
    ):
        """`REQUIREMENTS.md` names all four fields."""
        as_role(Role.VIEWER)

        assert client.get("/api/concepts", params={"query": "Expresso"}).json()["total"] == 1
        assert client.get("/api/concepts", params={"query": "Kaffee Crème"}).json()["total"] == 1

    def test_it_ignores_case_and_diacritics(self, client: TestClient, termbase, as_role):
        """→ D16"""
        as_role(Role.VIEWER)

        assert client.get("/api/concepts", params={"query": "creme"}).json()["total"] == 1

    def test_a_miss_returns_nothing(self, client: TestClient, termbase, as_role):
        as_role(Role.VIEWER)

        assert client.get("/api/concepts", params={"query": "Cappuccino"}).json()["total"] == 0

    def test_the_haystack_follows_an_edit(self, client: TestClient, termbase, as_role):
        as_role(Role.EDITOR)
        term_id = termbase["crema"]["term_entries"][0]["id"]
        patch_term(client, term_id, term="Crema di caffè")

        assert client.get("/api/concepts", params={"query": "caffe"}).json()["total"] == 1


class TestVisibility:
    def test_a_viewer_sees_entries_in_progress(self, client: TestClient, termbase, as_role):
        """Marked as unapproved rather than hidden, so nobody files a
        duplicate for a term already in review. → D10"""
        as_role(Role.VIEWER)

        page = client.get("/api/concepts").json()

        assert page["total"] == 2
        assert page["items"][0]["status"] == TermStatus.DRAFT

    def test_a_viewer_does_not_see_internal_notes(self, client: TestClient, termbase, as_role):
        """Blanked, not omitted — a null says nothing about whether remarks
        exist, and the response still matches the documented schema. → D18"""
        as_role(Role.VIEWER)

        response = client.get(f"/api/concepts/{termbase['espresso']['id']}")

        assert all(entry["notes"] is None for entry in response.json()["term_entries"])
        assert "Ristretto" not in response.text

    def test_a_contributor_does_not_either(self, client: TestClient, termbase, as_role):
        as_role(Role.CONTRIBUTOR)

        response = client.get(f"/api/concepts/{termbase['espresso']['id']}")

        assert "Ristretto" not in response.text

    def test_an_editor_does(self, client: TestClient, termbase, as_role):
        as_role(Role.EDITOR)

        concept = client.get(f"/api/concepts/{termbase['espresso']['id']}").json()

        notes = [entry.get("notes") for entry in concept["term_entries"]]
        assert "Nicht mit Ristretto verwechseln." in notes

    def test_the_term_list_never_carries_notes(self, client: TestClient, termbase, as_role):
        as_role(Role.ADMIN)

        assert "Ristretto" not in client.get("/api/concepts").text

    def test_anonymous_callers_see_nothing(self, client: TestClient, termbase):
        client.cookies.clear()

        assert client.get("/api/concepts").status_code == 401


class TestDeprecation:
    def test_a_concept_can_be_retired_with_a_successor(
        self, client: TestClient, termbase, as_role
    ):
        """→ D7"""
        as_role(Role.EDITOR)

        response = client.post(
            f"/api/concepts/{termbase['crema']['id']}/deprecate",
            json={"superseded_by_id": termbase["espresso"]["id"]},
        )

        assert response.status_code == 200
        assert response.json()["lifecycle"] == "deprecated"
        assert response.json()["superseded_by_id"] == termbase["espresso"]["id"]

    def test_a_retired_concept_stays_findable(self, client: TestClient, termbase, as_role):
        """Someone searching the old term must be led to the new one."""
        as_role(Role.EDITOR)
        client.post(f"/api/concepts/{termbase['crema']['id']}/deprecate", json={})

        assert client.get("/api/concepts", params={"query": "crema"}).json()["total"] == 1

    def test_a_concept_cannot_supersede_itself(self, client: TestClient, termbase, as_role):
        as_role(Role.EDITOR)

        response = client.post(
            f"/api/concepts/{termbase['crema']['id']}/deprecate",
            json={"superseded_by_id": termbase["crema"]["id"]},
        )

        assert response.status_code == 422

    def test_filtering_to_active_concepts_only(self, client: TestClient, termbase, as_role):
        as_role(Role.EDITOR)
        client.post(f"/api/concepts/{termbase['crema']['id']}/deprecate", json={})

        page = client.get("/api/concepts", params={"lifecycle": "active"}).json()

        assert [item["id"] for item in page["items"]] == [termbase["espresso"]["id"]]

    def test_reactivating_clears_the_successor(self, client: TestClient, termbase, as_role):
        as_role(Role.EDITOR)
        client.post(
            f"/api/concepts/{termbase['crema']['id']}/deprecate",
            json={"superseded_by_id": termbase["espresso"]["id"]},
        )

        response = client.post(f"/api/concepts/{termbase['crema']['id']}/reactivate")

        assert response.json()["lifecycle"] == "active"
        assert response.json()["superseded_by_id"] is None


class TestAssignment:
    def test_a_reviewer_can_claim_an_entry(
        self, client: TestClient, termbase, as_role, accounts
    ):
        """Without this the review queue is an undifferentiated pile. → D2"""
        reviewer = as_role(Role.REVIEWER)
        term_id = termbase["crema"]["term_entries"][0]["id"]

        response = client.post(
            f"/api/terms/{term_id}/assignee", json={"assignee_id": str(reviewer.id)}
        )

        assert response.json()["assignee_id"] == str(reviewer.id)

    def test_the_queue_can_be_filtered_by_assignee(
        self, client: TestClient, termbase, as_role, accounts
    ):
        reviewer = as_role(Role.REVIEWER)
        term_id = termbase["crema"]["term_entries"][0]["id"]
        client.post(f"/api/terms/{term_id}/assignee", json={"assignee_id": str(reviewer.id)})

        page = client.get("/api/concepts", params={"assignee_id": str(reviewer.id)}).json()

        assert [item["id"] for item in page["items"]] == [termbase["crema"]["id"]]

    def test_a_contributor_cannot_assign(self, client: TestClient, termbase, as_role, accounts):
        as_role(Role.CONTRIBUTOR)
        term_id = termbase["crema"]["term_entries"][0]["id"]

        response = client.post(f"/api/terms/{term_id}/assignee", json={"assignee_id": None})

        assert response.status_code == 403


class TestChangeHistory:
    def test_creation_is_recorded(self, client: TestClient, termbase, as_role):
        as_role(Role.EDITOR)
        term_id = termbase["crema"]["term_entries"][0]["id"]

        entries = client.get(f"/api/terms/{term_id}/history").json()

        assert [entry["field"] for entry in entries] == ["created"]

    def test_an_edit_records_the_old_and_new_value(self, client: TestClient, termbase, as_role):
        as_role(Role.EDITOR)
        term_id = termbase["crema"]["term_entries"][0]["id"]
        patch_term(client, term_id, term="Crema di caffè")

        change = client.get(f"/api/terms/{term_id}/history").json()[0]

        assert change["field"] == "term"
        assert change["old_value"] == "Crema"
        assert change["new_value"] == "Crema di caffè"

    def test_an_unchanged_field_produces_no_row(self, client: TestClient, termbase, as_role):
        as_role(Role.EDITOR)
        term_id = termbase["crema"]["term_entries"][0]["id"]
        patch_term(client, term_id, term="Crema")

        assert len(client.get(f"/api/terms/{term_id}/history").json()) == 1

    def test_a_transition_is_recorded(self, client: TestClient, termbase, as_role):
        as_role(Role.EDITOR)
        term_id = termbase["crema"]["term_entries"][0]["id"]
        client.post(f"/api/terms/{term_id}/transition", json={"action": "submit"})

        change = client.get(f"/api/terms/{term_id}/history").json()[0]

        assert change["field"] == "status"
        assert (change["old_value"], change["new_value"]) == ("draft", "proposed")

    def test_it_names_who_changed_it(self, client: TestClient, termbase, as_role):
        editor = as_role(Role.EDITOR)
        term_id = termbase["crema"]["term_entries"][0]["id"]
        patch_term(client, term_id, term="Crema di caffè")

        change = client.get(f"/api/terms/{term_id}/history").json()[0]

        assert change["changed_by_id"] == str(editor.id)

    def test_a_contributor_cannot_read_the_history(self, client: TestClient, termbase, as_role):
        """Visible to Editors and above, per REQUIREMENTS.md."""
        as_role(Role.CONTRIBUTOR)
        term_id = termbase["crema"]["term_entries"][0]["id"]

        assert client.get(f"/api/terms/{term_id}/history").status_code == 403

    def test_the_history_outlives_the_entry(self, client: TestClient, termbase, as_role, db):
        """History rows carry no foreign key to the entity for this reason."""
        as_role(Role.ADMIN)
        term_id = termbase["crema"]["term_entries"][0]["id"]
        patch_term(client, term_id, term="Crema di caffè")
        client.delete(f"/api/concepts/{termbase['crema']['id']}")

        from app.models import ChangeHistoryEntry

        remaining = db.query(ChangeHistoryEntry).count()
        assert remaining > 0


class TestEditingPermissions:
    def test_a_contributor_may_fix_their_own_draft(
        self, client: TestClient, as_role, languages
    ):
        as_role(Role.CONTRIBUTOR)
        concept = client.post(
            "/api/concepts", json={"terms": [{"language_code": "de", "term": "Kafee"}]}
        ).json()
        term_id = concept["term_entries"][0]["id"]

        assert patch_term(client, term_id, term="Kaffee").status_code == 200

    def test_a_contributor_may_not_edit_someone_else_s(
        self, client: TestClient, termbase, as_role
    ):
        as_role(Role.CONTRIBUTOR)
        term_id = termbase["crema"]["term_entries"][0]["id"]

        response = patch_term(client, term_id, term="Crema di caffè")

        assert response.status_code == 403

    def test_only_an_admin_may_delete_a_concept(self, client: TestClient, termbase, as_role):
        as_role(Role.APPROVER)
        assert client.delete(f"/api/concepts/{termbase['crema']['id']}").status_code == 403

        as_role(Role.ADMIN)
        assert client.delete(f"/api/concepts/{termbase['crema']['id']}").status_code == 204


class TestOptimisticLocking:
    """Two editors on one entry must not overwrite each other. → D4

    The model has carried a version column since the schema landed, but until
    the API accepted one, every request loaded the row fresh and therefore
    always saw the current version — so the guard never fired over HTTP.
    """

    def test_a_write_based_on_the_current_version_succeeds(
        self, client: TestClient, termbase, as_role
    ):
        as_role(Role.EDITOR)
        term_id = termbase["crema"]["term_entries"][0]["id"]
        version = client.get(f"/api/terms/{term_id}").json()["version"]

        response = client.patch(
            f"/api/terms/{term_id}", json={"version": version, "term": "Crema di caffè"}
        )

        assert response.status_code == 200

    def test_a_write_based_on_a_stale_read_is_refused(
        self, client: TestClient, termbase, as_role
    ):
        as_role(Role.EDITOR)
        term_id = termbase["crema"]["term_entries"][0]["id"]
        stale = client.get(f"/api/terms/{term_id}").json()["version"]
        patch_term(client, term_id, definition="Changed by someone else.")

        response = client.patch(
            f"/api/terms/{term_id}", json={"version": stale, "term": "Crema di caffè"}
        )

        assert response.status_code == 409
        assert "Reload" in response.json()["detail"]

    def test_the_refused_write_changed_nothing(self, client: TestClient, termbase, as_role):
        as_role(Role.EDITOR)
        term_id = termbase["crema"]["term_entries"][0]["id"]
        stale = client.get(f"/api/terms/{term_id}").json()["version"]
        patch_term(client, term_id, definition="Changed by someone else.")

        client.patch(f"/api/terms/{term_id}", json={"version": stale, "term": "Overwritten"})

        assert client.get(f"/api/terms/{term_id}").json()["term"] == "Crema"

    def test_the_version_advances_with_every_write(self, client: TestClient, termbase, as_role):
        as_role(Role.EDITOR)
        term_id = termbase["crema"]["term_entries"][0]["id"]
        before = client.get(f"/api/terms/{term_id}").json()["version"]

        patch_term(client, term_id, term="Crema di caffè")

        assert client.get(f"/api/terms/{term_id}").json()["version"] == before + 1

    def test_the_version_is_required(self, client: TestClient, termbase, as_role):
        """A lock check the client may omit is no lock at all."""
        as_role(Role.EDITOR)
        term_id = termbase["crema"]["term_entries"][0]["id"]

        response = client.patch(f"/api/terms/{term_id}", json={"term": "Crema di caffè"})

        assert response.status_code == 422

    def test_concepts_are_guarded_too(self, client: TestClient, termbase, as_role):
        as_role(Role.EDITOR)
        concept_id = termbase["crema"]["id"]
        stale = client.get(f"/api/concepts/{concept_id}").json()["version"]
        client.patch(
            f"/api/concepts/{concept_id}",
            json={"version": stale, "domain_ids": [termbase["legal"]["id"]]},
        )

        response = client.patch(
            f"/api/concepts/{concept_id}", json={"version": stale, "domain_ids": []}
        )

        assert response.status_code == 409
