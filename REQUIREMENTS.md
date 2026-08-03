# Verbarium — Requirements

> Terminology Management for People Who Care About Words

> AI-ready terminology management. Not FULL-AI.

Verbarium is an open-source, self-hosted terminology management tool designed for technical writers, translators, and cross-functional teams. It supports configurable fields and workflows, multilingual term management, and optional AI-assisted term extraction and suggestion via user-provided API keys.

---

## Project Principles

- **Self-hosted first** — no SaaS, no cloud dependency, no external data exposure
- **AI-ready, not FULL-AI** — all features work without AI; AI enriches where configured
- **BYOK (Bring Your Own Key)** — users provide their own AI provider API keys; no AI costs for the tool operator
- **Open Source** — MIT License
- **Simple by default, configurable by need** — sensible defaults, extensible schema

---

## License

MIT License

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python / FastAPI |
| Frontend | React / Vite |
| Database | SQLite (default) or PostgreSQL (team deployments) |
| Deployment | Docker Compose |
| AI Integration | Pluggable provider interface (BYOK) |

SQLite and PostgreSQL are both supported and selectable via configuration. SQLite is the default for single-user and development setups; PostgreSQL is recommended for team deployments.

---

## Roles

Six roles with escalating permissions. Roles are global per workspace in v1; domain-scoped permissions are planned for v2.

One instance holds exactly one workspace. Workspace configuration — name,
languages, AI provider — is a single settings record, and a second team runs a
second instance. → D8

| Role | Permissions |
|---|---|
| **Viewer** | Read and search. Entries in progress are visible and clearly marked as not yet approved; exports and the published glossary contain approved entries only. → D10 |
| **Contributor** | Submit term proposals (lands in review queue) |
| **Editor** | Create, edit, and enrich term entries |
| **Reviewer** | Fachliche Prüfung — recommends approval or rejection |
| **Approver** | Final approval or rejection of terms |
| **Admin** | Full workspace configuration, user management, field schema |

### Authentication

Local accounts: email as the login, passwords hashed with Argon2id,
authentication by HTTP-only session cookie with session state in the database.
Accounts are created by an Admin — there is no self-registration. The setup
wizard creates the first Admin account.

External identity providers (OIDC) are not part of v1.0 and can be added
without schema changes to existing data. → D15

### Approval Workflow

```
Contributor → Editor → Reviewer → Approver → Approved
                    ↖                       ↘ Rejected
                     ← Changes requested ←
```

Terms can also be created directly by Editors with status "Draft".

*Changes requested* returns an entry to Draft for rework, keeping the review
thread attached. *Rejected* means the concept does not belong in the termbase
at all. Both require a comment stating the reason — the change history records
values, not reasoning. → `docs/DATA-MODEL-DECISIONS.md` D6

---

## Data Model

Decisions marked → Dn are recorded in `docs/DATA-MODEL-DECISIONS.md`; open
ones are to be settled before the first migration ships.

### Concept Entry (language-independent)

Each term is anchored to a language-independent concept. A concept holds all language-specific entries together.

| Field | Required | Type | Notes |
|---|---|---|---|
| `id` | Auto | UUID | |
| `domains` | No | Tag[] | Multi-valued, stored as a join table — e.g. Marketing, Development, Legal → D9 |
| `lifecycle` | Yes | Enum | Active, Deprecated → D7 |
| `superseded_by` | No | FK | Successor concept when deprecated → D7 |
| `created_by` | Auto | User ref | |
| `created_at` | Auto | Timestamp | |
| `updated_at` | Auto | Timestamp | |
| `version` | Auto | Integer | Optimistic locking — rejects writes based on stale data → D4 |
| `custom_fields` | No | JSON | Workspace-defined additional fields |

Review status sits on the term entry, not here: each language runs its own
review cycle, and the concept shows the roll-up ("2 of 3 languages approved").
→ D1

### Term Entry (per language, linked to concept)

Each concept has one TermEntry per language.

| Field | Required | Type | Notes |
|---|---|---|---|
| `id` | Auto | UUID | |
| `concept_id` | Yes | FK | Links to ConceptEntry |
| `language` | Yes | ISO 639-1 | e.g. `de`, `en` |
| `term` | Yes | Text | Preferred term |
| `definition` | To approve | Text | Definition in this language. Required to reach Approved, not on creation → D5 |
| `synonyms` | No | Text[] | Permitted alternative forms |
| `nogo_alternatives` | No | Text[] | Forbidden alternatives — must not be used |
| `context_example` | No | Text | Example sentence or usage context |
| `source` | No | URL / Text | Origin of term or definition |
| `notes` | No | Text | Internal remarks |
| `status` | Yes | Enum | Draft, Proposed, In Review, Approved, Rejected → D1 |
| `assignee` | No | User ref | Who is currently handling this entry → D2 |
| `origin` | Auto | Enum | manual, ai, import — how the entry came to be → D3 |
| `created_by` | Auto | User ref | |
| `created_at` | Auto | Timestamp | |
| `updated_at` | Auto | Timestamp | |
| `version` | Auto | Integer | Optimistic locking → D4 |
| `custom_fields` | No | JSON | Workspace-defined additional fields |

### Change History

Every modification to a ConceptEntry or TermEntry is recorded:

- Timestamp
- User
- Field changed
- Previous value
- New value

History is read-only and visible to Editors, Reviewers, Approvers, and Admins.

### Review Comments

Separate from the change history, which is automatic and records values only.
Comments carry the reasoning: entry reference, author, timestamp, text. A
comment is mandatory when requesting changes or rejecting an entry. → D6

### Custom Fields

Workspace Admins can define additional fields per entry type (Concept or Term). Field types: text, long text, select, multi-select, boolean, URL, date. Custom fields are stored as JSON and rendered dynamically in the UI.

---

## AI Integration

### Principle: AI-ready, not FULL-AI

All core features (term entry, workflow, search, export) work without any AI provider configured. AI features are visibly inactive when no provider is set, with a clear setup prompt — not an error state.

### BYOK — Bring Your Own Key

API keys are configured per workspace by the Admin. Keys are stored encrypted and never exposed to the frontend. All AI calls go through the backend.

### Pluggable Provider Interface

The backend implements a single AI provider interface. Providers are selectable via workspace configuration:

| Provider | Key required | Cost |
|---|---|---|
| Anthropic Claude | Yes | Pay-per-use |
| OpenAI | Yes | Pay-per-use |
| Ollama (local) | No | Free |
| Mistral API | Yes | Free tier available |
| Groq | Yes | Free tier available |

New providers can be added without changing core application logic.

### AI Modes

**Pull Mode — single term enrichment**
User enters a term → AI suggests definition, translation, synonyms, context example, source hints. User reviews and accepts, edits, or discards each suggestion individually.

**Push Mode — document extraction**
User uploads a document (PDF, DOCX, MD, TXT) → AI extracts term candidates with suggested definitions → results appear in the Review Queue with status *Proposed* and origin *ai*, badged accordingly in the UI. Batch review and approval supported.

Origin is tracked as its own field rather than as a status, so that an entry
stays identifiable as an AI suggestion after it moves through the workflow.
→ D3

**Push Mode — external source extraction** *(v1.2)*
User provides a URL, Confluence space, or OpenAPI spec → same extraction flow as document upload.

All AI-generated entries enter the standard approval workflow. No AI output is approved automatically.

---

## Import / Export

### Import

| Format | Notes |
|---|---|
| CSV | Column mapping configurable at import time |
| JSON | Structured term objects |
| TBX | TermBase eXchange — standard from CAT tools (memoQ, Trados) |

The importer chooses the target status per run — "adopt as approved" for a
migrated legacy glossary, or "queue for review". Imported entries carry
origin *import*. → D11

### Export

| Format | Notes |
|---|---|
| CSV | All fields, filterable |
| TBX | Standards-compliant export for CAT tool integration |
| HTML Glossary | Formatted, publishable *(v2.0)* |
| PDF Glossary | Formatted *(v2.0)* |

---

## UI

- **Interface language:** German (DE) and English (EN) — selectable per user. Distinct from the languages terms are written in. → D14
- **Content languages:** Configured per workspace, changeable after setup, validated against ISO 639-1. The term list renders one column per configured language. → D14
- **Search:** Full-text search across terms, definitions, synonyms, NoGo alternatives. One portable implementation for both database backends in v1.0 — normalised prefix and substring matching, without stemming or ranking. → D16
- **Filter:** By language, domain, status, assignee, date range (created or changed, defaulting to changed → D13)

### Entry Management

Looking terms up and maintaining them are different jobs. These views serve
the second. → D12

- **Term list:** One row per concept, one column per configured language, with
  the per-language status in the cell. Coverage and gaps are then visible at a
  glance instead of requiring a query per language.
- **Gap filter:** "language missing" — filters otherwise only work on what
  exists, while the common management question is about what does not.
- **Bulk selection:** Apply the transitions the user's role permits to a
  selection. Deferred to v1.1 alongside AI batch review — in v1.0 the import
  covers the mass case by choosing its target status per run (D11).
- **Duplicate hint:** While entering a new term, show existing entries with
  similar terms or synonyms, including unapproved ones. Duplicates are the
  main data quality problem in a termbase.
- **My proposals:** Contributors see the status of what they submitted.
  Covers the feedback need without notification infrastructure, which is
  roadmapped for v3.0.

### Review Queue

Dedicated view for items awaiting review or approval. Defaults to what the
signed-in user's role can act on right now, rather than offering a role filter
that has to be set first. Supports claiming an entry (`assignee`), so parallel
reviewers do not duplicate each other's work. → D2, D12

---

## Setup & Onboarding

- Docker Compose setup with single command startup
- First-run Setup Wizard:
  - Create initial Admin account
  - Configure workspace name and languages
  - Optional: configure AI provider
- Sample dataset included: coffee terminology (DE + EN), covering multiple domains and demonstrating all field types and statuses

---

## Roadmap

### v1.0 — Foundation
- Auth: local accounts, session cookie, all six roles
- Workspace concept — one workspace per instance
- Concept/Term data model, content languages configurable per workspace
- NoGo alternatives, synonyms
- Status workflow per language (Draft → Proposed → In Review → Approved / Rejected), with a rework loop and mandatory comment on rejection
- Change history per term, review comments
- AI Pull Mode (single term enrichment)
- Search and filter
- Entry management: term list with language columns, gap filter, duplicate hint, "my proposals"
- Review queue scoped to the signed-in role, with assignment
- Deprecation with successor reference
- Entries in progress visible to all roles, marked as unapproved
- Export: CSV + TBX
- Import: CSV, JSON, TBX
- Interface in DE + EN
- Docker Compose, SQLite + PostgreSQL
- Setup Wizard with sample data
- MIT License

### v1.1 — Document Extraction
- Upload PDF, DOCX, MD, TXT
- AI extracts term candidates → Review Queue
- Batch review and approval, including bulk transitions in the term list

### v1.2 — External Sources
- Confluence API integration
- URL scraping
- OpenAPI / developer documentation parsing

### v2.0 — Platform
- Custom fields (configurable schema per workspace)
- Additional interface translations beyond DE + EN (content languages are already configurable in v1.0 → D14)
- Search with stemming and relevance ranking, backend-specific → D16
- Domain-scoped role permissions
- Glossary export: HTML + PDF
- REST API for external tool integration

### v3.0 — Ecosystem
- Git integration (Docs-as-Code, terminology in repository)
- CAT tool connectors (memoQ, Trados)
- Plugin system
- Webhooks and notifications on status changes

---

## Open Questions / TBD

Data model and entry management questions are tracked with their options,
recommendations, and outcomes in `docs/DATA-MODEL-DECISIONS.md`. D1, D7–D10 and
D14–D16 are settled; D2–D6 and D11–D13 stand as recommendations.

Still open:

- Domain-scoped permissions for v2: with multi-valued domains (D9), define
  whether access requires one matching domain or all of them
- Confluence API authentication model
- Offline/air-gapped support requirements

---

*Last updated: 2026-08-03*
