/** UI strings in German and English. → REQUIREMENTS.md, UI
 *
 *  A plain object rather than an i18n library: two languages and a few
 *  hundred strings do not need pluralisation rules, ICU messages, or a
 *  loader. `Translations` is derived from the German set, so a missing
 *  English key is a type error rather than a blank label at runtime.
 */

export const de = {
  appName: 'Verbarium',
  tagline: 'Terminologieverwaltung für Menschen, die Wörter ernst nehmen',

  common: {
    save: 'Speichern',
    cancel: 'Abbrechen',
    close: 'Schließen',
    loading: 'Wird geladen …',
    retry: 'Erneut versuchen',
    none: '—',
    optional: 'optional',
    language: 'Sprache',
    languages: 'Sprachen',
    of: 'von',
  },

  status: {
    draft: 'Entwurf',
    proposed: 'Vorgeschlagen',
    in_review: 'In Prüfung',
    approved: 'Freigegeben',
    rejected: 'Abgelehnt',
    missing: 'fehlt',
  },

  lifecycle: {
    active: 'Aktiv',
    deprecated: 'Veraltet',
  },

  role: {
    viewer: 'Leser',
    contributor: 'Einreicher',
    editor: 'Bearbeiter',
    reviewer: 'Prüfer',
    approver: 'Freigeber',
    admin: 'Administrator',
  },

  nav: {
    terms: 'Termliste',
    signOut: 'Abmelden',
    signedInAs: 'Angemeldet als',
  },

  login: {
    title: 'Anmelden',
    email: 'E-Mail-Adresse',
    password: 'Passwort',
    submit: 'Anmelden',
    failed: 'E-Mail-Adresse oder Passwort stimmt nicht.',
  },

  setup: {
    title: 'Verbarium einrichten',
    intro:
      'Diese Instanz ist noch leer. Lege den Arbeitsbereich, seine Sprachen und das erste Administratorkonto an.',
    workspaceName: 'Name des Arbeitsbereichs',
    contentLanguages: 'Inhaltssprachen',
    contentLanguagesHint:
      'Die Sprachen, in denen Terme geführt werden — nicht die Sprache der Oberfläche. Später änderbar.',
    addLanguage: 'Sprache hinzufügen',
    adminAccount: 'Erstes Administratorkonto',
    displayName: 'Anzeigename',
    email: 'E-Mail-Adresse',
    password: 'Passwort',
    passwordHint: 'Mindestens 12 Zeichen. Länge hilft, Sonderzeichen kaum.',
    submit: 'Einrichten',
    done: 'Fertig. Du kannst dich jetzt anmelden.',
  },

  list: {
    title: 'Termliste',
    search: 'Suchen',
    searchHint: 'Sucht in Termen, Definitionen, Synonymen und NoGo-Alternativen',
    filters: 'Filter',
    hasLanguage: 'Hat Sprache',
    missingLanguage: 'Sprache fehlt',
    missingLanguageHint: 'Findet Lücken — Concepts ohne Eintrag in dieser Sprache',
    status: 'Status',
    domain: 'Domäne',
    lifecycle: 'Lebenszyklus',
    clearFilters: 'Filter zurücksetzen',
    empty: 'Keine Einträge gefunden.',
    emptyUnfiltered: 'Noch keine Terme angelegt.',
    resultCount: 'Treffer',
    newConcept: 'Neuer Term',
    concept: 'Concept',
    domains: 'Domänen',
    updated: 'Geändert',
    previous: 'Zurück',
    next: 'Weiter',
  },

  concept: {
    back: 'Zurück zur Liste',
    notFound: 'Dieses Concept gibt es nicht.',
    domains: 'Domänen',
    noDomains: 'Keine Domäne zugeordnet',
    supersededBy: 'Ersetzt durch',
    deprecate: 'Außer Dienst stellen',
    reactivate: 'Wieder in Dienst nehmen',
    addLanguage: 'Sprache ergänzen',
    entries: 'Einträge',
    rollupHint: 'Der Status des Concepts ist der niedrigste seiner Sprachen.',
  },

  entry: {
    term: 'Term',
    definition: 'Definition',
    synonyms: 'Synonyme',
    nogo: 'NoGo-Alternativen',
    nogoHint: 'Formen, die nicht verwendet werden dürfen',
    contextExample: 'Verwendungsbeispiel',
    source: 'Quelle',
    notes: 'Interne Anmerkungen',
    notesHint: 'Nur für Bearbeiter und höher sichtbar',
    listHint: 'Mehrere Werte durch Komma trennen',
    edit: 'Bearbeiten',
    noDefinition: 'Noch keine Definition',
    assignee: 'Zuständig',
    unassigned: 'Niemandem zugewiesen',
    claim: 'Übernehmen',
    release: 'Abgeben',
    origin: 'Herkunft',
    originAi: 'KI-Vorschlag',
    originImport: 'Importiert',
    savedConflict:
      'Jemand anderes hat diesen Eintrag inzwischen geändert. Lade neu, bevor du speicherst.',
  },

  workflow: {
    submit: 'Zur Prüfung einreichen',
    start_review: 'Prüfung beginnen',
    request_changes: 'Überarbeitung erbitten',
    approve: 'Freigeben',
    reject: 'Ablehnen',
    commentLabel: 'Begründung',
    commentRequired: 'Ablehnung und Überarbeitung brauchen eine Begründung.',
    comments: 'Anmerkungen aus der Prüfung',
    noComments: 'Noch keine Anmerkungen.',
    history: 'Änderungsverlauf',
    noHistory: 'Noch keine Änderungen aufgezeichnet.',
    created: 'angelegt',
    changedFrom: 'von',
    changedTo: 'auf',
  },

  errors: {
    generic: 'Da ist etwas schiefgegangen.',
    offline: 'Der Server ist nicht erreichbar.',
    forbidden: 'Dafür reicht deine Rolle nicht.',
  },
} as const

/** Widens the literal types `as const` produces back to `string`, keeping the
 *  shape. Without this, `Translations` would demand the German wording in
 *  every language; with it, a missing or misspelled key is still a type error
 *  while the values stay free. */
type Widen<T> = { [K in keyof T]: T[K] extends string ? string : Widen<T[K]> }

/** The English set has to cover exactly the same keys. */
export type Translations = Widen<typeof de>

export const en: Translations = {
  appName: 'Verbarium',
  tagline: 'Terminology Management for People Who Care About Words',

  common: {
    save: 'Save',
    cancel: 'Cancel',
    close: 'Close',
    loading: 'Loading …',
    retry: 'Try again',
    none: '—',
    optional: 'optional',
    language: 'Language',
    languages: 'Languages',
    of: 'of',
  },

  status: {
    draft: 'Draft',
    proposed: 'Proposed',
    in_review: 'In review',
    approved: 'Approved',
    rejected: 'Rejected',
    missing: 'missing',
  },

  lifecycle: {
    active: 'Active',
    deprecated: 'Deprecated',
  },

  role: {
    viewer: 'Viewer',
    contributor: 'Contributor',
    editor: 'Editor',
    reviewer: 'Reviewer',
    approver: 'Approver',
    admin: 'Admin',
  },

  nav: {
    terms: 'Terms',
    signOut: 'Sign out',
    signedInAs: 'Signed in as',
  },

  login: {
    title: 'Sign in',
    email: 'Email address',
    password: 'Password',
    submit: 'Sign in',
    failed: 'That email address or password is not right.',
  },

  setup: {
    title: 'Set up Verbarium',
    intro:
      'This instance is empty. Create the workspace, its languages, and the first admin account.',
    workspaceName: 'Workspace name',
    contentLanguages: 'Content languages',
    contentLanguagesHint:
      'The languages terms are written in — not the interface language. Changeable later.',
    addLanguage: 'Add a language',
    adminAccount: 'First admin account',
    displayName: 'Display name',
    email: 'Email address',
    password: 'Password',
    passwordHint: 'At least 12 characters. Length helps; special characters barely do.',
    submit: 'Set up',
    done: 'Done. You can sign in now.',
  },

  list: {
    title: 'Terms',
    search: 'Search',
    searchHint: 'Searches terms, definitions, synonyms, and NoGo alternatives',
    filters: 'Filters',
    hasLanguage: 'Has language',
    missingLanguage: 'Language missing',
    missingLanguageHint: 'Finds gaps — concepts without an entry in this language',
    status: 'Status',
    domain: 'Domain',
    lifecycle: 'Lifecycle',
    clearFilters: 'Clear filters',
    empty: 'Nothing matches those filters.',
    emptyUnfiltered: 'No terms yet.',
    resultCount: 'results',
    newConcept: 'New term',
    concept: 'Concept',
    domains: 'Domains',
    updated: 'Changed',
    previous: 'Previous',
    next: 'Next',
  },

  concept: {
    back: 'Back to the list',
    notFound: 'There is no such concept.',
    domains: 'Domains',
    noDomains: 'No domain assigned',
    supersededBy: 'Superseded by',
    deprecate: 'Retire',
    reactivate: 'Put back in use',
    addLanguage: 'Add a language',
    entries: 'Entries',
    rollupHint: "A concept's status is the lowest of its languages.",
  },

  entry: {
    term: 'Term',
    definition: 'Definition',
    synonyms: 'Synonyms',
    nogo: 'NoGo alternatives',
    nogoHint: 'Forms that must not be used',
    contextExample: 'Usage example',
    source: 'Source',
    notes: 'Internal notes',
    notesHint: 'Visible to editors and above only',
    listHint: 'Separate several values with commas',
    edit: 'Edit',
    noDefinition: 'No definition yet',
    assignee: 'Assigned to',
    unassigned: 'Nobody',
    claim: 'Claim',
    release: 'Release',
    origin: 'Origin',
    originAi: 'AI suggestion',
    originImport: 'Imported',
    savedConflict: 'Someone else changed this entry. Reload before saving.',
  },

  workflow: {
    submit: 'Submit for review',
    start_review: 'Start review',
    request_changes: 'Request changes',
    approve: 'Approve',
    reject: 'Reject',
    commentLabel: 'Reason',
    commentRequired: 'Rejecting and requesting changes need a reason.',
    comments: 'Review comments',
    noComments: 'No comments yet.',
    history: 'Change history',
    noHistory: 'Nothing recorded yet.',
    created: 'created',
    changedFrom: 'from',
    changedTo: 'to',
  },

  errors: {
    generic: 'Something went wrong.',
    offline: 'The server is not reachable.',
    forbidden: 'Your role is not enough for that.',
  },
}

export const LOCALES = { de, en } as const
export type Locale = keyof typeof LOCALES
