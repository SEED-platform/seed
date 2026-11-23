import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output } from '@angular/core'
import { TranslocoDirective } from '@jsverse/transloco'
import type { GridApi } from 'ag-grid-community'
import { take, tap } from 'rxjs'
import type { CurrentUser, OrganizationUserSettings } from '@seed/api'
import { OrganizationService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { Pagination } from '../../../inventory/inventory.types'

type PageDirection = 'first' | 'previous' | 'next' | 'last'

@Component({
  selector: 'seed-inventory-grid-controls',
  templateUrl: './grid-controls.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, TranslocoDirective],
})
export class InventoryGridControlsComponent implements OnInit {
  @Input() currentUser!: CurrentUser
  @Input() gridApi: GridApi
  @Input() pagination!: Pagination
  @Input() pageRowCount = 0
  @Input() selectedViewIds: number[]
  // The page's settings which each save replaces
  @Input() userSettings: OrganizationUserSettings
  @Output() pageChange = new EventEmitter<number>()
  @Output() selectAllMatching = new EventEmitter<void>()
  private _configService = inject(ConfigService)
  private _organizationService = inject(OrganizationService)
  scheme: 'dark' | 'light'

  get hasMorePages(): boolean {
    return !!this.pagination && this.pagination.total > this.pageRowCount
  }

  // Every row on this page is checked, but there are more matching records on other pages
  get canSelectAllMatching(): boolean {
    return this.hasMorePages && this.pageRowCount > 0 && this.selectedViewIds.length === this.pageRowCount
  }

  get allMatchingSelected(): boolean {
    return this.hasMorePages && this.selectedViewIds.length === this.pagination.total
  }

  ngOnInit(): void {
    this._configService.scheme$.subscribe((scheme) => {
      this.scheme = scheme
    })
  }

  isPageButtonDisabled(direction: PageDirection): boolean {
    const { page, num_pages } = this.pagination
    const atStart = direction === 'first' || direction === 'previous'
    return atStart ? page <= 1 : page >= num_pages
  }

  onPageChange = (direction: PageDirection) => {
    const { page, num_pages } = this.pagination
    const pageLookup = { first: 1, previous: page - 1, next: page + 1, last: num_pages }

    const newPage = pageLookup[direction]
    if (newPage < 1 || newPage > num_pages) return

    this.pageChange.emit(newPage)
  }

  clearSelection() {
    this.gridApi.deselectAll()
  }

  resetGrid() {
    this.resetPins()
    this.resetFilters()
    this.resetSorts()
    this.updateOrgUser()
  }

  resetFilters() {
    this.gridApi.setFilterModel(null)
    this.userSettings.filters = { ...this.userSettings.filters, properties: {}, taxlots: {} }
  }

  resetSorts() {
    this.userSettings.sorts = { ...this.userSettings.sorts, properties: [], taxlots: [] }
  }

  resetPins() {
    this.userSettings.pins = { ...this.userSettings.pins, properties: { left: [], right: [] }, taxlots: { left: [], right: [] } }
  }

  updateOrgUser() {
    const { org_id, org_user_id } = this.currentUser
    this._organizationService
      .updateOrganizationUser(org_user_id, org_id, this.userSettings)
      .pipe(
        take(1),
        tap(() => {
          this.gridApi.resetColumnState()
          // Including sorts and pins restored on column defs, which resetColumnState keeps
          this.gridApi.applyColumnState({ defaultState: { pinned: null, sort: null } })
          this.gridApi.refreshClientSideRowModel()
          this.gridApi.refreshCells({ force: true })
          this.gridApi.onSortChanged()
          this.gridApi.autoSizeAllColumns()
        }),
      )
      .subscribe()
  }
}
