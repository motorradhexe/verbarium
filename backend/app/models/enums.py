"""Enumerations used across the model.

All of these are stored as strings with a check constraint rather than as
native database enums. Native PostgreSQL enums need a DDL migration to add a
single value and do not exist in SQLite at all — with two supported backends
the portable form is the practical one.
"""

from enum import StrEnum


class Role(StrEnum):
    """Six roles with escalating permissions, global per workspace in v1."""

    VIEWER = "viewer"
    CONTRIBUTOR = "contributor"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    APPROVER = "approver"
    ADMIN = "admin"

    @property
    def rank(self) -> int:
        """Position in the hierarchy, Viewer lowest.

        `REQUIREMENTS.md` calls the roles "escalating", so permissions are
        treated as cumulative: an Approver can do everything an Editor can.
        If a role ever needs a permission that a higher one lacks, this
        ordering stops being enough and the checks need an explicit
        permission matrix instead.
        """
        return _ROLE_ORDER.index(self)

    def can_act_as(self, required: "Role") -> bool:
        return self.rank >= required.rank


_ROLE_ORDER = [
    Role.VIEWER,
    Role.CONTRIBUTOR,
    Role.EDITOR,
    Role.REVIEWER,
    Role.APPROVER,
    Role.ADMIN,
]


class TermStatus(StrEnum):
    """Review status. Sits on the term entry: each language runs its own
    review cycle. → D1"""

    DRAFT = "draft"
    PROPOSED = "proposed"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ConceptLifecycle(StrEnum):
    """Independent of review status: a deprecated concept keeps whatever
    status its entries had. → D7"""

    ACTIVE = "active"
    DEPRECATED = "deprecated"


class EntryOrigin(StrEnum):
    """How an entry came to be. Deliberately not a status, so an entry stays
    identifiable as an AI suggestion after it moves through the workflow. → D3
    """

    MANUAL = "manual"
    AI = "ai"
    IMPORT = "import"


class ReviewTransition(StrEnum):
    """The workflow step a review comment accompanied, if any. Mandatory for
    the two negative outcomes. → D6"""

    SUBMITTED = "submitted"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    REJECTED = "rejected"


class HistoryEntityType(StrEnum):
    """Which table a change history row refers to."""

    CONCEPT = "concept"
    TERM_ENTRY = "term_entry"
