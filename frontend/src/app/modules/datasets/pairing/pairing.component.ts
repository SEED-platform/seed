import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { ActivatedRoute, Router } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, ColDef, GridApi, GridReadyEvent, RowDragEndEvent } from 'ag-grid-community'
import { combineLatest, filter, map, of, Subject, switchMap, take, takeUntil, tap } from 'rxjs'
import type { CurrentUser, Cycle, ImportFile } from '@seed/api'
import { CycleService, DatasetService, InventoryService, PairingService, UserService } from '@seed/api'
import { InventoryTabComponent, PageComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { InventoryType, Profile, State } from 'app/modules/inventory'

@Component({
  selector: 'seed-pairing',
  templateUrl: './pairing.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, InventoryTabComponent, MaterialImports, PageComponent, SharedImports],
})
export class PairingComponent implements OnDestroy, OnInit {
  private _configService = inject(ConfigService)
  private _cycleService = inject(CycleService)
  private _datasetService = inject(DatasetService)
  private _inventoryService = inject(InventoryService)
  private _pairingService = inject(PairingService)
  private _route = inject(ActivatedRoute)
  private _router = inject(Router)
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  fileId = Number(this._route.snapshot.paramMap.get('id'))
  type = this._route.snapshot.paramMap.get('type') as InventoryType

  allLeftData: State[] = []
  currentUser: CurrentUser
  cycleId: number = null
  cycles: Cycle[] = []
  gridTheme$ = this._configService.gridTheme$
  importFile: ImportFile
  leftColumnDefs: ColDef[] = []
  leftGridApi: GridApi
  leftRowData: State[] = []
  orgId: number
  propertyProfiles: Profile[] = []
  rightColumnDefs: ColDef[] = []
  rightGridApi: GridApi
  rightRowData: State[] = []
  showPaired: 'all' | 'paired' | 'unpaired' = 'all'
  taxlotProfiles: Profile[] = []

  ngOnInit(): void {
    this._userService.currentOrganizationId$
      .pipe(
        take(1),
        tap((orgId) => {
          this.orgId = orgId
        }),
        switchMap(() => this.getImportFile()),
        switchMap(() => this.getDependencies()),
        switchMap(() => this.loadInventory()),
        switchMap(() => this.watchTypeChanges()),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  // The route reuses this component across the sibling properties/taxlots routes, so the
  // `type` route param must be watched reactively rather than read once at construction time.
  watchTypeChanges() {
    return this._route.paramMap.pipe(
      map((params) => params.get('type') as InventoryType),
      filter((type) => type !== this.type),
      tap((type) => {
        this.type = type
      }),
      switchMap(() => this.loadInventory()),
    )
  }

  get otherType(): InventoryType {
    return this.type === 'taxlots' ? 'properties' : 'taxlots'
  }

  get leftTitle(): string {
    return this.type === 'taxlots' ? 'Tax Lot' : 'Property'
  }

  get rightTitle(): string {
    return this.otherType === 'taxlots' ? 'Tax Lot' : 'Property'
  }

  get pageTitle(): string {
    return this.type === 'taxlots' ? 'Pair Tax Lots to Properties' : 'Pair Properties to Tax Lots'
  }

  getImportFile() {
    return this._datasetService.getImportFile(this.orgId, this.fileId).pipe(
      take(1),
      tap((importFile) => {
        this.importFile = importFile
        this.cycleId = importFile.cycle
      }),
    )
  }

  getDependencies() {
    this._cycleService.getCycles(this.orgId)

    return combineLatest([
      this._cycleService.cycles$,
      this._userService.currentUser$,
      this._inventoryService.getColumnListProfiles('List View Profile', 'properties', true),
    ]).pipe(
      take(1),
      tap(([cycles, currentUser, profiles]) => {
        this.cycles = cycles
        this.currentUser = currentUser
        this.propertyProfiles = profiles.filter((p) => p.inventory_type === 0)
        this.taxlotProfiles = profiles.filter((p) => p.inventory_type === 1)
      }),
    )
  }

  profileIdFor(type: InventoryType): number | null {
    const profiles = type === 'taxlots' ? this.taxlotProfiles : this.propertyProfiles
    const settingsId = this.currentUser?.settings?.profile?.list?.[type]
    return profiles.find((p) => p.id === settingsId)?.id ?? profiles[0]?.id ?? null
  }

  loadInventory() {
    if (!this.cycleId) return of(null)

    return combineLatest([this.fetchSide(this.type), this.fetchSide(this.otherType)]).pipe(
      tap(([left, right]) => {
        this.allLeftData = (left.results ?? []) as State[]
        this.rightRowData = (right.results ?? []) as State[]
        this.leftColumnDefs = this.withDragColumn(left.column_defs ?? [])
        this.rightColumnDefs = this.withPairedColumn(right.column_defs ?? [])
        this.applyShowPairedFilter()
      }),
      map(() => null),
    )
  }

  fetchSide(type: InventoryType) {
    const inventory_type = type === 'taxlots' ? 'taxlot' : 'property'
    const params = new URLSearchParams({
      cycle: this.cycleId.toString(),
      ids_only: 'false',
      include_related: 'true',
      inventory_type,
      organization_id: this.orgId.toString(),
      page: '1',
      per_page: '999999999',
    })
    const data = { include_property_ids: null, profile_id: this.profileIdFor(type) }

    return this._inventoryService.getAgInventory(params.toString(), data)
  }

  withDragColumn(columnDefs: ColDef[]): ColDef[] {
    const dragColumn: ColDef = {
      field: 'drag',
      headerName: '',
      rowDrag: true,
      sortable: false,
      filter: false,
      resizable: false,
      width: 44,
      pinned: 'left',
    }
    return [dragColumn, ...columnDefs]
  }

  withPairedColumn(columnDefs: ColDef[]): ColDef[] {
    const pairedColumn: ColDef = {
      field: 'paired',
      headerName: 'Paired',
      minWidth: 260,
      sortable: false,
      filter: false,
      pinned: 'right',
      cellRenderer: this.pairedCellRenderer,
    }
    return [...columnDefs, pairedColumn]
  }

  pairedCellRenderer = ({ data }: { data: State }) => {
    const related = data.related ?? []
    if (!related.length) {
      const hint = this.type === 'taxlots' ? 'Drag Tax Lot here to pair with this Property' : 'Drag Property here to pair with this Tax Lot'
      return `<span class="text-xs italic text-secondary">${hint}</span>`
    }

    const chips = related
      .map((related_state) => {
        const viewId = this.type === 'taxlots' ? related_state.taxlot_view_id : related_state.property_view_id
        const label = this.pairedLabel(related_state)
        return `
          <span class="mb-1 mr-1 inline-flex items-center gap-1 rounded-full bg-primary-100 px-2 py-0.5 text-xs dark:bg-primary-800">
            ${label}
            <span class="material-icons icon-size-3 cursor-pointer" data-action="unpair" data-view-id="${viewId}" title="Unpair">close</span>
          </span>
        `
      })
      .join('')

    return `<div class="flex flex-wrap gap-1 py-1">${chips}</div>`
  }

  pairedLabel(state: State): string {
    // Field names in the API response are suffixed with a unique column id (e.g.
    // "address_line_1_11") to disambiguate property vs. tax lot columns of the same name.
    const candidates = ['address_line_1', 'pm_property_id', 'custom_id_1', 'jurisdiction_tax_lot_id']
    const stateKeys = Object.keys(state)
    for (const candidate of candidates) {
      const key = stateKeys.find((k) => k === candidate || k.startsWith(`${candidate}_`))
      const value = key ? state[key] : undefined
      if (typeof value === 'string' || typeof value === 'number') return String(value)
    }
    const viewId = this.type === 'taxlots' ? state.taxlot_view_id : state.property_view_id
    return `#${viewId}`
  }

  applyShowPairedFilter(): void {
    if (this.showPaired === 'paired') {
      this.leftRowData = this.allLeftData.filter((state) => (state.related ?? []).length > 0)
    } else if (this.showPaired === 'unpaired') {
      this.leftRowData = this.allLeftData.filter((state) => !(state.related ?? []).length)
    } else {
      this.leftRowData = this.allLeftData
    }
  }

  onLeftGridReady(event: GridReadyEvent) {
    this.leftGridApi = event.api
    this.leftGridApi.sizeColumnsToFit()
    this.wireDragDropIfReady()
  }

  onRightGridReady(event: GridReadyEvent) {
    this.rightGridApi = event.api
    this.rightGridApi.sizeColumnsToFit()
    this.wireDragDropIfReady()
  }

  wireDragDropIfReady(): void {
    if (!this.leftGridApi || !this.rightGridApi) return

    const dropZoneParams = this.rightGridApi.getRowDropZoneParams({
      onDragStop: (params: RowDragEndEvent) => {
        this.onPairDrop(params)
      },
    })
    this.leftGridApi.addRowDropZone(dropZoneParams)
  }

  onPairDrop(params: RowDragEndEvent) {
    const leftState = params.node.data as State
    const rightState = params.overNode?.data as State | undefined
    if (!rightState) return

    const propertyState = this.type === 'properties' ? leftState : rightState
    const taxlotState = this.type === 'properties' ? rightState : leftState

    this._pairingService
      .pairInventory(this.orgId, propertyState.property_view_id, taxlotState.taxlot_view_id, 'properties')
      .pipe(
        switchMap(() => this.loadInventory()),
        take(1),
      )
      .subscribe()
  }

  onRightCellClicked(event: CellClickedEvent) {
    if (event.colDef.field !== 'paired') return

    const target = event.event.target as HTMLElement
    const unpairAction = target.closest('[data-action="unpair"]')
    if (!unpairAction) return

    const relatedViewId = Number(unpairAction.getAttribute('data-view-id'))
    const rightState = event.data as State
    const viewId = this.otherType === 'taxlots' ? rightState.taxlot_view_id : rightState.property_view_id

    this._pairingService
      .unpairInventory(this.orgId, viewId, relatedViewId, this.otherType)
      .pipe(
        switchMap(() => this.loadInventory()),
        take(1),
      )
      .subscribe()
  }

  onCycleChange(cycleId: number) {
    this.cycleId = cycleId
    this.loadInventory().pipe(take(1)).subscribe()
  }

  onTypeChange = (type: InventoryType) => {
    if (type === this.type) return
    void this._router.navigate(['/data/pairing', this.fileId, type])
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
