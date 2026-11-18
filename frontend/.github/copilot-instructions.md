# SEED Angular — Copilot Instructions

## Project Context

Angular frontend for the SEED Platform™ (Standard Energy Efficiency Data) — an Angular app
(standalone components, no NgModules) replacing the legacy AngularJS UI. Focused on building energy
data management, with key workflows around inventory, insights/reporting, data quality, and
analyses. Paired with a Django backend in the parent `seed` repo (this repo is a git submodule of
it), available at `../seed` locally or at https://github.com/SEED-platform/seed.

**Stack:** Angular 22 · TypeScript 6.0 · RxJS · TailwindCSS · Angular Material · Chart.js · Ag-Grid ·
Transloco (i18n) · pnpm

**Backend API (`/api/v3/` vs `/api/v4/`):** The Django backend exposes both versioned REST APIs.
The overwhelming majority of endpoints this app calls are **v3** — reuse an existing v3 endpoint
whenever one exists (the legacy AngularJS app at `seed/static/seed/` calls the same v3 endpoints
and is a good reference for request/response shape). **Do not modify v3 endpoints, and never add a
new v3 endpoint.** Only introduce or call a `/api/v4/` endpoint when a feature genuinely needs a
new backend endpoint with no v3 equivalent (see the existing v4 calls in `organization.service.ts`,
`analysis.service.ts`, `groups.service.ts`, `inventory.service.ts` for precedent) — don't default
to v4 just because it's newer.

---

## Setup & commands

Package manager is **pnpm** (a `preinstall` script fails under npm/yarn). Node 24.15+ (24.x) or
26+, pnpm >=12.

```bash
pnpm i                    # install
pnpm start                # dev server at localhost:4200 (proxies /api/ and /media/ to Django)
pnpm watch                # build through Django to ../../collected_static/ng-app, served at /ng-app/
pnpm build                # production build (AoT + template typecheck)
pnpm lint                 # eslint + prettier check + stylelint, in parallel
pnpm lint:fix             # auto-fix all three
pnpm test                 # ng test (Karma + Jasmine)
pnpm cspell "**/*"        # spell check (also enforced per-file by eslint via @cspell/eslint-plugin)
pnpm update-translations  # pull translations from Lokalise (needs .env with LOKALISE_TOKEN)
```

- Dev-server proxy target is the `SEED_HOST` env var (default `http://127.0.0.1:8000`), configured
  in `proxy.conf.mjs` / a `.env` file (see `.env.example`).
- Spelling: add legitimate domain-specific words to `.spelling.dic`, not inline ignore comments.
- **Lokalise is the source of truth** for translations — `update-translations` only *pulls*, it
  never pushes new keys.
- To run a single spec: `pnpm test --include='**/some.component.spec.ts'`.
- CI (`.github/workflows/ci.yml`) runs `pnpm install`, `pnpm lint`, headless `pnpm test`, and
  `pnpm build` on push/PR to `main`.
- Tell me what keys to add to Lokalise in a simple list and I will add them and run update-translations so the public/i18n/*.json files are updated.

---

## Architecture

### Directory layout
```
src/
  @seed/           # Self-contained framework layer (derived from the Fuse admin template)
    api/           #   backend HTTP access, one folder per REST resource:
                   #   <resource>.service.ts + <resource>.types.ts (organization, property,
                   #   cycle, column, dataset, inventory, salesforce, …)
    components/    #   reusable UI kit (ag-grid, alert, card, drawer, label, modal, page, …)
    services/      #   app-wide services (config, confirmation, loading, error, media, …)
    materials/     #   MaterialImports barrel re-exporting Angular Material modules
    directives/ guards/ pipes/ routing/ validators/ styles/ tailwind/
  app/             # The application itself
    core/          #   auth, icons, navigation, snack-bar, transloco wiring
    layout/        #   shell layout component + layouts/
    modules/       #   lazy-loaded feature areas: inventory, insights, datasets, data-quality,
                   #   organizations, analyses, auth, profile, api, main, …
    mock-api/      #   app-specific mock API
```

### API layer (`src/@seed/api/`)
Each domain folder exports a single `@Injectable({ providedIn: 'root' })` service that follows this
pattern:
- Private `BehaviorSubject`/`ReplaySubject` holds internal state; a public `<name>$` `Observable`
  (`.asObservable()`) is exposed for consumers.
- HTTP calls use `HttpClient` with `catchError` → `ErrorService.handleError()`.

### Routing
Routing is fully lazy: each feature exports a default `Routes` array (`<feature>.routes.ts`) loaded
via `loadChildren: () => import('app/modules/<feature>/<feature>.routes')` (see `app.routes.ts`).
All authenticated routes live under the `AuthGuard`-protected block. Polymorphic paths (e.g.
inventory `properties`/`taxlots`, org `data-quality`/`derived-columns` sub-types) use custom
`UrlSegment` matcher functions instead of static path strings. Place new sibling routes **before**
dynamic `:id` routes so they aren't swallowed by the id matcher, and add a matching entry to
`src/app/core/navigation/navigation.service.ts`.

### App wiring & imports
`app.config.ts` wires Transloco, a custom `TitleStrategy` (appends "- SEED Platform™"), a
Luxon-based Material `DateAdapter`, `provideAuth()`, `provideIcons()`, and `provideSEED(...)`
(defined in `src/@seed/seed.provider.ts`), which registers SEED-wide providers (confirmation
dialogs, loading/media/platform/splash-screen services, HTTP interceptors) and optionally the
mock-API interceptor for local dev without a live Django backend. `tsconfig.json` defines explicit
path aliases for `@seed`, `@seed/*`, and `app/*` under `src/` without the deprecated `baseUrl`
option. Avoid deep relative (`../../..`) imports across that boundary.

### State & organization context
No NgRx/store — state lives in services via `BehaviorSubject`/`ReplaySubject` streams; components
inject services and subscribe via the `async` pipe or `takeUntil` unsubscription.
`UserService.currentOrganizationId$` is the source of truth for the active org; most API services
subscribe to it (in the constructor) to set their local `orgId`.

---

## Linting & code style

Three linters run in parallel via `pnpm lint` (or `pnpm lint:fix` to auto-fix):

| Tool | Scope | Config |
|------|-------|--------|
| ESLint + `angular-eslint` (+ `@cspell/eslint-plugin`) | `**/*.ts`, `**/*.html` | `eslint.config.mjs` |
| Prettier | `src/**/*.html` (template formatting) | `.prettierrc` |
| Stylelint | `src/**/*.scss` | `.stylelintrc.js` |

**Key ESLint rules:**
- `@typescript-eslint/consistent-type-definitions` → `type` only (never `interface`)
- `@typescript-eslint/consistent-type-imports` → always `import type` for type-only imports
- `@typescript-eslint/naming-convention` → unused variables and private members prefixed `_`
- `@typescript-eslint/member-ordering` → class order: signature → field → constructor → accessor →
  static-method → decorated-method → public-method → private-method → method
- `unused-imports/no-unused-imports` → no dead imports
- `@angular-eslint/component-selector` → element selectors, kebab-case, prefixed `seed`/`auth`/`layout`
- `@angular-eslint/template/prefer-control-flow` → use `@if`/`@for`/`@switch`, not `*ngIf`/`*ngFor`
- Spelling is enforced per-file, so a lint failure can be a spelling issue — add words to
  `.spelling.dic`.

**Prettier (`.prettierrc`):** single quotes, no semicolons, 140-char print width, trailing commas,
2-space indent. Plugins auto-sort Tailwind classes and HTML attributes on fix.
**Stylelint:** SCSS standard. Class/id selectors must be kebab-case. Use
`rgb(var(--seed-*-rgb) / <alpha>)` for theme color tokens (the comma `rgba(var(...), a)` form is
blocked).
**EditorConfig:** 2-space indent, UTF-8, final newline, trim trailing whitespace.
**No pre-commit hooks** — run `pnpm lint` manually before committing. Import order/sorting and the
single-quote/no-semicolon style are eslint/prettier-enforced, so run `pnpm lint:fix` rather than
hand-formatting.

---

## Key conventions

### TypeScript & Angular
- **Standalone components only** (`@Component({ imports: [...] })`), with separate `.html`/`.scss`
  files and kebab-case selectors prefixed `seed`/`auth`/`layout`.
- Angular v22 defaults to OnPush change detection. Existing components explicitly using
  `ChangeDetectionStrategy.Eager` preserve pre-v22 behavior; don't remove it without making their
  state updates compatible with OnPush.
- **Never use `any`** — use explicit types or generics. Use `type` (not `interface`) for shapes.
- Inject dependencies with `inject()` at the field level, not constructor params; prefix private
  fields with `_` (e.g. `private _cycleService = inject(CycleService)`).
- Append `$` to any observable-holding variable (e.g. `items$`).
- Consume Angular Material via the `MaterialImports` barrel from `@seed/materials`, not individual
  Material modules.
- Pass typed objects to methods rather than multiple positional parameters.
- **Prefer readability over clever code.** Favor small, single-purpose methods/getters and early
  returns over dense one-liners, deep ternary chains, or clever RxJS chaining. Move non-trivial
  logic out of templates and into the component class. (This is also why the app avoids
  `lodash`/large utility libs — see `DEVELOPER.md`.)

### RxJS
- Unsubscribe via `private readonly _unsubscribeAll$ = new Subject<void>()` +
  `takeUntil(this._unsubscribeAll$)`, calling `.next()`/`.complete()` in `ngOnDestroy()`, or use
  `AsyncPipe`. `HttpClient` observables auto-complete and don't need manual unsubscription.
- Prefer Observables over Promises throughout.

### CSS & UI (TailwindCSS + Angular Material)
- Tailwind utility-first, mobile-first; **all new UI must support both light and dark themes**.
  Avoid broad/global SCSS — scope styles to the component.
- **Colors:** never hardcode hex/rgb in templates or SCSS. Use the semantic theme utilities the
  theme plugin generates from `tailwind.config.ts` (`text-primary-{50-900}`, `bg-card`,
  `text-secondary`, … — see `src/@seed/tailwind/plugins/theming.ts`), which already adapt
  light/dark; add a `dark:` variant only for a one-off the theme doesn't cover. On Material
  components, express intent with `color="primary"`/`"accent"`/`"warn"`. If you must reference a
  `--seed-*` variable in SCSS, use the `rgb(var(--seed-*-rgb) / <alpha>)` form.
- **Buttons:** primary/main actions are the theme's dark-blue primary with white text — get this by
  picking the Material variant that matches intent rather than hand-styling: `mat-flat-button` for
  a primary action, `mat-stroked-button` for secondary/cancel, `mat-icon-button` for icon-only,
  `mat-raised-button` for a destructive/`warn` action (see any `modal/*.component.html`). Let
  Material's own padding stand — don't add custom `padding`/`px-*`/`py-*` to resize a button. For a
  page's primary (and optional secondary) action, don't hand-roll a button at all — pass
  `action`/`actionIcon`/`actionText` (and `action2*`) into `<seed-page [config]="...">`, which
  renders it consistently (see `organizations/cycles/cycles.component.html`). Reuse the shared
  icon-button styles and icons for add/save/edit/delete so the look stays consistent across the site.
- **Icon sizing:** size `mat-icon` with the `icon-size-*` scale (e.g. `icon-size-4`, `icon-size-5`
  — defined in `src/@seed/tailwind/plugins/icon-size.ts`), not raw `w-*`/`h-*` classes.
- **Spacing:** prefer flex/grid `gap-*` between sibling elements over `space-x-*`/`space-y-*` or
  manual `mr-*`/`ml-*`; reach for the extended spacing scale in `tailwind.config.ts` rather than
  arbitrary-value classes like `p-[13px]`.
- **Angular Material form fields:** default appearance is `fill` (set globally in `seed.provider.ts`).
- **Images/media:** prefer `webp` or `svg` formats.

### Translations (Transloco)
Keys are the English strings themselves (identity translation — key = value in `en_US.json`); the
file is a flat `Record<string, string>` (no nesting).
- **In templates** use the structural directive (preferred):
  `<div *transloco="let t"><h2>{{ t('My Heading') }}</h2></div>`.
- **In components** import `TranslocoDirective` (not `TranslocoModule`); for programmatic strings
  (snackbars, titles) inject `TranslocoService` and call `.translate('My string')`.
- **Workflow:** new keys (key = English string, value = same string) must be registered in
  Lokalise; `pnpm update-translations` then pulls them and regenerates `public/i18n/*.json`. For
  local dev you can add a key to `public/i18n/en_US.json`, but the next pull overwrites that file,
  so report every key you added in the list described under Setup (see `docs/porting-forms.md` §9).
- Every user-facing string needs a key. `pnpm lint` does **not** catch missing keys — audit
  manually and **flag** any missing ones rather than silently shipping untranslated strings. When
  asked to list strings that lack translations, print a plain list (no quotation marks or colons)
  that's easy to copy/paste. Many existing modals hardcode English strings — that's tech debt, not
  the intended pattern; new modals should use `*transloco`.

### Empty & loading states
- When no program is selected/available, show only the "No Programs Found" empty state — do **not**
  render chart containers, chart grids, table sections, or loading spinners.
- Show loading indicators only when a valid program is present and a fetch is in progress.

### Accessibility
- Follow Section 508 rules; flag any accessibility concerns in your response.

---

## Change discipline
- Make minimal, targeted edits — don't reformat unrelated code or templates.
- Preserve existing component `@Input()`/`@Output()` contracts and routing behavior.
- Don't add dependencies without a clear need.
- Don't change API payload shapes without explicit approval.
- Don't delete or edit the legacy AngularJS code (`seed/static/seed/` in the parent repo) as part
  of a migration PR unless explicitly asked — it keeps serving `/app/` until the team retires it.

## Definition of done

```bash
pnpm lint      # eslint + prettier + stylelint (use pnpm lint:fix to auto-fix)
pnpm test      # Karma + Jasmine (CI runs it headless)
pnpm build     # AoT build + template typecheck
```

All three must pass for the files you touched. For anything interactive or backend-driven (a new page,
form, grid, drag-and-drop, filter, etc.) that isn't a pure refactor/style change, these checks are
necessary but **not sufficient** — lint and build don't run the code and the unit tests don't hit a real backend, so none of them catches a missing ag-grid
module registration, a wrong assumption about an API response's field names/shape, a route-param
reactivity bug, or a layout that only breaks with real data. Actually load the page against a live
backend with real seeded data and click through it with the Playwright MCP tools before calling the
work done — see [`docs/local-testing.md`](../docs/local-testing.md) for standing up a throwaway
backend + seed data in this environment (including gotchas already discovered). Publish a couple of
`browser_take_screenshot` captures (the overall page, plus the notable new interaction) to the PR
description.

Then summarize: what changed, why, files touched, validation run, and remaining risks. Keep PR
messages brief — a one-line title plus an itemized list of changes (no lengthy prose).

---

## Migrating legacy pages & forms

This app is actively replacing the legacy AngularJS 1.x frontend (`seed/static/seed/` in the parent
`seed` repo), often by several agents in parallel. Don't re-derive conventions from scratch each
time — follow the docs below and copy the canonical examples they reference:

- **[`docs/porting-forms.md`](../docs/porting-forms.md)** — the form-specific recipe: canonical
  full-page/modal form components to copy, the reusable service integration points (`CycleService`,
  `ColumnService`, `SnackBarService`, `ErrorService`, …), the validation/confirm/save flow, and the
  Transloco + Lokalise workflow. It also covers non-form interactive workspaces (e.g. the dual-grid
  drag-and-drop `datasets/pairing` page), so check its examples table for the closest match before
  assuming a `FormGroup`/save-flow shape.
- **[`docs/local-testing.md`](../docs/local-testing.md)** — how to actually run and click through
  what you built (throwaway backend + seeded data + the Playwright MCP tools). Required before
  calling a migration done — see "Definition of done" above.

Don't reimplement backend logic — the API usually already exists in `SEED-platform/seed`. When a
legacy page's own settings/config mechanism (e.g. a bespoke `localStorage`-backed column picker)
duplicates something this app already provides (e.g. the List View Profile selector), reuse the
existing mechanism.

**Intentionally not implementing:**
- **Inventory Plots** (`/{type}/plots`) — was unlinked and effectively unused in the old UI (a
  fixed 2×2 grid of hardcoded scatter plots); superseded by the Insights module.
- **Sub-organization management** (`/accounts/:org/sub_org`) — the project is moving toward access
  levels instead of sub-orgs.
- **Pairing settings** (`/data/pairing/:importfile_id/{type}/settings`) — the ported pairing
  workflow reuses the existing List View Profile column selector instead of a second, parallel
  column-config page.
