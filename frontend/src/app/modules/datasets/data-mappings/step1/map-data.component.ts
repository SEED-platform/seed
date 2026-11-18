/* eslint-disable @typescript-eslint/no-unsafe-argument */
import { CommonModule } from '@angular/common'
import type { OnChanges, OnDestroy, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output } from '@angular/core'
import { FormsModule, ReactiveFormsModule } from '@angular/forms'
import { MatDialog } from '@angular/material/dialog'
import { ActivatedRoute } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellValueChangedEvent, ColDef, GridApi, GridReadyEvent, RowClassParams, RowNode } from 'ag-grid-community'
import { Subject, switchMap, take } from 'rxjs'
import type {
  Column,
  ColumnMapping,
  ColumnMappingProfile,
  ColumnMappingProfileType,
  Cycle,
  DataMappingRow,
  ImportFile,
  MappingSuggestionsResponse,
} from '@seed/api'
import { ColumnMappingProfileService } from '@seed/api'
import { AlertComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { ProgressBarObj } from '@seed/services/uploader'
import type { InventoryDisplayType } from 'app/modules/inventory'
import { buildColumnDefs } from './column-defs'
import { dataTypeMap, displayToDataTypeMap } from './constants'
import { CreateProfileComponent } from './modal/create-profile.component'

@Component({
  selector: 'seed-map-data',
  templateUrl: './map-data.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, AlertComponent, CommonModule, MaterialImports, ReactiveFormsModule, FormsModule],
})
export class MapDataComponent implements OnChanges, OnDestroy {
  @Input() orgId: number
  @Input() importFile: ImportFile
  @Input() columnMappingProfiles: ColumnMappingProfile[]
  @Input() cycle: Cycle
  @Input() firstFiveRows: Record<string, unknown>[]
  @Input() mappingSuggestions: MappingSuggestionsResponse
  @Input() rawColumnNames: string[]
  @Input() matchingPropertyColumns: string[]
  @Input() matchingTaxLotColumns: string[]
  @Output() completed = new EventEmitter<null>()
  @Output() defaultInventoryTypeChange = new EventEmitter<InventoryDisplayType>()

  private readonly _unsubscribeAll$ = new Subject<void>()
  private _configService = inject(ConfigService)
  private _columnMappingProfileService = inject(ColumnMappingProfileService)
  private _dialog = inject(MatDialog)
  private _router = inject(ActivatedRoute)
  columnDefs: ColDef[]
  dataValid = false
  defaultInventoryType: InventoryDisplayType = 'Property'
  defaultRow: Record<string, unknown>
  duplicateCounts: Record<string, number> = {}
  errorMessages: string[] = []
  fileId = this._router.snapshot.params.id as number
  gridApi: GridApi
  gridHeight = 0
  gridTheme$ = this._configService.gridTheme$
  mappedData: { mappings: DataMappingRow[] } = { mappings: [] }
  profile: ColumnMappingProfile
  propertyColumns: Column[] = []
  propertyColumnMap: Record<string, Column>
  propertyColumnNames: string[]
  rowData: Record<string, unknown>[] = []
  taxlotColumns: Column[] = []
  taxlotColumnMap: Record<string, Column>
  taxlotColumnNames: string[]

  gridOptions = {
    singleClickEdit: true,
    suppressMovableColumns: true,
    getRowClass: (params: RowClassParams<DataMappingRow>) => (params.data?.hasDuplicate ? 'bg-red-700/50' : ''),
  }

  progressBarObj: ProgressBarObj = {
    message: [],
    progress: 0,
    total: 100,
    complete: false,
    statusMessage: '',
    progressLastUpdated: null,
    progressLastChecked: null,
  }

  ngOnChanges(changes: SimpleChanges): void {
    // property columns is the last value to be set
    if ((changes.matchingPropertyColumns?.currentValue as string[])?.length) {
      this.setColumns()
      this.setGrid()
    }
  }

  setGrid() {
    this.defaultRow = {
      isExtraData: false,
      omit: null,
      to_field_display_name: null,
      to_table_name: this.defaultInventoryType,
      to_data_type: null,
      to_field: null,
      from_units: null,
    }
    this.setColumnDefs()
    this.setRowData()
  }

  setColumnDefs() {
    this.columnDefs = buildColumnDefs(
      this.propertyColumnNames,
      this.taxlotColumnNames,
      this.importFile.uploaded_filename,
      this.seedHeaderChange.bind(this),
      this.dataTypeChange.bind(this),
      this.validateData.bind(this),
    )
  }

  setRowData() {
    this.rowData = []

    // transpose first 5 rows to fit into the grid
    for (const header of this.rawColumnNames) {
      const keys = ['row1', 'row2', 'row3', 'row4', 'row5']
      const values = this.firstFiveRows.map((r) => r[header])
      const rows: Record<string, unknown> = Object.fromEntries(keys.map((k, i) => [k, values[i]]))

      const data = { ...rows, ...this.defaultRow, from_field: header }
      this.rowData.push(data)
    }

    for (const row of this.rowData) {
      row.omit = false
    }
    this.getGridHeight()
  }

  onGridReady(agGrid: GridReadyEvent) {
    this.gridApi = agGrid.api
  }

  getGridHeight() {
    const vh = window.innerHeight - 285 // header + footer
    if (!this.rowData?.length) return

    this.gridHeight = Math.min(this.rowData.length * 42 + 100, vh)
  }

  setAllInventoryType(value: InventoryDisplayType) {
    this.defaultInventoryType = value
    this.defaultInventoryTypeChange.emit(value)
    this.gridApi.forEachNode((node) => node.setDataValue('to_table_name', value))
    this.setColumns()
  }

  setColumns() {
    this.propertyColumns = this.mappingSuggestions?.property_columns ?? []
    this.propertyColumnNames = this.mappingSuggestions?.property_columns.map((c) => c.display_name) ?? []
    this.propertyColumnMap = Object.fromEntries(this.propertyColumns.map((c) => [c.display_name, c]))
    this.taxlotColumns = this.mappingSuggestions?.taxlot_columns ?? []
    this.taxlotColumnNames = this.mappingSuggestions?.taxlot_columns.map((c) => c.display_name) ?? []
    this.taxlotColumnMap = Object.fromEntries(this.taxlotColumns.map((c) => [c.display_name, c]))
  }

  seedHeaderChange = (params: CellValueChangedEvent): void => {
    const node = params.node as RowNode
    const newValue = params.newValue as string
    const column = this.getColumnMap(node.data)[newValue] ?? null

    const dataTypeConfig = dataTypeMap[column?.data_type] ?? { display: 'None', units: null }
    const to_field = column?.column_name ?? newValue
    node.setData({
      ...node.data,
      isNewColumn: !column,
      isExtraData: column?.is_extra_data ?? true,
      to_data_type: dataTypeConfig.display,
      to_field,
      from_units: dataTypeConfig.units,
    })
    this.refreshNode(node)
    this.validateData()
  }

  getColumnMap(nodeData: { to_table_name: InventoryDisplayType }) {
    if (nodeData.to_table_name === 'Tax Lot') return this.taxlotColumnMap
    if (nodeData.to_table_name === 'Property') return this.propertyColumnMap
    return this.defaultInventoryType === 'Tax Lot' ? this.taxlotColumnMap : this.propertyColumnMap
  }

  getColumns() {
    return this.defaultInventoryType === 'Tax Lot' ? this.taxlotColumns : this.propertyColumns
  }

  dataTypeChange = (params: CellValueChangedEvent): void => {
    const node = params.node as RowNode
    node.setDataValue('from_units', null)
    this.refreshNode(node)
  }

  refreshNode(node: RowNode) {
    this.gridApi.refreshCells({
      rowNodes: [node],
      force: true,
    })
  }

  copyHeadersToSeed() {
    this.gridApi.forEachNode((node: RowNode<{ from_field: string }>) => {
      const fileHeader = node.data.from_field
      node.setDataValue('to_field_display_name', fileHeader)
    })
  }

  applyProfile() {
    const toTableMap = { TaxLotState: 'Tax Lot', PropertyState: 'Property' }
    const mappingsMap = Object.fromEntries(this.profile.mappings.map((m) => [m.from_field, m]))
    const columnNameMap = Object.fromEntries(this.getColumns().map((c) => [c.column_name, c.display_name]))
    this.gridApi.forEachNode((node: RowNode<{ from_field: string }>) => {
      const mapping = mappingsMap[node.data.from_field]
      if (!mapping) return // skip if no mapping found

      const displayField = columnNameMap[mapping.to_field] ?? mapping.to_field
      node.setDataValue('to_field_display_name', displayField)
      node.setDataValue('to_field', mapping.to_field)
      node.setDataValue('from_units', mapping.from_units)
      node.setDataValue('to_table_name', toTableMap[mapping.to_table_name])
      node.setDataValue('omit', mapping.is_omitted)
    })
  }

  saveProfile() {
    // overwrite the existing profile
    this.profile.mappings = this.getMappingsFromGrid()
    this._columnMappingProfileService.update(this.orgId, this.profile).subscribe()
  }

  getMappingsFromGrid(): ColumnMapping[] {
    const mappings: ColumnMapping[] = []
    this.gridApi.forEachNode((node) => {
      const mapping = this.formatRowToMapping(node.data)
      if (mapping) mappings.push(mapping)
    })
    return mappings
  }

  formatRowToMapping(row: Record<string, unknown>): ColumnMapping {
    if (!row.to_field) return null
    const to_table_name = row.to_table_name === 'Tax Lot' ? 'TaxLotState' : 'PropertyState'
    const mapping: ColumnMapping = {
      from_field: row.from_field as string,
      from_units: row.from_units as string,
      to_field: row.to_field as string,
      to_table_name,
    }
    if (row.omit) mapping.is_omitted = true
    return mapping
  }

  createProfile() {
    const profileType: ColumnMappingProfileType = this.importFile.source_type === 'BuildingSync' ? 'BuildingSync Custom' : 'Normal'
    const profileTypes: ColumnMappingProfileType[]
      = profileType === 'BuildingSync Custom' ? ['BuildingSync Default', 'BuildingSync Custom'] : ['Normal']
    const dialogRef = this._dialog.open(CreateProfileComponent, {
      width: '40rem',
      data: {
        existingNames: this.columnMappingProfiles.map((p) => p.name),
        orgId: this.orgId,
        profileType,
        mappings: this.getMappingsFromGrid(),
      },
    })

    dialogRef
      .afterClosed()
      .pipe(
        take(1),
        switchMap(() => this._columnMappingProfileService.getProfiles(this.orgId, profileTypes)),
      )
      .subscribe()
  }

  // Format data for backend consumption
  mapData() {
    if (!this.dataValid) return

    this.mappedData.mappings = [] // reset so returning via "Back to Mapping" doesn't resend old rows
    this.gridApi.forEachNode(({ data }: { data: DataMappingRow }) => {
      if (data.omit) return // skip omitted rows

      const { from_field, from_units, to_data_type, to_field, to_field_display_name, to_table_name } = data

      this.mappedData.mappings.push({
        from_field,
        from_units: from_units?.replace('²', '**2') ?? null,
        to_data_type: displayToDataTypeMap[to_data_type] ?? null,
        to_field,
        to_field_display_name,
        to_table_name: to_table_name === 'Tax Lot' ? 'TaxLotState' : 'PropertyState',
      })
    })
    this.completed.emit()
  }

  validateData() {
    this.errorMessages = []
    const matchingColumns = this.defaultInventoryType === 'Tax Lot' ? this.matchingTaxLotColumns : this.matchingPropertyColumns
    let toFields = []
    this.gridApi.forEachNode((node: RowNode<DataMappingRow>) => {
      if (node.data.omit) return // skip omitted rows
      toFields.push(node.data.to_field)
    })

    // at least one matching column
    const hasMatchingCol = toFields.some((col) => matchingColumns.includes(col))
    if (!hasMatchingCol) {
      const matchingColNames = this.getColumns()
        .filter((c) => c.is_matching_criteria)
        .map((c) => c.display_name)
        .join(', ')
      this.errorMessages.push(`At least one of the following Property fields is required: ${matchingColNames}.`)
    }

    // all fields must be mapped (no empty fields)
    if (!toFields.every((f) => f)) {
      this.dataValid = false
      this.errorMessages.push('All SEED Headers must be mapped. Empty values are not allowed.')
    }

    // no duplicates
    toFields = toFields.filter((f) => f)
    this.duplicateCounts = {}
    if (toFields.length !== new Set(toFields).size) {
      this.setDuplicateCounts()
    }
    this.markDuplicates()

    this.dataValid = this.errorMessages.length === 0
    this.gridApi.redrawRows()
  }

  setDuplicateCounts() {
    this.gridApi.forEachNode((node: RowNode<DataMappingRow>) => {
      const v = node.data?.to_field_display_name
      if (v) this.duplicateCounts[v] = (this.duplicateCounts[v] ?? 0) + 1
    })
    this.dataValid = false
    this.errorMessages.push('Duplicate headers found. Each SEED Header must be unique.')
  }

  markDuplicates() {
    // mark duplicate rows with 'hasDuplicate' for styling
    this.gridApi.forEachNode((node: RowNode<DataMappingRow>) => {
      const v = node.data?.to_field_display_name
      node.data.hasDuplicate = v ? this.duplicateCounts[v] > 1 : false
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
