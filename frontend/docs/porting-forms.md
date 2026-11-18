# Porting Forms from Legacy AngularJS → SEED Angular

A repeatable recipe for porting a legacy AngularJS form/screen from
[`SEED-platform/seed`](https://github.com/SEED-platform/seed) into this Angular v22 app.

> Read [`DEVELOPER.md`](../DEVELOPER.md) first for the general coding standards, and
> [`MIGRATION.md`](../MIGRATION.md) for the page/route-level migration playbook and checklist.
> This guide is the form-specific layer on top of both. Follow it so every agent produces
> consistent output.

---

## 1. Before you write code

1. **Find the legacy source of truth.** Fetch the legacy controller + partial for behavior
   reference (do not translate line-by-line — port the *behavior*):
   ```bash
   gh api repos/SEED-platform/seed/contents/<path-to-controller>.js?ref=<branch> --jq .content | base64 -d
   gh api repos/SEED-platform/seed/contents/<path-to-partial>.html?ref=<branch> --jq .content | base64 -d
   ```
2. **Confirm the backend exists.** In almost all cases the API already exists in
   `SEED-platform/seed`. Do **not** reimplement backend logic — just call it.
3. **Pick the shape:** a **full-page form** (its own route), a **modal form** (dialog), or — if
   the legacy page isn't really a form (no single record + save action, e.g. a dual-grid
   drag-and-drop workspace) — the closest **interactive workspace** example instead. Use the
   matching canonical example below.
4. **Plan mode first** for non-trivial ports: list files to add/change, the component
   structure, validation, and the save flow — then implement.

---

## 2. Canonical examples (copy these)

| Need | Reference file |
| --- | --- |
| Full-page form + route + services + confirm dialog | `src/app/modules/inventory/create/inventory-create.component.ts` / `.html` |
| Modal form (dialog + reactive form + service) | `src/app/modules/inventory-detail/notes/modal/form-modal.component.ts` |
| Confirm / delete dialog | `src/@seed/components/delete-modal/delete-modal.component.ts` |
| Modal header | `src/@seed/components/modal/modal-header.component.ts` (`ModalHeaderComponent`) |
| Page shell | `PageComponent` (`seed-page`) from `@seed/components` |
| Inline validation errors | `AlertComponent` (`seed-alert`) from `@seed/components` |
| Access-level selectors | `src/app/modules/inventory/**/ali-change-modal.component.ts` |
| Property/Tax Lot tab switcher on a page | `InventoryTabComponent` (`seed-page-inventory-tab`) from `@seed/components` |
| Interactive dual-grid workspace (no form/save flow — drag rows between two `ag-grid` grids to associate them, custom cell-renderer chips with click-to-remove) | `src/app/modules/datasets/pairing/pairing.component.ts` / `.html` |

**Cross-grid drag-and-drop (`ag-grid` Community, no Enterprise needed):** to let a user drag rows
from one grid and drop them onto rows of a second grid (see `PairingComponent`), add a narrow
`{ field: 'drag', rowDrag: true, pinned: 'left' }` column to the *source* grid, then once both
grids are ready:
```ts
const dropZoneParams = targetGridApi.getRowDropZoneParams({
  onDragStop: (params) => { /* params.node.data = dragged row, params.overNode?.data = target row */ },
})
sourceGridApi.addRowDropZone(dropZoneParams)
```
Don't set `rowDragManaged: true` if the dragged row should stay in the source grid after the drop
(e.g. pairing a property that can still be re-paired) — that flag is for same-grid reordering and
will otherwise remove the row from its source list.

---

## 3. Reusable integration points

All API services follow the **private `BehaviorSubject` → public `$` Observable** pattern and are
re-exported from `@seed/api`.

| Concern | Service (`@seed/api`) | Key members |
| --- | --- | --- |
| Current org id | `UserService` | `currentOrganizationId$` |
| Cycles | `CycleService` | `cycles$`, `getCycles(orgId)` |
| Columns | `ColumnService` | `propertyColumns$`, `taxLotColumns$`, `getPropertyColumns(orgId)`, `getTaxLotColumns(orgId)` |
| Access level tree | `OrganizationService` | `accessLevelTree$` (`.accessLevelNames`), `accessLevelInstancesByDepth$`, `getMatchingCriteriaColumns(orgId)` |
| Column list profiles | `InventoryService` | `getColumnListProfiles(profileLocation, inventoryType, brief?)` |
| Feedback | `SnackBarService` (`app/core/snack-bar/snack-bar.service`) | `success()`, `info()`, `warning()`, `alert()` |
| Errors | `ErrorService` (`@seed/services`) | `handleError(error, message)` — used inside service `catchError` |
| Dialogs | `@angular/material/dialog` `MatDialog` | open a modal that renders `ModalHeaderComponent` |

**Access-level selector pattern** (authoritative):
```ts
const depth = this.accessLevelNames.findIndex((name) => name === selectedLevel)
this.accessLevelInstances = this.accessLevelInstancesByDepth[depth] ?? []
```
`accessLevelInstancesByDepth` is **0-based** and aligns directly with `accessLevelNames`
(the root is depth 0). Do not copy the legacy AngularJS `index + 1` offset.

---

## 4. Adding a new service method

Put HTTP calls in the relevant `@seed/api` service, typed, with centralized error handling:

```ts
createThing(data: ThingCreate, inventoryType: InventoryType): Observable<ThingResponse> {
  const url = `/api/v3/${inventoryType}/form_create/`
  const params: Record<string, number> = { organization_id: this.orgId }
  return this._httpClient.post<ThingResponse>(url, data, { params }).pipe(
    catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error creating thing')),
  )
}
```

- Add request/response `type`s to the feature's `*.types.ts` and export as needed.
- Prefer a single typed payload object over multiple positional args.
- Do **not** manually unsubscribe from `HttpClient` calls (they complete on their own).

---

## 5. Component skeleton (full-page form)

```ts
import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { Component, inject } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms'
import { ActivatedRoute, Router } from '@angular/router'
import { Subject, takeUntil } from 'rxjs'
import { /* ...services... */ } from '@seed/api'
import { AlertComponent, PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-<feature>',
  templateUrl: './<feature>.component.html',
  imports: [AlertComponent, CommonModule, MaterialImports, PageComponent, ReactiveFormsModule],
})
export class FeatureComponent implements OnInit, OnDestroy {
  private _route = inject(ActivatedRoute)
  private _router = inject(Router)
  private _snackBar = inject(SnackBarService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  form = new FormGroup({
    name: new FormControl<string | null>(null, Validators.required),
  })

  ngOnInit(): void { /* read route params, load data via combineLatest(...).pipe(take(1)) */ }

  save(): void { /* confirm dialog → service call → snackbar + navigate */ }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
```

Template essentials (`<feature>.component.html`):
```html
<seed-page [config]="{ title: t('Create Thing'), titleIcon: 'fa-solid:building' }">
  <div class="p-6 sm:p-10" *transloco="let t">
    @if (formErrors.length) {
      <seed-alert type="error" appearance="outline">…</seed-alert>
    }
    <form [formGroup]="form"> … </form>
  </div>
</seed-page>
```

**Member ordering** (enforced by eslint): fields (including arrow-function fields) come before
methods; public methods before `private _*` methods. Keep all private helpers at the bottom.

---

## 6. Modal form skeleton

Mirror `notes/modal/form-modal.component.ts`:

```ts
export class FeatureModalComponent implements OnDestroy {
  private _dialogRef = inject(MatDialogRef<FeatureModalComponent>)
  data = inject(MAT_DIALOG_DATA) as { orgId: number; /* … */ }
  form = new FormGroup({ /* … */ })

  onSubmit() {
    this._service.save(/* … */).pipe(takeUntil(this._unsubscribeAll$), tap(() => this.close(true))).subscribe()
  }
  close(success = false) { this._dialogRef.close(success) }
}
```
Render `ModalHeaderComponent` at the top of the modal template (title + close button).

---

## 7. Validation & save flow

- Build validation into the reactive form (`Validators`) plus a computed `formErrors: string[]`
  for cross-field/business rules; disable the submit button while invalid or in-flight.
- Surface errors via `AlertComponent` (list) and keep the submit button
  `[disabled]="!valid || formErrors.length > 0 || saving"`.
- **Confirm before mutating:** open a confirm dialog (`MatDialog`), act on the boolean result.
- **On success:** `SnackBarService.success(...)` and navigate to the created/updated record
  (e.g. `this._router.navigate(['/', type, viewId])`).
- **On no-op / duplicate:** `SnackBarService.info(...)`, do not navigate.
- **On error:** already surfaced by `ErrorService.handleError` inside the service `catchError`.

> Convention decided during the inventory-create port: **replace legacy "success modal that
> offers to view the record" with a success snackbar + automatic navigation.** Keep the
> pre-save confirm dialog. Reuse this behavior for consistency.

---

## 8. Routing & navigation

1. Add the route to the feature's `*.routes.ts`. Place static routes (e.g. `create`, `settings`)
   **before** the dynamic `:id` route so they aren't swallowed by the id matcher.
   ```ts
   { path: 'create', title: 'Create Thing', component: FeatureComponent },
   ```
2. Add a nav entry in `src/app/core/navigation/navigation.service.ts` (link, title,
   `icon: 'fa-solid:…'`, `type: 'basic'`, `exactMatch: true`). Verify the icon exists in the
   `public/icons/fa-solid.svg` sprite.

---

## 9. Translations (Transloco + Lokalise)

**Lokalise is the source of truth.** `pnpm update-translations` only **pulls** the bundle from
Lokalise and overwrites `public/i18n/*.json` — it does **not** push new keys. So new strings must
be registered in Lokalise; do not hand-maintain the JSON as the system of record.

**Key convention:** the **English text is the key** (e.g. `t('Add Column')`). Longer/legacy
messages sometimes use `UPPER_SNAKE` keys — reuse an existing key if one already fits (search
`public/i18n/en_US.json` first). Interpolate with `{{param}}`.

**In templates** — wrap the scope and use the `t` function (or the `transloco` pipe):
```html
<seed-page *transloco="let t" [config]="{ title: t(titleKey), titleIcon: 'fa-solid:building' }">
  <span>{{ t('Save') }}</span>
  <span>{{ t('Successfully created {{type}}', { type: typeLabel }) }}</span>
</seed-page>
```
`t` is in scope for the host element's own bindings (e.g. `[config]`), so you can put
`*transloco="let t"` directly on `seed-page`. Add `TranslocoDirective` (or `TranslocoPipe`) to
the component `imports`.

**In TypeScript** — for strings built in code (validation messages, dialog title/body, snackbars),
inject `TranslocoService` and call `translate`:
```ts
private _transloco = inject(TranslocoService)
// …
this._snackBar.success(this._transloco.translate('Successfully created {{type}}', { type }))
```

**Fallback behavior:** `fallbackLang` is `en_US`. A missing key renders as the **key text**
(English), but a missing *interpolated* key renders the literal `{{param}}`. So after adding
`t('…{{x}}')` strings, register them in Lokalise (or add them to `public/i18n/en_US.json` for
local dev — note that a later `update-translations` pull will regenerate that file).

**Gotcha — don't translate values used for data matching.** Keep raw API-facing values English.
Example from the inventory-create form: `displayType` (`'Property'` / `'Tax Lot'`) is compared
against `profile.inventory_type`, so it must stay English; the UI label is translated separately.

---

## 10. Definition of done

```bash
pnpm lint      # eslint + prettier + stylelint  (pnpm lint:fix auto-fixes most issues)
pnpm build     # AoT build + template typecheck
```

Both must pass for the files you touched. Common gotchas:
- **Union narrowing:** eslint/tsc won't narrow the *false* branch of `a && typeof a === 'object'`.
  Narrow with `typeof x === 'string'` first, or extract a helper that always returns the wanted type.
- **`no-base-to-string`:** don't `.toString()` a possibly-object value; use an explicit accessor.
- **Member ordering / naming:** fields before methods, public before private, `_` prefix on privates.
- Use **pnpm 12+** (there is a `pnpm-lock.yaml`); Node 24.15+ (24.x) or 26+ is required.

**Lint and build are not the finish line.** Neither one executes the component, so neither can
catch a missing ag-grid module registration, a wrong assumption about a live API response's
field names/shape, a route-param reactivity bug (Angular reuses component instances across
sibling routes — see the Pairing migration's tab-switch bug), or a layout that only breaks with
real data. Before considering the port done, actually run the page against a live backend with
real seeded data (both populated and empty/edge-case data, not just the happy path) and click
through the ported behavior with Playwright — see [`docs/local-testing.md`](local-testing.md) for
how to stand up a throwaway backend + test data in this environment.

---

## 11. Checklist (copy into your PR description)

- [ ] Legacy behavior reviewed (controller + partial)
- [ ] Standalone component(s) with `MaterialImports`, separate `.ts`/`.html`
- [ ] Reactive form with typed controls + validation + `formErrors` list
- [ ] Existing `@seed/api` service reused; new HTTP method typed with `ErrorService.handleError`
- [ ] Confirm dialog before mutate; success snackbar + navigate; info on no-op/duplicate
- [ ] All strings via Transloco (`t('…')`)
- [ ] Route added before `:id`; nav entry added; icon verified in sprite
- [ ] `pnpm lint` and `pnpm build` pass
- [ ] Live-tested against a real backend with seeded data via Playwright (see
      `docs/local-testing.md`) — not just rendered, actually clicked through
- [ ] Screenshots (overview + notable new interaction) hosted on a `pr-<number>-screenshots`
      prerelease and embedded in the PR description (see `docs/local-testing.md`) — not committed
      to the repo
