# Data Model & Entry Management Decisions

Open questions and decisions that shape the data model and the entry
management UI. Recorded here because most of them are cheap now and expensive
after the first migration ships with real data in it.

Written before any model code exists. `REQUIREMENTS.md` stays the product
specification; this file records *why* the model looks the way it does, and
which questions are still open.

**Status values**

| Status | Meaning |
|---|---|
| `Accepted` | Decided — implement it this way |
| `Proposed` | Recommendation, no objection raised; will be built this way unless changed |
| `Open` | Genuine product decision, no default |

D1 and D7–D10 were decided on 2026-08-03 and carry a **Decision** note.
D17–D19 arose while implementing and follow the recommendation given at the
time; say so if you want any of them the other way.

| # | Question | Outcome |
|---|---|---|
| D1 | Status per concept or per language | Accepted — per language, on `TermEntry` |
| D2 | Assignee | Proposed — on `TermEntry`, with a claim action |
| D3 | Entry origin | Proposed — own field, not a status |
| D4 | Concurrent edits | Proposed — `version`, optimistic locking |
| D5 | Required fields | Proposed — enforced per status transition |
| D6 | Rejection terminal? | Proposed — rework loop, mandatory comment |
| D7 | Deprecation | Accepted — v1.0, with successor reference |
| D8 | Workspace model | Accepted — one per instance |
| D9 | Domain cardinality | Accepted — multi-valued, join table |
| D10 | Work in progress visible | Accepted — visible and badged, exports stay approved-only |
| D11 | Import and workflow | Proposed — target status chosen per import run |
| D12 | Entry management views | Proposed — bulk selection deferred to v1.1, rest v1.0 |
| D13 | Date filter semantics | Proposed — created or changed, defaulting to changed |
| D14 | Content languages | Accepted — configurable from v1.0 |
| D15 | Authentication | Accepted — local accounts, session cookie |
| D16 | Full-text search | Accepted — portable implementation for v1.0 |
| D17 | Concept status roll-up | Proposed — lowest status across languages |
| D18 | Visibility of `notes` | Proposed — editorial roles only, blanked not omitted |
| D19 | Editing an approved entry | Proposed — substantive edits require re-approval |

---

## D1 — Status granularity: per concept or per language

**Status:** Accepted — status per `TermEntry`, concept lifecycle separate (2026-08-03)

`REQUIREMENTS.md` puts `status` on `ConceptEntry` only; `TermEntry` has no
status of its own.

That breaks as soon as a second language enters an approved concept. The
German entry is approved and visible to Viewers, who "read and search approved
terms only". Someone adds the English entry. Either the concept drops back to
*In Review* — and the already-approved German entry disappears for every
Viewer — or the concept stays *Approved* and the unreviewed English entry is
published immediately. Neither is acceptable.

It also removes the single most useful piece of overview: which language is in
which state. A concept-level status cannot express "German approved, English
in review, French missing", and that matrix is what anyone managing a
termbase needs to see.

**Options**

1. **Status per `TermEntry`**, concept status derived for display
   ("2 of 3 languages approved"). Each language runs its own review cycle.
2. Status stays on the concept, plus visibility rules that hide unapproved
   languages from Viewers. Keeps one workflow per concept, but every query
   needs the visibility rule, and reviewers approve a bundle whose parts they
   may not all be qualified to judge.
3. Hybrid: concept-level lifecycle (active/deprecated) plus per-language
   review status.

**Recommendation:** option 3 in effect — review status on `TermEntry`, and a
separate concept-level lifecycle for deprecation (see D7). A reviewer who
speaks German should be able to approve the German entry without implicitly
vouching for the English one.

**Consequences:** `TermEntry` gains `status`; `ConceptEntry.status` becomes
derived (not stored) or is replaced by the lifecycle field. Review queue,
search visibility, and the language columns in the list view all key off the
per-language status.

**Roll-up rule:** settled in D17.

---

## D2 — Assignee

**Status:** Proposed

`REQUIREMENTS.md` promises a filter "by language, domain, status, assignee,
date range", but no entity has an assignee field — it is the only occurrence
of the word in the document.

Without it the review queue is an undifferentiated pile: nobody knows what is
theirs, and two reviewers work the same entry.

**Recommendation:** `assignee` (nullable user reference) on whatever carries
the review status — `TermEntry` under D1. Plus an explicit "claim" action, so
picking work up is one click and visible to everyone else.

---

## D3 — Entry origin

**Status:** Proposed

The AI section says extracted candidates land in the review queue with status
"AI Proposal", but the status enum is *Draft, Proposed, In Review, Approved,
Rejected*. "AI Proposal" is not in it.

Origin is not a workflow state. Modelling it as one makes the enum grow with
every source (an "Imported" status next), and it destroys the ability to ask
"how many AI suggestions were eventually approved?" — because the entry stops
being an AI proposal the moment it moves on.

**Recommendation:** separate field `origin: manual | ai | import` on
`TermEntry`, defaulting to `manual`. AI extraction creates entries with
status *Proposed* and origin *ai*. The UI badges them as AI proposals; the
status enum stays closed.

**Consequences:** enables the "AI-ready, not FULL-AI" claim to be measured,
and lets reviewers filter their queue to human or machine input.

---

## D4 — Concurrent edits

**Status:** Proposed

Two editors on the same entry currently means last-write-wins, silently. The
change history would record both writes, so the loss is reconstructable —
but only by someone who already noticed it happened.

**Recommendation:** `version` integer on `ConceptEntry` and `TermEntry`,
incremented on write. A save carrying a stale version is rejected with a
conflict the UI can surface ("someone else changed this entry").

Cheap now, invasive later: it touches every write path and every update
schema.

---

## D5 — Required fields are status-dependent

**Status:** Proposed

`definition` is marked required on `TermEntry`. That collides with two
specified flows: a Contributor submitting a quick proposal, and AI extraction
producing candidates that may have no definition yet.

**Recommendation:** enforce required-ness at the workflow transition, not in
the database. `term` and `language` are hard requirements (`NOT NULL`);
`definition` is required to reach *Approved*, and the UI shows what is still
missing before an entry can be submitted or approved.

**Consequences:** validation lives in the service layer per target status,
not only in the Pydantic schema.

---

## D6 — Rejection is not a terminal state

**Status:** Proposed

The workflow diagram ends at *Rejected*. A rejected proposal is therefore
dead, with no path back — but terminology work is iterative, and most
rejections mean "not like this", not "never".

There is also no way to say *why*. The change history records field values
before and after, not the reasoning behind a decision. Without it, rejections
get explained by email and the rationale is unfindable a year later.

**Recommendation:**

- Add a *Changes requested* transition that returns an entry to *Draft*,
  keeping the review thread attached.
- *Rejected* stays, meaning "this concept does not belong in the termbase".
- A comment is mandatory for *Changes requested* and *Rejected*.
- Comments are a small separate entity (entry reference, author, timestamp,
  text) — distinct from the change history, which stays automatic and
  read-only.

---

## D7 — Deprecation and supersession

**Status:** Accepted for v1.0 (2026-08-03)

There is no delete, archive, or deprecate anywhere in the model. Terminology
ages: a term that was correct for years gets replaced. *Rejected* means
something else entirely — it never was valid.

Lookup is what suffers. Someone searching the old term finds nothing and
either uses it anyway or files a duplicate proposal, when the system could
have pointed them at the replacement.

**Decision:** concept-level lifecycle `active | deprecated` plus optional
`superseded_by` pointing at the successor concept, in v1.0. Deprecated entries
stay searchable and render as "no longer used — see X". Hard deletion stays
admin-only and rare, because the change history of a deleted entry is worth
more than the row.

**Consequences:** deprecation is not a review status — a deprecated entry
keeps whatever review status it had. Export needs a rule for whether
deprecated entries are included (proposal: excluded from the glossary,
included in TBX with the successor reference, since CAT tools benefit from
knowing what not to use).

---

## D8 — Workspace model

**Status:** Accepted — one workspace per instance (2026-08-03)

`REQUIREMENTS.md` uses "workspace" throughout (roles are "global per
workspace", admins configure "workspace name and languages", AI keys are "per
workspace"), and lists "multi-instance vs. single-instance deployment for
large organizations" as an open question.

The two readings differ in every table: one workspace per instance means no
`workspace_id` anywhere; multiple workspaces per instance means a foreign key
on nearly every row, plus scoping on every query and a tenant check in every
endpoint.

Retrofitting the second onto the first is a migration touching all data plus
an audit of every query for missed scoping — the classic source of
cross-tenant data leaks.

**Decision:** one workspace per instance. No `workspace_id` on any entity. A
second team runs a second container, which matches "self-hosted first" and
keeps the deployment story simple.

**Consequences:** workspace configuration (name, languages, AI provider,
encrypted keys) is a single settings record, enforced as a singleton — one
row, fixed primary key. The setup wizard writes it on first run. Should
multi-tenancy ever be needed, the migration path is a new instance plus
export/import, not a schema change.

---

## D9 — Domain cardinality

**Status:** Accepted — multi-valued (2026-08-03)

`domain` is typed "Tag / Select" — one value or several is unspecified.

v2 plans domain-scoped permissions, which is where it becomes structural: if
an entry can carry three domains and a user is only permitted one of them,
the permission rules need an explicit answer (any-match or all-match).

**Decision:** a concept can carry several domains, stored as a join table
(`concept_domains`) with domains as their own entity, so they can be renamed
without touching every entry.

**Consequences:** filtering by domain is a join, not a column comparison. The
v2 permission rule — access on one matching domain or on all of them — stays
open and is listed in `REQUIREMENTS.md`; any-match is the more common reading
and the more permissive one, so it should be chosen deliberately rather than
by default.

---

## D10 — Visibility of work in progress

**Status:** Accepted for v1.0 (2026-08-03)

Viewers "read and search approved terms only". So while a term is being
drafted and reviewed, nobody outside the editorial roles can see that it
exists. The predictable result is a duplicate proposal for a term already in
review — and duplicates are the main data quality problem in termbases.

**Decision:** everyone can *find* entries in progress, clearly badged as not
yet approved. Exports, the published glossary, and the default search scope
stay approved-only. The Viewer role in `REQUIREMENTS.md` was amended
accordingly.

**Consequences:** `notes` on `TermEntry` is described as "internal remarks"
and would now be readable by Viewers. Either it stays visible to editorial
roles only — the safer reading of "internal" — or the field is renamed. To be
settled when the API's field-level visibility is built.

This also makes the duplicate hint (D12) work as intended: it can only warn
about entries the user is allowed to see.

---

## D11 — Import and workflow

**Status:** Proposed

The import formats are specified; the status of imported entries is not.
Both obvious answers fail: importing as *Approved* floods the termbase with
unreviewed content, importing as *Proposed* leaves someone approving 500
entries one at a time.

**Recommendation:** the importer chooses the target status per import run
("adopt as approved" for a migrated legacy glossary vs. "queue for review"),
with the choice recorded on the entries via `origin: import`. Bulk approval
in the review queue is required for v1.0, not v1.1 — the import creates the
need long before AI extraction does.

---

## D12 — Entry management views

**Status:** Proposed

`REQUIREMENTS.md` specifies search, filters, and the review queue. It does
not specify a list view, which is where managing entries actually happens.
Sorting, pagination, saved views, bulk selection, and any aggregate view are
absent.

**Recommendation:**

- **Concept-centric list**, one row per concept, one column per configured
  language, with the per-language status shown in the cell. A term with a
  German entry approved and no English one is then visible at a glance. A
  flat per-term list shows the same concept twice and loses the connection.
- **Gap filter** — "language missing". Filters work on what exists; the most
  common management question is about what does not.
- **Review queue defaults to what my role can act on**, rather than offering
  a role filter the user has to set first. A reviewer opening the queue
  should not first wade past 200 drafts that are not theirs.
- **Bulk selection** with the transitions the role permits — deferred to v1.1,
  where it joins AI batch review. This holds together only because the
  importer picks its target status per run (D11): without that, v1.0 would
  have no answer for approving a migrated glossary. If D11 changes, bulk
  selection has to move back into v1.0.
- **Duplicate hint at creation** — a similarity check on term and synonyms
  while typing, showing existing entries including unapproved ones (D10).
- **"My proposals"** — a contributor needs to see the fate of what they
  submitted. Notifications are roadmapped for v3.0; a list view of one's own
  entries and their status covers the need for v1.0 without any
  notification infrastructure.

---

## D13 — Date filter semantics

**Status:** Proposed

"Filter by date range" does not say created or changed.

**Recommendation:** both, selectable, defaulting to changed — "what moved
recently" is the more common question. Requires `updated_at` on `TermEntry`,
which the current model only has on `ConceptEntry` even though the change
history tracks term modifications.

---

## D14 — Content languages: fixed or configurable

**Status:** Accepted — configurable from v1.0 (2026-08-03)

`REQUIREMENTS.md` said three incompatible things: the setup wizard configures
"workspace name and languages", v1.0 promises "DE + EN baseline, extensible to
more languages", and v2.0 lists "Additional languages beyond DE + EN" as a
feature still to come.

It also used one word for two things. "Languages: German (DE) and English (EN)
— selectable per user" under UI is the *interface* language. The languages a
term is written in are a different axis entirely: a user reading the interface
in German still maintains English terms.

**Decision:** content languages are configured per workspace and can be
changed after setup. `TermEntry.language` references the configured set rather
than a fixed enum. The interface ships in DE and EN, chosen per user, and that
is what v2.0's roadmap entry now refers to.

**Consequences:** the term list renders one column per configured language, so
the view adapts instead of hard-coding two. Removing a language that still has
entries needs a rule — proposal: block it and point at the affected entries,
rather than cascading a delete. Language codes stay ISO 639-1 and are
validated against it, so the configured set cannot drift into free text.

---

## D15 — Authentication

**Status:** Accepted — local accounts with session cookie (2026-08-03)

`REQUIREMENTS.md` specifies six roles and "create initial Admin account", but
says nothing about how anyone signs in — no mention of passwords, sessions,
tokens, or external identity providers anywhere in the document.

**Decision:** local accounts. Passwords hashed with Argon2id, authentication
by HTTP-only session cookie, accounts created by an Admin. The setup wizard
creates the first Admin. No self-registration: a self-hosted termbase with an
open signup form is a liability, and inviting colleagues is a rare enough
action to stay manual.

**Consequences:** the `User` entity carries email (as the login), display
name, password hash, role, and active flag. `created_by` and `assignee`
reference it.

Adding OIDC later is additive — nullable `issuer` and `subject` columns plus
a callback route — so this is not a dead end. Session storage starts in the
database, which keeps the deployment to one container without Redis.

---

## D16 — Full-text search across two database backends

**Status:** Accepted — portable implementation for v1.0 (2026-08-03)

Search has to cover terms, definitions, synonyms, and NoGo alternatives, on
both SQLite and PostgreSQL. The two have nothing in common here: SQLite offers
FTS5 virtual tables, PostgreSQL `tsvector` with language-aware stemming.

**Decision:** one portable implementation for v1.0 — normalised, case- and
diacritic-insensitive matching on prefixes and substrings, behind a service
interface so the backend can be swapped without touching callers.

**Consequences:** no stemming and no relevance ranking in v1.0. For German
compounds this is a real limitation, and it is the reason the interface exists
— PostgreSQL `tsvector` is the obvious upgrade once search quality becomes the
complaint. The decisive argument against splitting now is support: the same
query returning different results depending on the backend is a problem nobody
wants to debug across two engines.

Search must respect D10 — entries in progress are findable and badged, while
exports and the published glossary stay approved-only.

---

## D17 — How a concept's status is derived

**Status:** Proposed — implemented as recommended (2026-08-03)

D1 put the review status on the term entry, which left open what a concept
shows when its languages disagree.

**Decision:** the lowest status across the concept's entries. German approved
and English still a draft makes the concept a draft, so a filter for "not
finished" finds everything that still needs work — the question the term list
exists to answer.

Two refinements the naive rule gets wrong:

- **A missing language is a gap, not a status.** It does not enter the
  calculation at all; the gap filter is what surfaces it.
- **Rejected sits outside the scale.** One rejected translation must not make
  a concept with an approved German entry look rejected, so rejected entries
  are skipped — unless every entry is rejected, in which case the concept is.

**Consequences:** the roll-up is computed, never stored, so it cannot drift
out of sync with the entries. Sorting the term list by status therefore cannot
use a column, which is fine at the sizes a termbase reaches.

---

## D18 — Who sees internal notes

**Status:** Proposed — implemented as recommended (2026-08-03)

`notes` is described as "internal remarks", but D10 made entries in progress
visible to every role, which would have exposed them.

**Decision:** visible from Editor upward. Below that the field is **blanked,
not omitted** — the response keeps the same shape for every caller.

Omitting the key per role was the first implementation and it did not survive
contact with FastAPI: the route's `response_model` filters the response
anyway, so the field vanished for everyone. Beyond that, a response whose keys
depend on the caller would not match what OpenAPI documents, and a null
reveals nothing about whether remarks exist.

**Consequences:** field-level visibility lives in `app/api/presenters.py`, in
one place, rather than being repeated per route.

---

## D19 — Editing an approved entry

**Status:** Proposed — implemented as recommended (2026-08-03)

Nothing said what happens when someone edits an entry that is already
approved. Silently keeping the badge would make "Approved" mean "somebody once
approved some version of this".

**Decision:** changing `term`, `definition`, `synonyms`, or
`nogo_alternatives` returns the entry to Draft, so it goes through review
again. Changing `context_example`, `source`, or `notes` does not — correcting
a source should not cost a review cycle.

**Consequences:** the split is a judgement call about which fields carry the
meaning a reviewer signed off on. It lives in `SUBSTANTIVE_FIELDS` in
`app/services/workflow.py`, as one list to change if the boundary turns out
to sit elsewhere in practice.
