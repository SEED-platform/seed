import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MatDialog } from '@angular/material/dialog'
import { ActivatedRoute, Router } from '@angular/router'
import { TranslocoDirective, TranslocoService } from '@jsverse/transloco'
import type { Observable } from 'rxjs'
import { combineLatest, filter, map, of, startWith, Subject, switchMap, take, takeUntil } from 'rxjs'
import type { AccessLevelsByDepth, Column, Cycle, MatchingCriteriaColumnsResponse } from '@seed/api'
import { ColumnService, CycleService, InventoryService, OrganizationService, UserService } from '@seed/api'
import { AlertComponent, PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type {
  InventoryFormCreateData,
  InventoryFormCreateState,
  InventoryStateType,
  InventoryType,
  Profile,
} from 'app/modules/inventory/inventory.types'
import { CreateConfirmModalComponent } from './create-confirm-modal.component'

type FormColumnRow = {
  id: number;
  ctrl: FormControl<Column | string | null>;
  table_name: InventoryStateType;
  column_name: string;
  display_name: string;
  is_extra_data: boolean;
  is_matching_criteria: boolean;
  data_type: string;
  derived_column: number | null;
  value: string;
  is_duplicate: boolean;
  filtered: Column[];
}

@Component({
  selector: 'seed-inventory-create',
  templateUrl: './inventory-create.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, CommonModule, FormsModule, MaterialImports, PageComponent, ReactiveFormsModule, TranslocoDirective],
})
export class InventoryCreateComponent implements OnInit, OnDestroy {
  private _route = inject(ActivatedRoute)
  private _router = inject(Router)
  private _dialog = inject(MatDialog)
  private _columnService = inject(ColumnService)
  private _cycleService = inject(CycleService)
  private _inventoryService = inject(InventoryService)
  private _organizationService = inject(OrganizationService)
  private _userService = inject(UserService)
  private _snackBar = inject(SnackBarService)
  private _transloco = inject(TranslocoService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  private _rowId = 0

  type = this._route.snapshot.paramMap.get('type') as InventoryType
  primary: InventoryStateType
  related: InventoryStateType
  relatedType: InventoryType
  displayType: string
  titleKey: string

  orgId: number
  loaded = false
  creating = false

  cycles: Cycle[] = []
  columns: Column[] = []
  profiles: Profile[] = []
  accessLevelNames: string[] = []
  accessLevelInstancesByDepth: AccessLevelsByDepth = {}
  accessLevelInstances: { id: number; name: string }[] = []

  matchingColumns: Column[] = []
  canonicalColumns: Column[] = []
  extraColumns: Column[] = []
  matchingPropertyNames = ''
  matchingTaxlotNames = ''

  rows: FormColumnRow[] = []
  selectedProfileId: number | null = null
  formErrors: string[] = []
  valid = false

  configForm = new FormGroup({
    access_level: new FormControl<string | null>(null),
    access_level_instance: new FormControl<number | null>(null, Validators.required),
    cycle: new FormControl<number | null>(null, Validators.required),
  })

  displayColumn = (val: Column | string | null): string => {
    if (!val) return ''
    return typeof val === 'object' ? val.display_name : val
  }

  ngOnInit(): void {
    if (this.type === 'taxlots') {
      this.primary = 'TaxLotState'
      this.related = 'PropertyState'
      this.relatedType = 'properties'
    } else {
      this.primary = 'PropertyState'
      this.related = 'TaxLotState'
      this.relatedType = 'taxlots'
    }
    this.displayType = this.type === 'taxlots' ? 'Tax Lot' : 'Property'
    this.titleKey = this.type === 'taxlots' ? 'Create Tax Lot' : 'Create Property'

    this.watchAccessLevel()
    this.watchConfig()
    this.loadData()
  }

  loadData(): void {
    this._userService.currentOrganizationId$
      .pipe(
        switchMap((orgId) => {
          this.orgId = orgId
          this._cycleService.getCycles(orgId)
          const columns$ = this.type === 'properties' ? this._columnService.propertyColumns$ : this._columnService.taxLotColumns$
          return combineLatest([
            this._cycleService.cycles$.pipe(filter((cycles) => cycles.length > 0)),
            columns$.pipe(filter((columns) => columns.length > 0)),
            this._organizationService.accessLevelTree$,
            this._organizationService.accessLevelInstancesByDepth$,
            this._inventoryService.getColumnListProfiles('List View Profile', this.type),
            this._organizationService.getMatchingCriteriaColumns(this.orgId) as Observable<MatchingCriteriaColumnsResponse>,
          ])
        }),
        take(1),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe(([cycles, columns, tree, byDepth, profiles, matching]) => {
        this.cycles = cycles
        this.columns = columns
        this.accessLevelNames = tree.accessLevelNames
        this.accessLevelInstancesByDepth = byDepth
        this.profiles = profiles.filter((p) => p.inventory_type === this.displayType && p.profile_location === 'List View Profile')
        this.matchingPropertyNames = matching.PropertyState.join(', ')
        this.matchingTaxlotNames = matching.TaxLotState.join(', ')

        for (const c of this.columns) {
          if (c.table_name !== this.primary) continue
          if (c.is_matching_criteria) this.matchingColumns.push(c)
          if (c.is_extra_data) this.extraColumns.push(c)
          if (!c.is_extra_data && !c.derived_column) this.canonicalColumns.push(c)
        }

        this.rows = this.matchingColumns.map((c) => this._makeRow(c))

        // Default selections: deepest access level, its first instance, first cycle
        const deepestLevel = this.accessLevelNames.at(-1) ?? null
        this.configForm.patchValue({ access_level: deepestLevel, cycle: this.cycles[0]?.id ?? null })
        this._updateAccessLevelInstances(deepestLevel)
        this.configForm.patchValue({ access_level_instance: this.accessLevelInstances[0]?.id ?? null })

        this.loaded = true
        this.validate()
      })
  }

  watchConfig(): void {
    this.configForm.valueChanges.pipe(takeUntil(this._unsubscribeAll$)).subscribe(() => {
      this.validate()
    })
  }

  watchAccessLevel(): void {
    this.configForm
      .get('access_level')
      .valueChanges.pipe(takeUntil(this._unsubscribeAll$))
      .subscribe((level) => {
        this._updateAccessLevelInstances(level)
        this.configForm.get('access_level_instance').setValue(this.accessLevelInstances[0]?.id ?? null)
      })
  }

  addColumn(): void {
    this.rows.push(this._makeRow())
    this.validate()
  }

  removeColumn(index: number): void {
    this.rows.splice(index, 1)
    this.validate()
  }

  setColumns(type: 'canonical' | 'extra' | 'reset'): void {
    this._removeEmptyLastColumn()
    if (type === 'reset') {
      this.selectedProfileId = null
      this.rows = this.matchingColumns.map((c) => this._makeRow(c))
    } else {
      const source = type === 'canonical' ? this.canonicalColumns : this.extraColumns
      for (const col of source) {
        const exists = this.rows.some((r) => r.table_name === col.table_name && r.column_name === col.column_name)
        if (!exists) this.rows.push(this._makeRow(col))
      }
    }
    this.validate()
  }

  changeProfile(profileId: number | null): void {
    this.selectedProfileId = profileId
    const profile = this.profiles.find((p) => p.id === profileId)
    if (!profile?.columns?.length) {
      this.rows = []
      this.validate()
      return
    }
    const profileColumnNames = new Set(profile.columns.map((c) => c.column_name))
    this.rows = this.columns.filter((c) => profileColumnNames.has(c.column_name)).map((c) => this._makeRow(c))
    this.validate()
  }

  validate(): void {
    this.formErrors = []
    const cycle = this.configForm.get('cycle').value
    const ali = this.configForm.get('access_level_instance').value
    this.valid = Boolean(cycle) && Boolean(ali)
    if (!cycle) this.formErrors.push(this._transloco.translate('Cycle is required'))
    if (!ali) this.formErrors.push(this._transloco.translate('Access Level Instance is required'))

    // Duplicate display names
    const counts: Record<string, number> = {}
    for (const r of this.rows) {
      if (!r.display_name) continue
      counts[r.display_name] = (counts[r.display_name] || 0) + 1
    }
    let hasDuplicates = false
    for (const r of this.rows) {
      r.is_duplicate = Boolean(r.display_name) && counts[r.display_name] > 1
      if (r.is_duplicate) hasDuplicates = true
    }
    if (hasDuplicates) this.formErrors.push(this._transloco.translate('Duplicate columns are not allowed'))

    // At least one matching-criteria value per present table
    const tablesPresent: Record<InventoryStateType, number> = { PropertyState: 0, TaxLotState: 0 }
    const matchingValues: Record<InventoryStateType, number> = { PropertyState: 0, TaxLotState: 0 }
    for (const r of this.rows) {
      tablesPresent[r.table_name] += 1
      if (r.is_matching_criteria && r.value !== '' && r.value != null) matchingValues[r.table_name] += 1
    }
    const propertyPresent = this.type === 'properties' || tablesPresent.PropertyState > 0
    const taxlotPresent = this.type === 'taxlots' || tablesPresent.TaxLotState > 0
    if (propertyPresent && !matchingValues.PropertyState) {
      this.formErrors.push(
        this._transloco.translate('At least one of the following Property fields is required: {{fields}}', {
          fields: this.matchingPropertyNames,
        }),
      )
    }
    if (taxlotPresent && !matchingValues.TaxLotState) {
      this.formErrors.push(
        this._transloco.translate('At least one of the following Tax Lot fields is required: {{fields}}', {
          fields: this.matchingTaxlotNames,
        }),
      )
    }
  }

  save(): void {
    const { primary, related } = this._buildData()
    const cycle = this.cycles.find((c) => c.id === this.configForm.get('cycle').value)
    const aliName = this.accessLevelInstances.find((a) => a.id === this.configForm.get('access_level_instance').value)?.name ?? ''
    const typeLabel = this._typeLabel()

    this._dialog
      .open(CreateConfirmModalComponent, {
        width: '40rem',
        data: {
          title: this._transloco.translate('Create new {{type}}', { type: typeLabel }),
          body: this._transloco.translate('Create {{ali}} {{type}} in Cycle {{cycle}}?', {
            ali: aliName,
            type: typeLabel,
            cycle: cycle?.name ?? '',
          }),
          confirmText: this._transloco.translate('Confirm'),
          confirmIcon: 'fa-solid:check',
        },
      })
      .afterClosed()
      .pipe(take(1), takeUntil(this._unsubscribeAll$))
      .subscribe((confirmed: boolean) => {
        if (!confirmed) return
        this._create(primary, related)
      })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  private _updateAccessLevelInstances(level: string | null): void {
    const depth = this.accessLevelNames.findIndex((name) => name === level)
    this.accessLevelInstances = depth >= 0 ? (this.accessLevelInstancesByDepth[depth] ?? []) : []
  }

  private _typeLabel(): string {
    return this._transloco.translate(this.type === 'taxlots' ? 'Tax Lot' : 'Property')
  }

  private _makeRow(col?: Column): FormColumnRow {
    const row: FormColumnRow = {
      id: this._rowId++,
      ctrl: new FormControl(col ?? ''),
      table_name: col?.table_name ?? this.primary,
      column_name: col?.column_name ?? '',
      display_name: col?.display_name ?? '',
      is_extra_data: col?.is_extra_data ?? false,
      is_matching_criteria: col?.is_matching_criteria ?? false,
      data_type: col?.data_type ?? '',
      derived_column: col?.derived_column ?? null,
      value: '',
      is_duplicate: false,
      filtered: [],
    }
    row.ctrl.valueChanges.pipe(startWith(row.ctrl.value), takeUntil(this._unsubscribeAll$)).subscribe((val) => {
      row.filtered = this._filterColumns(val)
      this._syncRow(row, val)
      if (this.loaded) this.validate()
    })
    return row
  }

  private _searchText(val: Column | string | null): string {
    if (typeof val === 'string') return val
    if (val) return val.display_name
    return ''
  }

  private _filterColumns(val: Column | string | null): Column[] {
    const text = this._searchText(val).toLowerCase()
    return this.columns.filter((c) => c.display_name.toLowerCase().includes(text) || c.column_name.toLowerCase().includes(text))
  }

  private _syncRow(row: FormColumnRow, val: Column | string | null): void {
    if (val && typeof val === 'object') {
      this._applyColumn(row, val)
      return
    }
    const text = this._searchText(val).trim()
    const found = this.columns.find((c) => c.display_name === text) ?? this.columns.find((c) => c.column_name === text)
    if (found) {
      this._applyColumn(row, found)
    } else {
      row.table_name = this.primary
      row.column_name = text
      row.display_name = text
      row.is_extra_data = true
      row.is_matching_criteria = false
      row.data_type = 'string'
      row.derived_column = null
    }
  }

  private _applyColumn(row: FormColumnRow, col: Column): void {
    row.table_name = col.table_name
    row.column_name = col.column_name
    row.display_name = col.display_name
    row.is_extra_data = col.is_extra_data
    row.is_matching_criteria = col.is_matching_criteria
    row.data_type = col.data_type
    row.derived_column = col.derived_column
  }

  private _removeEmptyLastColumn(): void {
    const last = this.rows.at(-1)
    if (last && !last.display_name && !last.column_name) {
      this.rows.pop()
    }
  }

  private _buildData(): { primary: InventoryFormCreateData; related: InventoryFormCreateData | null } {
    const data: Record<InventoryStateType, { state: InventoryFormCreateState }> = {
      PropertyState: { state: { extra_data: {} } },
      TaxLotState: { state: { extra_data: {} } },
    }
    for (const r of this.rows) {
      const name = r.column_name || r.display_name
      if (!name) continue
      if (r.value === '' || r.value == null) continue
      const target = r.is_extra_data ? data[r.table_name].state.extra_data : data[r.table_name].state
      target[name] = r.value
    }

    const config = {
      access_level_instance_id: this.configForm.get('access_level_instance').value,
      cycle_id: this.configForm.get('cycle').value,
    }

    const relatedState = data[this.related].state
    const relatedEmpty = Object.keys(relatedState).length === 1 && Object.keys(relatedState.extra_data).length === 0

    let related: InventoryFormCreateData | null = null
    if (!relatedEmpty) {
      // Properties and taxlots share a link via the property's 'lot_number' field
      const taxId = data.TaxLotState.state.jurisdiction_tax_lot_id
      if (taxId != null && taxId !== '') {
        data.PropertyState.state.lot_number = taxId
      }
      related = { ...config, state: data[this.related].state }
    }
    const primary = { ...config, state: data[this.primary].state }
    return { primary, related }
  }

  private _create(primary: InventoryFormCreateData, related: InventoryFormCreateData | null): void {
    this.creating = true
    this._inventoryService
      .createInventory(primary, this.type)
      .pipe(
        switchMap((response) => {
          const viewId = response.view_id
          if (related && viewId) {
            return this._inventoryService.createInventory(related, this.relatedType, viewId).pipe(map(() => viewId))
          }
          return of(viewId)
        }),
        take(1),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe({
        next: (viewId) => {
          this.creating = false
          if (viewId) {
            this._snackBar.success(this._transloco.translate('Successfully created {{type}}', { type: this._typeLabel() }))
            void this._router.navigate([`/${this.type}`, viewId])
          } else {
            this._snackBar.info(this._transloco.translate('Duplicate record exists'))
          }
        },
        error: () => {
          this.creating = false
        },
      })
  }
}
