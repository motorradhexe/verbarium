"""The status workflow for term entries. → D1, D5, D6

    Contributor → Editor → Reviewer → Approver → Approved
                ↖                               ↘ Rejected
                 ← Changes requested ←

Each language runs this cycle on its own: approving the German entry says
nothing about the English one.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.models.enums import ReviewTransition, Role, TermStatus
from app.models.term import TermEntry
from app.models.user import User


class TransitionError(Exception):
    """Base class for a refused transition."""


class TransitionNotAllowed(TransitionError):
    """The entry is not in a status this transition applies to."""


class TransitionForbidden(TransitionError):
    """The user's role is too low for this transition."""


class CommentRequired(TransitionError):
    """A negative outcome has to say why. → D6"""


class IncompleteEntry(TransitionError):
    """A field required at this status is missing. → D5"""


class Action(StrEnum):
    SUBMIT = "submit"
    START_REVIEW = "start_review"
    REQUEST_CHANGES = "request_changes"
    APPROVE = "approve"
    REJECT = "reject"


@dataclass(frozen=True)
class Transition:
    """One allowed move through the workflow."""

    action: Action
    #: Statuses the entry may be in for this action to apply.
    from_statuses: frozenset[TermStatus]
    to_status: TermStatus
    minimum_role: Role
    #: Whether the caller has to give a reason.
    requires_comment: bool
    #: What the comment is recorded as, if one is given.
    records_as: ReviewTransition


TRANSITIONS: dict[Action, Transition] = {
    Action.SUBMIT: Transition(
        action=Action.SUBMIT,
        from_statuses=frozenset({TermStatus.DRAFT}),
        to_status=TermStatus.PROPOSED,
        # A Contributor's whole purpose is submitting proposals.
        minimum_role=Role.CONTRIBUTOR,
        requires_comment=False,
        records_as=ReviewTransition.SUBMITTED,
    ),
    Action.START_REVIEW: Transition(
        action=Action.START_REVIEW,
        from_statuses=frozenset({TermStatus.PROPOSED}),
        to_status=TermStatus.IN_REVIEW,
        minimum_role=Role.REVIEWER,
        requires_comment=False,
        records_as=ReviewTransition.SUBMITTED,
    ),
    Action.REQUEST_CHANGES: Transition(
        action=Action.REQUEST_CHANGES,
        from_statuses=frozenset({TermStatus.PROPOSED, TermStatus.IN_REVIEW}),
        to_status=TermStatus.DRAFT,
        minimum_role=Role.REVIEWER,
        requires_comment=True,
        records_as=ReviewTransition.CHANGES_REQUESTED,
    ),
    Action.APPROVE: Transition(
        action=Action.APPROVE,
        from_statuses=frozenset({TermStatus.IN_REVIEW}),
        to_status=TermStatus.APPROVED,
        minimum_role=Role.APPROVER,
        requires_comment=False,
        records_as=ReviewTransition.APPROVED,
    ),
    Action.REJECT: Transition(
        action=Action.REJECT,
        from_statuses=frozenset({TermStatus.PROPOSED, TermStatus.IN_REVIEW}),
        to_status=TermStatus.REJECTED,
        minimum_role=Role.APPROVER,
        requires_comment=True,
        records_as=ReviewTransition.REJECTED,
    ),
}

#: Fields that must be filled before an entry can be approved. Enforced here
#: rather than by the column, so a quick proposal or an AI candidate can be
#: created without them. → D5
REQUIRED_TO_APPROVE = ("term", "definition")

#: Changing one of these on an approved entry sends it back for review: an
#: "Approved" badge has to mean somebody approved *this* wording. Notes,
#: examples, and sources can be corrected without a new cycle.
SUBSTANTIVE_FIELDS = frozenset({"term", "definition", "synonyms", "nogo_alternatives"})


def check(entry: TermEntry, action: Action, user: User, comment: str | None) -> Transition:
    """Validate a transition, raising the specific reason it is refused."""
    transition = TRANSITIONS[action]

    if entry.status not in transition.from_statuses:
        allowed = ", ".join(sorted(status.value for status in transition.from_statuses))
        raise TransitionNotAllowed(
            f"{action.value} applies to entries in {allowed}, not {entry.status.value}"
        )

    if not user.role.can_act_as(transition.minimum_role):
        raise TransitionForbidden(
            f"{action.value} requires the {transition.minimum_role.value} role or higher"
        )

    if transition.requires_comment and not (comment and comment.strip()):
        raise CommentRequired(f"{action.value} requires a comment explaining the decision")

    if action is Action.APPROVE:
        missing = [field for field in REQUIRED_TO_APPROVE if not getattr(entry, field)]
        if missing:
            raise IncompleteEntry(f"Cannot approve without {', '.join(missing)}")

    return transition


def needs_reapproval(entry: TermEntry, changed_fields: set[str]) -> bool:
    """Whether an edit invalidates an existing approval."""
    return entry.status is TermStatus.APPROVED and bool(changed_fields & SUBSTANTIVE_FIELDS)


#: Rollup order, lowest first. A concept is only as far along as its least
#: advanced language, so the "not finished yet" filter finds everything that
#: still needs work. Rejected sits outside this scale and is handled
#: separately. → D1
ROLLUP_ORDER = [
    TermStatus.DRAFT,
    TermStatus.PROPOSED,
    TermStatus.IN_REVIEW,
    TermStatus.APPROVED,
]


def rollup_status(entries: list[TermEntry]) -> TermStatus | None:
    """The status shown for a concept, derived from its languages.

    None when there is nothing to summarise. Rejected entries are ignored
    unless every entry is rejected — one rejected translation should not make
    a concept with an approved German entry look rejected. A missing language
    is a gap, not a status, and does not enter this calculation.
    """
    if not entries:
        return None

    considered = [entry for entry in entries if entry.status is not TermStatus.REJECTED]
    if not considered:
        return TermStatus.REJECTED

    return min(considered, key=lambda entry: ROLLUP_ORDER.index(entry.status)).status
