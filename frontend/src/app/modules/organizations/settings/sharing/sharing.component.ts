import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { RouterLink } from '@angular/router'
import type { Observable } from 'rxjs'
import { combineLatest, finalize, forkJoin, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { Column, Organization, SharedField, UsedColumn, UserAuth } from '@seed/api'
import { AnalysisService, ColumnService, OrganizationService, UserService } from '@seed/api'
import { AlertComponent, PageComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { naturalSort } from '@seed/utils'

// A used column paired with its current public-sharing selection state
type SharableField = {
  id: number;
  table_name: string;
  name: string;
  display_name: string;
  public_checked: boolean;
}

@Component({
  selector: 'seed-organizations-settings-sharing',
  templateUrl: './sharing.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, FormsModule, MaterialImports, PageComponent, ReactiveFormsModule, RouterLink, SharedImports],
})
export class SharingComponent implements OnDestroy, OnInit {
  private _analysisService = inject(AnalysisService)
  private _columnService = inject(ColumnService)
  private _organizationService = inject(OrganizationService)
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  // Every column defined for the org (Property + Tax Lot), used as the catalog for `addField()` —
  // see `availableFieldsToAdd`. Populated in `_setFields`.
  private _allColumns: SharableField[] = []

  readonly baseUrl = window.location.origin

  organization: Organization
  auth: UserAuth
  // Rows shown in the table below: every column currently populated with data, plus any column
  // already marked public even if it no longer has data (see `_setFields`). Additional columns
  // (e.g. ones that don't have data yet) can be appended via `addField()`, driven by the "Add a
  // field" autocomplete in the template — `public_checked` still only gets persisted on `save()`.
  fields: SharableField[] = []
  loading = true
  loadError = false
  saving = false
  saved = false
  searchTableName = ''
  searchDisplayName = ''
  addFieldQuery = ''

  thresholdForm = new FormGroup({
    query_threshold: new FormControl<number | null>(null, [Validators.min(0), Validators.pattern(/^\d+$/)]),
  })

  get canManage(): boolean {
    return (this.organization?.is_parent ?? false) && (this.auth?.requires_owner ?? false)
  }

  get filteredFields(): SharableField[] {
    const tableSearch = this.searchTableName.trim().toLowerCase()
    const displaySearch = this.searchDisplayName.trim().toLowerCase()
    return this.fields.filter(
      (field) =>
        this.tableLabel(field.table_name).toLowerCase().includes(tableSearch) && field.display_name.toLowerCase().includes(displaySearch),
    )
  }

  get allFilteredSelected(): boolean {
    const visible = this.filteredFields
    return visible.length > 0 && visible.every((field) => field.public_checked)
  }

  get someFilteredSelected(): boolean {
    return this.filteredFields.some((field) => field.public_checked) && !this.allFilteredSelected
  }

  // Org columns not already shown in `fields`, filtered by `addFieldQuery` — the pick-list for
  // the "Add a field" autocomplete. Capped so a large org's column catalog doesn't render an
  // unbounded dropdown.
  get availableFieldsToAdd(): SharableField[] {
    const existingKeys = new Set(this.fields.map((field) => `${field.table_name}:${field.id}`))
    const query = this.addFieldQuery.trim().toLowerCase()
    return this._allColumns
      .filter((field) => !existingKeys.has(`${field.table_name}:${field.id}`))
      .filter(
        (field) =>
          !query || field.display_name.toLowerCase().includes(query) || this.tableLabel(field.table_name).toLowerCase().includes(query),
      )
      .slice(0, 50)
  }

  ngOnInit(): void {
    combineLatest([this._organizationService.currentOrganization$, this._userService.auth$])
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe(([organization, auth]) => {
        const orgChanged = this.organization?.id !== organization.id
        this.organization = organization
        this.auth = auth
        if (orgChanged) {
          this._loadSharingData(organization.id)
        }
      })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  tableLabel(tableName: string): string {
    return tableName === 'TaxLotState' ? 'Tax Lot' : 'Property'
  }

  // A plain `<a target="_blank">` to a same-origin URL gets redirected to same-tab navigation by
  // the app-wide `ExternalLinkDirective` (it only forces a new tab for cross-origin links), so
  // the "Test" buttons open explicitly via `window.open` instead.
  openInNewTab(url: string): void {
    window.open(url, '_blank', 'noopener,noreferrer')
  }

  onSelectAllChange(checked: boolean): void {
    const visibleIds = new Set(this.filteredFields.map((field) => field.id))
    for (const field of this.fields) {
      if (visibleIds.has(field.id)) {
        field.public_checked = checked
      }
    }
  }

  // Appends an org column picked from the "Add a field" autocomplete to the table, unchecked by
  // default — the user still has to tick "Share" and click "Save Changes" for it to persist.
  addField(field: SharableField): void {
    this.fields = [...this.fields, { ...field, public_checked: false }].sort((a, b) => naturalSort(a.display_name, b.display_name))
    this.addFieldQuery = ''
  }

  // MatAutocomplete uses this to compute the text left in the input after a selection; always
  // blank so the input stays ready for the next search instead of echoing the picked field's name.
  clearAutocompleteDisplay(): string {
    return ''
  }

  toggleFeed(enabled: boolean): void {
    this.organization.public_feed_enabled = enabled
    this._organizationService.updateSettings(this.organization).subscribe()
  }

  save(): void {
    if (this.thresholdForm.invalid || this.saving || !this.canManage) {
      return
    }

    this.saving = true
    this.saved = false
    this.organization.query_threshold = this.thresholdForm.get('query_threshold').value
    this.organization.public_fields = this.fields.filter((field) => field.public_checked).map(({ id }) => ({ id }))

    this._organizationService
      .updateSettings(this.organization)
      .pipe(
        switchMap(() => this._fetchSharingData(this.organization.id)),
        takeUntil(this._unsubscribeAll$),
        finalize(() => {
          this.saving = false
        }),
      )
      .subscribe({
        next: () => {
          this.saved = true
        },
        error: () => {
          this.saved = false
        },
      })
  }

  private _loadSharingData(orgId: number): void {
    this.loading = true
    this.loadError = false
    this._fetchSharingData(orgId)
      .pipe(
        takeUntil(this._unsubscribeAll$),
        finalize(() => {
          this.loading = false
        }),
      )
      .subscribe({
        error: () => {
          this.loadError = true
        },
      })
  }

  private _fetchSharingData(orgId: number): Observable<{
    usedColumns: UsedColumn[];
    propertyColumns: Column[];
    taxLotColumns: Column[];
    sharedFields: SharedField[];
    queryThreshold: number;
  }> {
    return forkJoin({
      usedColumns: this._analysisService.getUsedColumns(orgId),
      // Full org column catalog (Property + Tax Lot, used or not) — lets the user add a field to
      // the table below that doesn't have data yet, not just ones already in `usedColumns`.
      propertyColumns: this._columnService.getPropertyColumns(orgId),
      taxLotColumns: this._columnService.getTaxLotColumns(orgId),
      sharedFields: this._organizationService.getSharedFields(orgId),
      queryThreshold: this._organizationService.getQueryThreshold(orgId),
    }).pipe(
      tap(({ usedColumns, propertyColumns, taxLotColumns, sharedFields, queryThreshold }) => {
        this._setFields(usedColumns, [...propertyColumns, ...taxLotColumns], sharedFields)
        this.thresholdForm.get('query_threshold').setValue(queryThreshold)
      }),
    )
  }

  private _setFields(usedColumns: UsedColumn[], allColumns: Column[], sharedFields: SharedField[]): void {
    const publicKeys = new Set(sharedFields.map((field) => `${field.table_name}:${field.name}`))
    const usedKeys = new Set(usedColumns.map((column) => `${column.table_name}:${column.id}`))
    const toSharableField = (column: UsedColumn | Column): SharableField => ({
      id: column.id,
      table_name: column.table_name,
      name: column.name,
      display_name: column.display_name,
      public_checked: publicKeys.has(`${column.table_name}:${column.name}`),
    })

    // Deduplicate the full column catalog by composite table_name:id key before storing.
    const dedupedColumns = [...new Map(allColumns.map((col) => [`${col.table_name}:${col.id}`, col])).values()]
    this._allColumns = dedupedColumns.map(toSharableField).sort((a, b) => naturalSort(a.display_name, b.display_name))

    // Include any column that's already shared but fell out of `usedColumns` (its data was since
    // cleared) so saving doesn't silently un-share it just because it's no longer populated.
    const staleSharedFields = this._allColumns.filter((field) => field.public_checked && !usedKeys.has(`${field.table_name}:${field.id}`))

    this.fields = [...usedColumns.map(toSharableField), ...staleSharedFields].sort((a, b) => naturalSort(a.display_name, b.display_name))
  }
}
