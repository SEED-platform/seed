import { CommonModule } from '@angular/common'
import type { ElementRef, OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { ActivatedRoute } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, ColDef, GridApi, GridOptions, GridReadyEvent } from 'ag-grid-community'
import { Chart } from 'chart.js/auto'
import { filter, type Observable, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { Cycle, Dataset, GroupService, Meter, MeterUsage } from '@seed/api'
import { CycleService, DatasetService, GroupsService, MeterService, OrganizationService, UserService } from '@seed/api'
import { DeleteModalComponent, NotFoundComponent, PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { ViewResponse } from 'app/modules/inventory/inventory.types'
import { FormModalComponent } from './modal/form-modal.component'
import { GreenButtonUploadModalComponent } from './modal/green-button-upload-modal.component'

@Component({
  selector: 'seed-inventory-detail-meters',
  templateUrl: './meters.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MaterialImports, NotFoundComponent, PageComponent],
})
export class MetersComponent implements OnDestroy, OnInit {
  private readonly _unsubscribeAll$ = new Subject<void>()
  private _configService = inject(ConfigService)
  private _cycleService = inject(CycleService)
  private _dialog = inject(MatDialog)
  private _datasetService = inject(DatasetService)
  private _groupsService = inject(GroupsService)
  private _meterService = inject(MeterService)
  private _organizationService = inject(OrganizationService)
  private _route = inject(ActivatedRoute)
  private _userService = inject(UserService)
  cycles: Cycle[]
  datasets: Dataset[]
  excludedIds: number[] = []
  gridTheme$ = this._configService.gridTheme$
  interval: 'Exact' | 'Year' | 'Month' = 'Month'
  groupIds: number[]
  meterDefs: ColDef[] = []
  meterData: Record<string, unknown>[] = []
  meterGridApi: GridApi
  meters: Meter[]
  meterReadings: MeterUsage
  orgId: number
  readingDefs: ColDef[] = []
  readingData: Record<string, unknown>[] = []
  readingGridApi: GridApi
  readingGridHeight = 0
  readingsCollapsed = false
  services: GroupService[] = []
  view: ViewResponse
  viewId: number
  viewDisplayField$: Observable<string>
  @ViewChild('metersChart') private _chartCanvas?: ElementRef<HTMLCanvasElement>
  private _chart: Chart | null = null

  defaultColDef = {
    sortable: true,
    filter: true,
    floatingFilter: true,
    resizable: true,
    filterParams: {
      suppressAndOrCondition: true,
    },
  }

  gridOptions: GridOptions = {
    rowSelection: {
      mode: 'multiRow',
      checkboxes: true,
      headerCheckbox: true,
    },
    onSelectionChanged: () => {
      this.meterSelectionChanged()
    },
  }

  ngOnInit(): void {
    this.getUrlParams()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        switchMap(() => this._userService.currentOrganizationId$),
        tap((orgId) => {
          this.orgId = orgId
        }),
        tap(() => {
          this.setStreams()
        }),
      )
      .subscribe()
  }

  getUrlParams() {
    return this._route.parent.paramMap.pipe(
      tap((params) => {
        this.viewId = parseInt(params.get('id'))
        this.viewDisplayField$ = this._organizationService.getViewDisplayField(this.viewId, 'properties')
      }),
    )
  }

  setStreams() {
    this._meterService.list(this.orgId, this.viewId)
    this._meterService.listReadings(this.orgId, this.viewId, this.interval, this.excludedIds)
    this._groupsService.listForInventory(this.orgId, [this.viewId], 'properties')

    this._meterService.meters$
      .pipe(
        tap((meters) => {
          this.meters = meters
          this.setMeterGrid()
        }),
      )
      .subscribe((meters) => (this.meters = meters))

    this._meterService.meterReadings$
      .pipe(
        tap((meterReadings) => {
          this.meterReadings = meterReadings
          this.setReadingGrid()
        }),
      )
      .subscribe((meterReadings) => (this.meterReadings = meterReadings))

    this._groupsService.groups$
      .pipe(
        filter(Boolean),
        tap((groups) => {
          this.groupIds = groups.map((g) => g.id)
          this.services = groups
            .map((g) => g.systems || [])
            .flat()
            .map((sys) => sys.services || [])
            .flat()
        }),
      )
      .subscribe()

    this._cycleService.cycles$
      .pipe(
        tap((cycles) => {
          this.cycles = cycles
        }),
      )
      .subscribe()

    this._datasetService.datasets$
      .pipe(
        tap((datasets) => {
          this.datasets = datasets
        }),
      )
      .subscribe()
  }

  setMeterGrid() {
    this.setMeterData()
    this.setMeterColumnDefs()
  }

  setReadingGrid() {
    this.applyMeterFilter()
  }

  setMeterColumnDefs() {
    this.meterDefs = [
      { field: 'id', hide: true },
      { field: 'alias', headerName: 'Alias', hide: true },
      { field: 'type', headerName: 'Type' }, // needed? alias combines type, source, source id
      { field: 'source', headerName: 'Source' }, // needed? alias combines type, source, source id
      { field: 'source_id', headerName: 'Source ID' }, // needed?
      { field: 'direction', headerName: 'Direction' },
      { field: 'service', headerName: 'Service' },
      { field: 'is_virtual', headerName: 'Is Virtual' },
      { field: 'scenario_id', headerName: 'Scenario ID' }, // needed?
      { field: 'scenario_name', headerName: 'Scenario Name' },
      { field: 'actions', headerName: 'Actions', cellRenderer: this.actionRenderer },
    ]

    // hide column if all values are falsy
    const showColumn = (field: string, rowData: Record<string, unknown>[]) => rowData.some((row) => !!row[field])
    this.meterDefs = this.meterDefs.filter((colDef) => colDef.field === 'actions' || showColumn(colDef.field, this.meterData))
  }

  actionRenderer = () => {
    return `
      <div class="flex gap-2 mt-2 align-center">
      <span class="material-icons cursor-pointer text-secondary" title="Delete" data-action="delete">clear</span>
      ${this.groupIds.length ? '<span class="material-icons cursor-pointer text-secondary" title="Edit" data-action="edit">edit</span>' : ''}
      </div>
    `
  }

  setMeterData() {
    this.meterData = this.meters.map((m: Meter) => {
      const serviceName = this.services.find((s) => s.id === m.config.service_id)?.name || ''
      return { ...m, direction: m.config.direction, service: serviceName }
    })
    setTimeout(() => {
      if (this.meterGridApi && !this.meterGridApi.isDestroyed()) {
        this.meterGridApi?.selectAll()
      }
    }, 100)
  }

  setReadingData() {
    if (!this.meterReadings) return
    this.readingData = this.meterReadings.readings
    this.getReadingGridHeight()
    setTimeout(() => {
      this.buildChart()
    })
  }

  // Client-side filter readings and column defs to match selected meters (matches legacy filterByMeterSelections)
  applyMeterFilter() {
    if (!this.meterReadings) return
    const timeFields = new Set(['start_time', 'end_time', 'month', 'year'])
    const nameMap: Record<string, string> = { end_time: 'End Time', start_time: 'Start Time' }

    const gridSelectedRows = (this.meterGridApi?.getSelectedRows() as Meter[] | undefined) ?? []
    const selectedRows = (gridSelectedRows.length ? gridSelectedRows : this.meters) ?? []
    const selectedLabels = new Set(selectedRows.map((m) => `${m.type} - ${m.source ?? 'None'} - ${m.source_id ?? 'None'}`))
    const selectedLabelsArray = [...selectedLabels]

    this.readingDefs = this.meterReadings.column_defs
      .filter((col) => timeFields.has(col.field) || selectedLabels.size === 0 || selectedLabels.has(col.field))
      .map((col) => ({ field: col.field, headerName: nameMap[col.field] ?? col.displayName }))

    this.readingData
      = selectedLabels.size === 0
        ? this.meterReadings.readings
        : this.meterReadings.readings.filter((row) => selectedLabelsArray.some((label) => label in row))
    this.getReadingGridHeight()
    setTimeout(() => {
      this.buildChart()
    })
  }

  buildChart(): void {
    this._chart?.destroy()
    this._chart = null
    if (this.interval === 'Exact' || !this.readingData.length || !this.readingDefs.length) return
    const canvas = this._chartCanvas?.nativeElement
    if (!canvas) return

    const colors = ['#a6cee3', '#1f78b4', '#b2df8a', '#33a02c', '#fb9a99', '#e31a1c', '#fdbf6f', '#ff7f00', '#cab2d6', '#6a3d9a']
    const timeFields = new Set(['start_time', 'end_time', 'month', 'year'])
    const labelField = this.interval.toLowerCase()
    const labels = this.readingData.map((d) => String((d[labelField] as string | number) ?? (d.start_time as string | number) ?? ''))
    const scales: Record<string, unknown> = {}
    const datasets = this.readingDefs
      .filter((col) => !timeFields.has(col.field) && col.field !== labelField)
      .map((col, i) => {
        const unit = /\(([^)]+)\)$/.exec(col.headerName ?? col.field)?.[1] ?? 'Value'
        if (!scales[unit]) {
          scales[unit] = {
            type: 'linear',
            position: Object.keys(scales).length === 0 ? 'left' : 'right',
            title: { display: true, text: unit },
          }
        }
        const color = colors[i % colors.length]
        return {
          label: col.headerName ?? col.field,
          data: this.readingData.map((d) => d[col.field] as number | null),
          yAxisID: unit,
          backgroundColor: color,
          borderColor: color,
          tension: 0.1,
          fill: false,
        }
      })

    this._chart = new Chart(canvas, {
      type: 'line',
      data: { labels, datasets },
      options: { responsive: true, scales, plugins: { legend: { position: 'top' } } },
    })
  }

  get meterGridHeight() {
    if (!this.meterData.length) return 0
    return Math.min(this.meterData.length * 34 + 50, 500)
  }

  getReadingGridHeight() {
    const div = document.querySelector('#content')
    if (!div || !this.readingData?.length) return

    const divHeight = div.getBoundingClientRect().height ?? 1
    this.readingGridHeight = Math.min(this.readingData.length * 29 + 97, divHeight * 0.9)
  }

  onMeterGridReady(agGrid: GridReadyEvent) {
    this.meterGridApi = agGrid.api
    this.meterGridApi.sizeColumnsToFit()
    this.meterGridApi.addEventListener('cellClicked', this.onMeterCellClicked.bind(this) as (event: CellClickedEvent) => void)
  }

  onReadingGridReady(agGrid: GridReadyEvent) {
    this.readingGridApi = agGrid.api
  }

  onMeterCellClicked(event: CellClickedEvent) {
    if (event.colDef.field !== 'actions') return

    const target = event.event.target as HTMLElement
    const action = target.getAttribute('data-action')
    const { id } = event.data as { id: number }

    const meter = this.meters.find((m) => m.id === id)

    if (action === 'edit') {
      this.editMeter(meter)
    } else if (action === 'delete') {
      this.deleteMeter(meter)
    }
  }

  deleteMeter(meter: Meter) {
    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { model: 'Meter', instance: meter.alias },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this._meterService.delete(this.orgId, this.viewId, meter.id)),
      )
      .subscribe()
  }

  editMeter(meter: Meter) {
    this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: { meter, orgId: this.orgId, groupId: null, viewId: this.viewId },
    })
  }

  uploadGreenButtonData = () => {
    this._dialog.open(GreenButtonUploadModalComponent, {
      width: '40rem',
      data: {
        orgId: this.orgId,
        viewId: this.viewId,
        cycleId: this.cycles[0].id,
        systemId: null,
        datasetId: this.datasets[0].id ?? null,
        interval: this.interval,
        excludedIds: this.excludedIds,
      },
    })
  }

  intervalChange() {
    this._meterService.listReadings(this.orgId, this.viewId, this.interval)
  }

  meterSelectionChanged() {
    const allIds = this.meters.map((m: Meter) => m.id)
    const selectedIds = this.meterGridApi.getSelectedRows().map((r: { id: number }) => r.id)
    this.excludedIds = allIds.filter((id) => !selectedIds.includes(id))
    this.applyMeterFilter()
  }

  destroyGrids() {
    if (this.meterGridApi) {
      this.meterGridApi.destroy()
      this.meterGridApi = null
    }
    if (this.readingGridApi) {
      this.readingGridApi.destroy()
      this.readingGridApi = null
    }
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
    this._chart?.destroy()
  }
}
