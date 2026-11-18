import { CommonModule } from '@angular/common'
import type { OnChanges, OnDestroy, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output } from '@angular/core'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, ColDef, FirstDataRenderedEvent, GridApi, GridReadyEvent } from 'ag-grid-community'
import type { Observable } from 'rxjs'
import { of, Subject, takeUntil, tap } from 'rxjs'
import type { Column, Organization } from '@seed/api'
import { ColumnService, PairingService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { GenericRelatedInventory, InventoryType, ViewResponse } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-inventory-detail-paired-grid',
  templateUrl: './paired-grid.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MaterialImports],
})
export class PairedGridComponent implements OnChanges, OnDestroy {
  @Input() org: Organization
  @Input() type: InventoryType
  @Input() view: ViewResponse
  @Input() viewId: number
  @Output() refreshView = new EventEmitter<null>()
  private _columnService = inject(ColumnService)
  private _configService = inject(ConfigService)
  private _pairingService = inject(PairingService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  gridApi: GridApi
  gridTheme$ = this._configService.gridTheme$
  columns: Column[]
  columnDefs: ColDef[] = []
  defaultColumn: Column
  rowData: Record<string, unknown>[] = []
  defaultColDef = {
    sortable: false,
    filter: false,
    resizable: true,
    suppressMovable: true,
  }
  colDefMap = {
    taxlots: { idField: 'pm_property_id', idName: 'PM Property ID' },
    properties: { idField: 'jurisdiction_tax_lot_id', idName: 'Jurisdiction Tax Lot ID' },
  }
  otherMap = {
    properties: { other: 'taxlot', others: 'taxlots' },
    taxlots: { other: 'property', others: 'properties' },
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.view) {
      this.getData().subscribe()
    }
  }

  get data() {
    if (!this.view) return []
    return this.type === 'taxlots' ? this.view.properties : this.view.taxlots
  }

  getData(): Observable<Column[]> {
    if (!this.data.length) return of<Column[]>([])

    const stream = this.type === 'taxlots' ? this._columnService.propertyColumns$ : this._columnService.taxLotColumns$
    return stream.pipe(
      takeUntil(this._unsubscribeAll$),
      tap((columns) => {
        this.columns = columns
        const defaultColumnName = this.type === 'taxlots' ? this.org.property_display_field : this.org.taxlot_display_field
        this.defaultColumn = columns.find((c) => c.column_name === defaultColumnName)
        this.setGrid()
      }),
    )
  }

  setGrid() {
    const { idField, idName } = this.colDefMap[this.type]
    const { other, others } = this.otherMap[this.type]

    this.columnDefs = [
      { field: 'id', hide: true },
      {
        field: idField,
        headerName: idName,
        cellRenderer: ({ value }) => value as string,
      },
      { field: this.defaultColumn.column_name, headerName: this.defaultColumn.display_name },
      { field: 'Unpair', headerName: 'Unpair', cellRenderer: this.unpairRenderer },
    ]
    this.rowData = this.data.map((item: GenericRelatedInventory) => ({
      id: (item[other] as { id: string }).id,
      [idField]: `<a href="${others}/${item.id}/" class="underline">${item.state[idField] as string}</a>`,
      [this.defaultColumn.column_name]: item.state[this.defaultColumn.column_name],
    }))
  }

  unpairRenderer = () => {
    return '<span class="material-icons mt-2  cursor-pointer text-secondary">clear</span>'
  }

  get gridHeight() {
    return Math.min(this.rowData.length * 42 + 50, 500)
  }

  onGridReady(agGrid: GridReadyEvent) {
    this.gridApi = agGrid.api
    this.gridApi.addEventListener('cellClicked', this.onCellClicked.bind(this) as (event: CellClickedEvent) => void)
  }

  onCellClicked(event: CellClickedEvent) {
    if (event.colDef.field !== 'Unpair') return
    const { id } = event.data as { id: number }
    if (confirm(`Are you sure you want to unpair this ${this.otherMap[this.type].other}?`)) {
      this._pairingService.unpairInventory(this.org.id, this.viewId, id, this.type).subscribe(() => {
        this.refreshView.emit()
      })
    }
  }

  onFirstDataRendered(params: FirstDataRenderedEvent) {
    params.api.sizeColumnsToFit()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
