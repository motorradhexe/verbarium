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

| Role | Permissions |
|---|---|
| **Viewer** | Read and search approved terms only |
| **Contributor** | Submit term proposals (lands in review queue) |
| **Editor** | Create, edit, and enrich term entries |
| **Reviewer** | Fachliche Prüfung — recommends approval or rejection |
| **Approver** | Final approval or rejection of terms |
| **Admin** | Full workspace configuration, user management, field schema |

### Approval Workflow

```
Contributor → Editor → Reviewer → Approver → Approved
                                            ↘ Rejected
```

Terms can also be created directly by Editors with status "Draft".

---

## Data Model

### Concept Entry (language-independent)

Each term is anchored to a language-independent concept. A concept holds all language-specific entries together.

| Field | Required | Type | Notes |
|---|---|---|---|
| `id` | Auto | UUID | |
| `domain` | No | Tag / Select | e.g. Marketing, Development, Legal |
| `status` | Yes | Enum | Draft, Proposed, In Review, Approved, Rejected |
| `created_by` | Auto | User ref | |
| `created_at` | Auto | Timestamp | |
| `updated_at` | Auto | Timestamp | |
| `custom_fields` | No | JSON | Workspace-defined additional fields |

### Term Entry (per language, linked to concept)

Each concept has one TermEntry per language.

| Field | Required | Type | Notes |
|---|---|---|---|
| `id` | Auto | UUID | |
| `concept_id` | Yes | FK | Links to ConceptEntry |
| `language` | Yes | ISO 639-1 | e.g. `de`, `en` |
| `term` | Yes | Text | Preferred term |
| `definition` | Yes | Text | Definition in this language |
| `synonyms` | No | Text[] | Permitted alternative forms |
| `nogo_alternatives` | No | Text[] | Forbidden alternatives — must not be used |
| `context_example` | No | Text | Example sentence or usage context |
| `source` | No | URL / Text | Origin of term or definition |
| `notes` | No | Text | Internal remarks |
| `created_by` | Auto | User ref | |
| `created_at` | Auto | Timestamp | |
| `custom_fields` | No | JSON | Workspace-defined additional fields |

### Change History

Every modification to a ConceptEntry or TermEntry is recorded:

- Timestamp
- User
- Field changed
- Previous value
- New value

History is read-only and visible to Editors, Reviewers, Approvers, and Admins.

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
User uploads a document (PDF, DOCX, MD, TXT) → AI extracts term candidates with suggested definitions → results appear in the Review Queue with status "AI Proposal". Batch review and approval supported.

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

### Export

| Format | Notes |
|---|---|
| CSV | All fields, filterable |
| TBX | Standards-compliant export for CAT tool integration |
| HTML Glossary | Formatted, publishable *(v2.0)* |
| PDF Glossary | Formatted *(v2.0)* |

---

## UI

- **Languages:** German (DE) and English (EN) — selectable per user
- **Search:** Full-text search across terms, definitions, synonyms, NoGo alternatives
- **Filter:** By language, domain, status, assignee, date range
- **Review Queue:** Dedicated view for items awaiting review or approval, filterable by role

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
- Auth + all six roles
- Workspace concept
- Concept/Term data model (DE + EN baseline, extensible to more languages)
- NoGo alternatives, synonyms
- Status workflow (Draft → Proposed → In Review → Approved / Rejected)
- Change history per term
- AI Pull Mode (single term enrichment)
- Search and filter
- Export: CSV + TBX
- Import: CSV, JSON, TBX
- UI in DE + EN
- Docker Compose, SQLite + PostgreSQL
- Setup Wizard with sample data
- MIT License

### v1.1 — Document Extraction
- Upload PDF, DOCX, MD, TXT
- AI extracts term candidates → Review Queue
- Batch review and approval

### v1.2 — External Sources
- Confluence API integration
- URL scraping
- OpenAPI / developer documentation parsing

### v2.0 — Platform
- Custom fields (configurable schema per workspace)
- Additional languages beyond DE + EN
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

- Domain-scoped permissions: define exact permission matrix for v2
- Confluence API authentication model
- Multi-instance vs. single-instance deployment for large organizations
- Offline/air-gapped support requirements

---

*Last updated: 2026-04-30*
