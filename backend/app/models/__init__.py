"""SQLAlchemy ORM models.

Every model is imported here so that `Base.metadata` is complete — Alembic's
autogenerate compares against it, and a model that is not imported is a table
that silently never gets created.
"""

from app.models.concept import Concept, Domain, concept_domains
from app.models.enums import (
    ConceptLifecycle,
    EntryOrigin,
    HistoryEntityType,
    ReviewTransition,
    Role,
    TermStatus,
)
from app.models.history import ChangeHistoryEntry, ReviewComment
from app.models.session import UserSession
from app.models.term import TermEntry
from app.models.user import User
from app.models.workspace import SINGLETON_ID, Language, WorkspaceSettings

__all__ = [
    "SINGLETON_ID",
    "ChangeHistoryEntry",
    "Concept",
    "ConceptLifecycle",
    "Domain",
    "EntryOrigin",
    "HistoryEntityType",
    "Language",
    "ReviewComment",
    "ReviewTransition",
    "Role",
    "TermEntry",
    "TermStatus",
    "User",
    "UserSession",
    "WorkspaceSettings",
    "concept_domains",
]
