import { CommonModule } from '@angular/common'
import type { OnChanges, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core'
import { TranslocoDirective } from '@jsverse/transloco'
import type { ColDef, GridApi } from 'ag-grid-community'
import type { Column, Label, OrganizationUserSettings } from '@seed/api'
import { buildFilterChips, FilterChipsComponent, removeGridFilter } from '@seed/components/filter-chips'
import { MaterialImports } from '@seed/materials'
import type { FilterSortChip, FiltersSorts, InventoryType } from '../../../inventory/inventory.types'
import type { LabelOperator, LabelSelections } from './filter-group/filter-group-selector.component'

export type LabelChip = {
  id: number;
  name: string;
  operator: LabelOperator;
  prefix: string;
}

const LABEL_PREFIXES: Record<LabelOperator, string> = { and: 'AND', or: 'OR', exclude: 'Exclude' }

@Component({
  selector: 'seed-inventory-filter-sort-chips',
  templateUrl: './filter-sort-chips.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, FilterChipsComponent, MaterialImports, TranslocoDirective],
})
export class FilterSortChipsComponent implements OnChanges {
  @Input() columns: Column[]
  @Input() columnDefs: ColDef[]
  @Input() gridApi: GridApi
  @Input() userSettings: OrganizationUserSettings
  @Input() type: InventoryType
  @Input() labels: Label[] = []
  @Input() labelSelections: LabelSelections
  @Output() labelRemoved = new EventEmitter<LabelChip>()
  // The saved filters and sorts without one the grid doesn't have (e.g., on a column outside the profile)
  @Output() savedFilterSortRemoved = new EventEmitter<FiltersSorts>()
  filterChips: FilterSortChip[] = []
  labelChips: LabelChip[] = []
  sortChips: FilterSortChip[] = []

  ngOnChanges(changes: SimpleChanges) {
    const { userSettings, columnDefs, labels, labelSelections } = changes
    if (userSettings?.currentValue || columnDefs?.currentValue) {
      this.getFilterChips()
      this.getSortChips()
    }
    if (labels || labelSelections) {
      this.getLabelChips()
    }
  }

  get sorts() {
    return this.userSettings.sorts?.[this.type] ?? []
  }

  get filters() {
    return this.userSettings.filters?.[this.type] ?? {}
  }

  getFilterChips() {
    this.filterChips = buildFilterChips({ filterModel: this.filters, columnDefs: this.columnDefs, columns: this.columns })
  }

  getLabelChips() {
    const { andLabels = [], orLabels = [], excludeLabels = [] } = this.labelSelections ?? {}
    const idsByOperator: [LabelOperator, number[]][] = [
      ['and', andLabels],
      ['or', orLabels],
      ['exclude', excludeLabels],
    ]
    this.labelChips = idsByOperator.flatMap(([operator, ids]) =>
      ids.map((id) => ({
        id,
        operator,
        name: this.labels?.find((label) => label.id === id)?.name ?? `${id}`,
        prefix: LABEL_PREFIXES[operator],
      })),
    )
  }

  getSortChips() {
    this.sortChips = []
    for (let sort of this.sorts) {
      const direction = sort.startsWith('-') ? 'desc' : 'asc'
      sort = sort.replace(/^-/, '')
      const colDef = this.columnDefs.find(({ field }) => field === sort)
      if (colDef) {
        this.sortChips.push({
          field: colDef.field,
          displayName: `${colDef.headerName} ${direction}`,
          original: sort,
        })
      } else {
        const column = this.columns.find((c) => c.name === sort)
        const displayName = column?.display_name ?? sort
        this.sortChips.push({
          field: sort,
          displayName: `${displayName} ${direction}`,
          original: sort,
        })
      }
    }
  }

  removeFilter(columnName: string): void {
    if (Object.hasOwn(this.gridApi.getFilterModel(), columnName)) {
      removeGridFilter(this.gridApi, columnName)
    } else {
      const filters = Object.fromEntries(Object.entries(this.filters).filter(([name]) => name !== columnName))
      this.savedFilterSortRemoved.emit({ filters, sorts: this.sorts })
    }
  }

  removeLabel(chip: LabelChip): void {
    this.labelRemoved.emit(chip)
  }

  removeSort(sortToRemove: string): void {
    const currentState = this.gridApi.getColumnState()
    if (!currentState.some(({ colId, sort }) => colId === sortToRemove && sort)) {
      const sorts = this.sorts.filter((sort) => sort.replace(/^-/, '') !== sortToRemove)
      this.savedFilterSortRemoved.emit({ filters: this.filters, sorts })
      return
    }
    const updatedState = currentState.map((col) => {
      return col.colId === sortToRemove ? { ...col, sort: null } : col
    })
    this.gridApi.applyColumnState({ state: updatedState })
  }
}
