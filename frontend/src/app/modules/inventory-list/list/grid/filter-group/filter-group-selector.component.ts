import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MatDialog } from '@angular/material/dialog'
import { TranslocoDirective } from '@jsverse/transloco'
import type { GridApi } from 'ag-grid-community'
import { filter, Subject, take, takeUntil, tap } from 'rxjs'
import type { CurrentUser, FilterGroup, FilterGroupInventoryType, Label } from '@seed/api'
import { FilterGroupService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { LABEL_COLOR_MAP } from '../grid.component'
import type { FilterGroupModalData } from './filter-group-modal.component'
import { FilterGroupModalComponent } from './filter-group-modal.component'

export type LabelOperator = 'and' | 'or' | 'exclude'

export type LabelSelections = {
  andLabels: number[];
  orLabels: number[];
  excludeLabels: number[];
}

@Component({
  selector: 'seed-filter-group-selector',
  templateUrl: './filter-group-selector.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, TranslocoDirective],
})
export class FilterGroupSelectorComponent implements OnDestroy, OnInit {
  private _dialog = inject(MatDialog)
  private _filterGroupService = inject(FilterGroupService)
  private _snackBar = inject(SnackBarService)
  private _unsubscribeAll$ = new Subject<void>()

  @Input() currentUser: CurrentUser
  @Input() gridApi: GridApi
  @Input() inventoryType: FilterGroupInventoryType = 'Property'
  @Input() labels: Label[] = []
  @Input() orgId: number
  @Output() filterGroupApplied = new EventEmitter<FilterGroup | null>()
  @Output() labelSelectionsChanged = new EventEmitter<LabelSelections>()

  filterGroups: FilterGroup[] = []
  selectedFilterGroupId: number | null = null
  selectedFilterGroup: FilterGroup | null = null
  modified = false

  // Label selections for the current filter group
  andLabels: number[] = []
  orLabels: number[] = []
  excludeLabels: number[] = []
  showLabelPanel = false

  get isAliRoot(): boolean {
    return this.currentUser?.is_ali_root ?? false
  }

  ngOnInit(): void {
    this._filterGroupService.filterGroups$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((groups) => {
          this.filterGroups = groups.filter((g) => g.inventory_type === this.inventoryType)
        }),
      )
      .subscribe()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  onFilterGroupChange(id: number | null): void {
    this.selectedFilterGroupId = id
    this.selectedFilterGroup = this.filterGroups.find((fg) => fg.id === id) ?? null
    this.modified = false

    if (this.selectedFilterGroup) {
      this._applyFilterGroup(this.selectedFilterGroup)
    } else {
      this._clearFilters()
    }
  }

  markModified(): void {
    if (this.selectedFilterGroup) {
      this.modified = true
    }
  }

  // --- CRUD actions ---

  newFilterGroup(): void {
    const dialogRef = this._dialog.open(FilterGroupModalComponent, {
      width: '28rem',
      data: { action: 'new' } satisfies FilterGroupModalData,
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter((name): name is string => !!name),
        tap((name) => {
          const filters = this.gridApi?.getFilterModel() ?? {}
          const payload = {
            name,
            inventory_type: this.inventoryType,
            query_dict: filters,
            and_labels: this.andLabels,
            or_labels: this.orLabels,
            exclude_labels: this.excludeLabels,
          }

          this._filterGroupService
            .create(this.orgId, payload)
            .pipe(
              take(1),
              tap((fg) => {
                this.selectedFilterGroupId = fg.id
                this.selectedFilterGroup = fg
                this.modified = false
                this._snackBar.success(`Created ${fg.name}`)
              }),
            )
            .subscribe()
        }),
      )
      .subscribe()
  }

  saveFilterGroup(): void {
    const selectedFilterGroup = this.selectedFilterGroup
    if (!selectedFilterGroup) return

    const filters = this.gridApi?.getFilterModel() ?? {}
    const payload = {
      name: selectedFilterGroup.name,
      inventory_type: this.inventoryType,
      query_dict: filters,
      and_labels: this.andLabels,
      or_labels: this.orLabels,
      exclude_labels: this.excludeLabels,
    }

    this._filterGroupService
      .update(this.orgId, selectedFilterGroup.id, payload)
      .pipe(
        take(1),
        tap((fg) => {
          this.selectedFilterGroup = fg
          this.modified = false
          this._snackBar.success(`Saved ${fg.name}`)
        }),
      )
      .subscribe()
  }

  renameFilterGroup(): void {
    const selectedFilterGroup = this.selectedFilterGroup
    if (!selectedFilterGroup) return

    const dialogRef = this._dialog.open(FilterGroupModalComponent, {
      width: '28rem',
      data: { action: 'rename', name: selectedFilterGroup.name } satisfies FilterGroupModalData,
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter((name): name is string => !!name),
        tap((name) => {
          const payload = {
            name,
            inventory_type: this.inventoryType,
            query_dict: selectedFilterGroup.query_dict,
            and_labels: selectedFilterGroup.and_labels,
            or_labels: selectedFilterGroup.or_labels,
            exclude_labels: selectedFilterGroup.exclude_labels,
          }

          this._filterGroupService
            .update(this.orgId, selectedFilterGroup.id, payload)
            .pipe(
              take(1),
              tap((fg) => {
                this.selectedFilterGroup = fg
                this._snackBar.success(`Renamed to ${fg.name}`)
              }),
            )
            .subscribe()
        }),
      )
      .subscribe()
  }

  deleteFilterGroup(): void {
    const selectedFilterGroup = this.selectedFilterGroup
    if (!selectedFilterGroup) return

    const dialogRef = this._dialog.open(FilterGroupModalComponent, {
      width: '28rem',
      data: { action: 'delete', name: selectedFilterGroup.name } satisfies FilterGroupModalData,
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        tap(() => {
          const name = selectedFilterGroup.name
          this._filterGroupService
            .delete(this.orgId, selectedFilterGroup.id)
            .pipe(
              take(1),
              tap(() => {
                this.selectedFilterGroupId = null
                this.selectedFilterGroup = null
                this.modified = false
                this._snackBar.success(`Deleted ${name}`)
              }),
            )
            .subscribe()
        }),
      )
      .subscribe()
  }

  // --- Label management ---

  toggleLabel(labelId: number, operator: LabelOperator): void {
    const wasSelected = this.isLabelSelected(labelId, operator)

    // Remove from all lists first
    this._removeFromAllLabelLists(labelId)

    // If it wasn't already selected in this operator, add it
    if (!wasSelected) {
      this._getLabelList(operator).push(labelId)
    }
    this.markModified()
    this._emitLabelSelections()
  }

  isLabelSelected(labelId: number, operator: LabelOperator): boolean {
    return this._getLabelList(operator).includes(labelId)
  }

  get hasLabelSelections(): boolean {
    return this.andLabels.length > 0 || this.orLabels.length > 0 || this.excludeLabels.length > 0
  }

  getLabelDotColor(color: string): string {
    return LABEL_COLOR_MAP[color] ?? LABEL_COLOR_MAP.gray
  }

  // --- Private ---

  private _applyFilterGroup(fg: FilterGroup): void {
    // Apply column filters
    if (this.gridApi && fg.query_dict) {
      this.gridApi.setFilterModel(fg.query_dict)
    }

    // Apply label selections
    this.andLabels = [...(fg.and_labels ?? [])]
    this.orLabels = [...(fg.or_labels ?? [])]
    this.excludeLabels = [...(fg.exclude_labels ?? [])]

    this.filterGroupApplied.emit(fg)
    this._emitLabelSelections()
  }

  private _clearFilters(): void {
    this.andLabels = []
    this.orLabels = []
    this.excludeLabels = []
    this.filterGroupApplied.emit(null)
    this._emitLabelSelections()
  }

  private _emitLabelSelections(): void {
    this.labelSelectionsChanged.emit({
      andLabels: [...this.andLabels],
      orLabels: [...this.orLabels],
      excludeLabels: [...this.excludeLabels],
    })
  }

  private _getLabelList(operator: LabelOperator): number[] {
    switch (operator) {
      case 'and':
        return this.andLabels
      case 'or':
        return this.orLabels
      case 'exclude':
        return this.excludeLabels
    }
  }

  private _removeFromAllLabelLists(labelId: number): void {
    this.andLabels = this.andLabels.filter((id) => id !== labelId)
    this.orLabels = this.orLabels.filter((id) => id !== labelId)
    this.excludeLabels = this.excludeLabels.filter((id) => id !== labelId)
  }
}
