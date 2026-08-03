"""Model-level tests.

These assert the guarantees the database itself enforces. Anything checked
only in Python would still let a bad row in through an import, a migration, or
a direct write.
"""

import uuid

import pytest
from sqlalchemy import Uuid, bindparam, text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.models import (
    Concept,
    ConceptLifecycle,
    Domain,
    Language,
    ReviewComment,
    TermEntry,
    TermStatus,
    User,
    WorkspaceSettings,
)
from app.models.enums import EntryOrigin, ReviewTransition, Role
from app.models.workspace import SINGLETON_ID
from tests.conftest import make_term


class TestWorkspaceSettings:
    def test_singleton_row_is_allowed(self, db: Session):
        db.add(WorkspaceSettings(name="Coffee Terminology"))
        db.commit()

        assert db.get(WorkspaceSettings, SINGLETON_ID) is not None

    def test_second_workspace_is_rejected(self, db: Session):
        """One instance holds exactly one workspace. → D8"""
        db.add(WorkspaceSettings(name="First"))
        db.commit()

        db.add(WorkspaceSettings(id=2, name="Second"))
        with pytest.raises(IntegrityError):
            db.commit()


class TestLanguages:
    def test_a_language_in_use_cannot_be_deleted(
        self, db: Session, concept: Concept, user: User, languages: list[Language]
    ):
        """RESTRICT rather than a cascade through the termbase. → D14"""
        db.add(make_term(concept, user, "de", "Espresso"))
        db.commit()

        db.delete(db.get(Language, "de"))
        with pytest.raises(IntegrityError):
            db.commit()

    def test_an_unused_language_can_be_removed(self, db: Session, languages: list[Language]):
        db.delete(db.get(Language, "en"))
        db.commit()

        assert db.get(Language, "en") is None

    def test_region_tags_are_rejected(self, db: Session):
        db.add(Language(code="de-DE", name="German (Germany)"))
        with pytest.raises((IntegrityError, StatementError)):
            db.commit()


class TestTermEntries:
    def test_one_entry_per_concept_and_language(
        self, db: Session, concept: Concept, user: User, languages: list[Language]
    ):
        db.add(make_term(concept, user, "de", "Espresso"))
        db.commit()

        db.add(make_term(concept, user, "de", "Espresso (Variante)"))
        with pytest.raises(IntegrityError):
            db.commit()

    def test_the_same_language_in_another_concept_is_fine(
        self, db: Session, concept: Concept, user: User, languages: list[Language]
    ):
        other = Concept(created_by_id=user.id)
        db.add(other)
        db.commit()

        db.add(make_term(concept, user, "de", "Espresso"))
        db.add(make_term(other, user, "de", "Crema"))
        db.commit()

        assert db.query(TermEntry).count() == 2

    def test_languages_carry_their_own_status(
        self, db: Session, concept: Concept, user: User, languages: list[Language]
    ):
        """The point of D1: German approved while English is still a draft."""
        db.add(make_term(concept, user, "de", "Espresso", status=TermStatus.APPROVED))
        db.add(make_term(concept, user, "en", "Espresso", status=TermStatus.DRAFT))
        db.commit()
        db.expire_all()

        by_language = {entry.language_code: entry.status for entry in concept.term_entries}
        assert by_language == {"de": TermStatus.APPROVED, "en": TermStatus.DRAFT}

    def test_an_entry_may_be_created_without_a_definition(
        self, db: Session, concept: Concept, user: User, languages: list[Language]
    ):
        """Quick proposals and AI candidates come in without one. → D5"""
        db.add(make_term(concept, user, "de", "Espresso", origin=EntryOrigin.AI))
        db.commit()

        assert db.query(TermEntry).one().definition is None

    def test_an_unknown_status_is_rejected(
        self, db: Session, concept: Concept, user: User, languages: list[Language]
    ):
        """The check constraint, not just the ORM: raw SQL must fail too.

        The value is deliberately short enough to fit the column — the enum
        renders as a VARCHAR sized to its longest member, so a longer value
        would be caught by the width rather than by the constraint under test.
        """
        entry = make_term(concept, user, "de", "Espresso")
        db.add(entry)
        db.commit()

        statement = text("UPDATE term_entries SET status = 'reviewed' WHERE id = :id").bindparams(
            # Typed, because the two backends store UUIDs differently: native
            # `uuid` on PostgreSQL, 32-character hex on SQLite.
            bindparam("id", value=entry.id, type_=Uuid)
        )

        with pytest.raises(IntegrityError):
            db.execute(statement)
            db.commit()

    def test_deleting_a_concept_removes_its_entries(
        self, db: Session, concept: Concept, user: User, languages: list[Language]
    ):
        db.add(make_term(concept, user, "de", "Espresso"))
        db.commit()

        db.delete(concept)
        db.commit()

        assert db.query(TermEntry).count() == 0

    def test_lists_default_to_empty(
        self, db: Session, concept: Concept, user: User, languages: list[Language]
    ):
        db.add(make_term(concept, user, "de", "Espresso"))
        db.commit()

        entry = db.query(TermEntry).one()
        assert entry.synonyms == []
        assert entry.nogo_alternatives == []
        assert entry.custom_fields == {}


class TestOptimisticLocking:
    def test_a_write_based_on_a_stale_read_is_rejected(
        self, db: Session, concept: Concept, user: User, languages: list[Language]
    ):
        """Two editors on one entry must not overwrite each other. → D4"""
        entry = make_term(concept, user, "de", "Espresso")
        db.add(entry)
        db.commit()

        # Simulate a second session that saved first.
        db.execute(
            text(
                "UPDATE term_entries SET term = 'Espresso Doppio', version = version + 1 "
                "WHERE id = :id"
            ).bindparams(bindparam("id", value=entry.id, type_=Uuid)),
        )
        db.commit()

        entry.term = "Ristretto"
        with pytest.raises(StaleDataError):
            db.commit()

    def test_the_version_advances_on_every_write(self, db: Session, concept: Concept):
        assert concept.version == 1

        concept.lifecycle = ConceptLifecycle.DEPRECATED
        db.commit()

        assert concept.version == 2


class TestDeprecation:
    def test_a_deprecated_concept_points_at_its_successor(self, db: Session, user: User):
        """→ D7"""
        successor = Concept(created_by_id=user.id)
        db.add(successor)
        db.commit()

        outdated = Concept(
            created_by_id=user.id,
            lifecycle=ConceptLifecycle.DEPRECATED,
            superseded_by_id=successor.id,
        )
        db.add(outdated)
        db.commit()
        db.expire_all()

        assert db.get(Concept, outdated.id).superseded_by.id == successor.id

    def test_an_active_concept_cannot_have_a_successor(self, db: Session, user: User):
        successor = Concept(created_by_id=user.id)
        db.add(successor)
        db.commit()

        db.add(Concept(created_by_id=user.id, superseded_by_id=successor.id))
        with pytest.raises(IntegrityError):
            db.commit()

    def test_a_concept_cannot_supersede_itself(self, db: Session, user: User):
        identifier = uuid.uuid4()
        db.add(
            Concept(
                id=identifier,
                created_by_id=user.id,
                lifecycle=ConceptLifecycle.DEPRECATED,
                superseded_by_id=identifier,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


class TestDomains:
    def test_a_concept_can_carry_several_domains(self, db: Session, concept: Concept):
        """→ D9"""
        marketing = Domain(name="Marketing")
        legal = Domain(name="Legal")
        db.add_all([marketing, legal])
        concept.domains.extend([marketing, legal])
        db.commit()
        db.expire_all()

        assert {d.name for d in db.get(Concept, concept.id).domains} == {"Marketing", "Legal"}

    def test_domain_names_are_unique(self, db: Session):
        db.add_all([Domain(name="Marketing"), Domain(name="Marketing")])
        with pytest.raises(IntegrityError):
            db.commit()


class TestUsers:
    def test_email_is_unique(self, db: Session, user: User):
        db.add(
            User(
                email=user.email,
                display_name="Someone else",
                password_hash="x",
                role=Role.VIEWER,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()

    def test_an_author_cannot_be_deleted(self, db: Session, concept: Concept, user: User):
        """Entries reference their author, and the history outlives the row."""
        db.delete(user)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_an_unassigned_reviewer_leaves_the_entry_in_place(
        self, db: Session, concept: Concept, user: User, languages: list[Language]
    ):
        reviewer = User(
            email="reviewer@example.org",
            display_name="Reviewer",
            password_hash="x",
            role=Role.REVIEWER,
        )
        db.add(reviewer)
        db.commit()

        entry = make_term(concept, user, "de", "Espresso", assignee_id=reviewer.id)
        db.add(entry)
        db.commit()

        db.delete(reviewer)
        db.commit()
        db.expire_all()

        assert db.get(TermEntry, entry.id).assignee_id is None


class TestReviewComments:
    def test_a_comment_records_the_transition_it_accompanied(
        self, db: Session, concept: Concept, user: User, languages: list[Language]
    ):
        """→ D6"""
        entry = make_term(concept, user, "de", "Espresso")
        db.add(entry)
        db.commit()

        db.add(
            ReviewComment(
                term_entry_id=entry.id,
                author_id=user.id,
                body="Definition covers the drink, not the method.",
                transition=ReviewTransition.CHANGES_REQUESTED,
            )
        )
        db.commit()

        comment = db.query(ReviewComment).one()
        assert comment.transition == ReviewTransition.CHANGES_REQUESTED

    def test_comments_go_with_the_entry(
        self, db: Session, concept: Concept, user: User, languages: list[Language]
    ):
        entry = make_term(concept, user, "de", "Espresso")
        db.add(entry)
        db.commit()
        db.add(ReviewComment(term_entry_id=entry.id, author_id=user.id, body="Looks good."))
        db.commit()

        db.delete(entry)
        db.commit()

        assert db.query(ReviewComment).count() == 0
