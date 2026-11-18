import { AsyncPipe } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { ActivatedRoute, Router } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, ColDef, GridApi, GridReadyEvent, SelectionChangedEvent } from 'ag-grid-community'
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'
import { filter, Subject, switchMap, take, takeUntil, tap } from 'rxjs'
import type { GroupMeter, MeterInterval } from '@seed/api'
import { GroupsService, OrganizationService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import { GroupDetailLayoutComponent } from '../group-detail-layout.component'
import type { CreateMeterDialogData } from './dialogs/create-meter-dialog.component'
import { CreateMeterDialogComponent } from './dialogs/create-meter-dialog.component'
import type { DeleteMeterDialogData } from './dialogs/delete-meter-dialog.component'
import { DeleteMeterDialogComponent } from './dialogs/delete-meter-dialog.component'
import type { EditMeterDialogData } from './dialogs/edit-meter-dialog.component'
import { EditMeterDialogComponent } from './dialogs/edit-meter-dialog.component'
import type { MeterReadingsDialogData } from './dialogs/meter-readings-dialog.component'
import { MeterReadingsDialogComponent } from './dialogs/meter-readings-dialog.component'
import type { UploadReadingsDialogData } from './dialogs/upload-readings-dialog.component'
import { UploadReadingsDialogComponent } from './dialogs/upload-readings-dialog.component'

ModuleRegistry.registerModules([AllCommunityModule])

@Component({
  selector: 'seed-group-meters',
  templateUrl: './meters.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, AsyncPipe, MaterialImports, PageComponent],
})
export class GroupMetersComponent implements OnDestroy, OnInit {
  private _configService = inject(ConfigService)
  private _groupsService = inject(GroupsService)
  private _organizationService = inject(OrganizationService)
  private _route = inject(ActivatedRoute)
  private _router = inject(Router)
  private readonly _unsubscribeAll$ = new Subject<void>()
  private _dialog = inject(MatDialog)

  gridTheme$ = this._configService.gridTheme$
  groupId = parseInt(this._route.parent.snapshot.paramMap.get('groupId'))
  layout = inject(GroupDetailLayoutComponent) // parent route component; supplies breadcrumb links
  inventoryType = this._getInventoryType()
  orgId: number
  meters: GroupMeter[] = []
  meterGridApi: GridApi
  allReadings: Record<string, unknown>[] = []
  allReadingColumnDefs: ColDef[] = []
  readings: Record<string, unknown>[] = []
  readingColumnDefs: ColDef[] = []
  selectedMeter: GroupMeter | null = null
  interval: MeterInterval = 'Month'
  intervals: MeterInterval[] = ['Exact', 'Month', 'Year']
  loadingMeters = true
  loadingReadings = false

  meterColumnDefs: ColDef[] = [
    { headerName: 'ID', field: 'id', width: 80 },
    { headerName: 'Type', field: 'type', flex: 1 },
    { headerName: 'Alias', field: 'alias', flex: 1 },
    { headerName: 'Source', field: 'source', width: 130 },
    { headerName: 'Connection Type', field: 'connection_type', width: 150 },
    {
      headerName: 'Property',
      field: 'property_display_field',
      flex: 1,
      cellRenderer: (params: { value: string; data: GroupMeter }) => {
        if (!params.value || !params.data?.view_id) return params.value ?? ''
        return `<a data-action="navigate-property" class="text-primary-600 hover:underline cursor-pointer">${params.value}</a>`
      },
    },
    { headerName: 'System', field: 'system_name', width: 130 },
    {
      headerName: 'Connection',
      field: 'service_name',
      width: 140,
      cellRenderer: (params: { value: string; data: GroupMeter }) => {
        if (!params.value || !params.data?.service_group) return params.value ?? ''
        return `<a data-action="navigate-connection" class="text-primary-600 hover:underline cursor-pointer">${params.value}</a>`
      },
    },
    { headerName: 'Virtual', field: 'is_virtual', width: 90 },
    {
      headerName: 'Actions',
      field: 'actions',
      width: 180,
      sortable: false,
      filter: false,
      cellRenderer: () => {
        return `<div class="flex items-center gap-1 h-full">
          <button data-action="view-readings" class="cursor-pointer border-none bg-transparent p-1" title="View Readings">
            <span class="material-icons text-primary-600" style="font-size:18px">bar_chart</span>
          </button>
          <button data-action="edit" class="cursor-pointer border-none bg-transparent p-1" title="Edit Meter Connection">
            <span class="material-icons text-cyan-600" style="font-size:18px">edit</span>
          </button>
          <button data-action="delete" class="cursor-pointer border-none bg-transparent p-1" title="Delete Meter">
            <span class="material-icons text-red-700" style="font-size:18px">delete</span>
          </button>
          <button data-action="add-readings" class="cursor-pointer border-none bg-transparent p-1" title="Upload Meter Readings">
            <span class="material-icons text-primary-700" style="font-size:18px">add</span>
          </button>
        </div>`
      },
    },
  ]

  defaultColDef: ColDef = {
    sortable: true,
    filter: true,
    resizable: true,
  }

  meterGridOptions = {
    rowSelection: {
      mode: 'multiRow' as const,
      checkboxes: true,
      headerCheckbox: true,
    },
  }

  onMeterGridReady(event: GridReadyEvent) {
    this.meterGridApi = event.api
    // Select all meters by default
    this.meterGridApi.selectAll()
  }

  onMeterSelectionChanged(_event: SelectionChangedEvent) {
    this.applyMeterFilter()
  }

  applyMeterFilter() {
    const selectedMeters = (this.meterGridApi?.getSelectedRows() as GroupMeter[]) ?? []
    const timeColumns = ['start_time', 'end_time', 'month', 'year']
    const meterLabels = selectedMeters.map((m) => this._getMeterLabel(m))

    const selectedColumns = new Set([...timeColumns, ...meterLabels])
    this.readingColumnDefs = this.allReadingColumnDefs.filter((col) => selectedColumns.has(col.field))
    this.readings = this.allReadings.filter((reading) => meterLabels.some((label) => label in reading))
  }

  ngOnInit() {
    this._organizationService.currentOrganization$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        filter((org) => Boolean(org?.org_id)),
        take(1),
        tap(({ org_id }) => {
          this.orgId = org_id
        }),
        switchMap(() => this._groupsService.getMeters(this.orgId, this.groupId)),
        tap((data) => {
          this.meters = data
          this.loadingMeters = false
          this.loadReadings()
        }),
      )
      .subscribe()
  }

  loadReadings() {
    this.loadingReadings = true
    this._groupsService.getMeterUsage(this.orgId, this.groupId, this.interval).subscribe({
      next: (data) => {
        this.allReadings = data.readings
        this.allReadingColumnDefs = data.column_defs.map((col) => ({
          headerName: col.headerName ?? col.field,
          field: col.field,
          flex: 1,
          sortable: true,
          filter: true,
        }))
        this.loadingReadings = false
        this.applyMeterFilter()
      },
      error: () => {
        this.allReadings = []
        this.allReadingColumnDefs = []
        this.readings = []
        this.readingColumnDefs = []
        this.loadingReadings = false
      },
    })
  }

  changeInterval(interval: MeterInterval) {
    this.interval = interval
    this.loadReadings()
  }

  onMeterCellClicked(event: CellClickedEvent) {
    const target = event.event?.target as HTMLElement
    const action = target?.closest('[data-action]')?.getAttribute('data-action')
    if (!action) return

    const meter = event.data as GroupMeter
    switch (action) {
      case 'edit':
        this.editMeter(meter)
        break
      case 'delete':
        this.deleteMeter(meter)
        break
      case 'add-readings':
        this.addReadings(meter)
        break
      case 'navigate-property':
        if (meter.view_id) {
          void this._router.navigate(['/', this.inventoryType, meter.view_id, 'meters'])
        }
        break
      case 'navigate-connection':
        if (meter.service_group) {
          void this._router.navigate(['/', this.inventoryType, 'groups', meter.service_group, 'systems'])
        }
        break
      case 'view-readings':
        this.viewMeterReadings(meter)
        break
    }
  }

  createMeter() {
    const data: CreateMeterDialogData = { orgId: this.orgId, groupId: this.groupId }
    this._dialog
      .open(CreateMeterDialogComponent, { data, width: '500px' })
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this._refreshMeters()),
      )
      .subscribe()
  }

  editMeter(meter: GroupMeter) {
    const data: EditMeterDialogData = { orgId: this.orgId, groupId: this.groupId, meter }
    this._dialog
      .open(EditMeterDialogComponent, { data, width: '500px' })
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this._refreshMeters()),
      )
      .subscribe()
  }

  deleteMeter(meter: GroupMeter) {
    const data: DeleteMeterDialogData = { orgId: this.orgId, groupId: this.groupId, meter }
    this._dialog
      .open(DeleteMeterDialogComponent, { data, width: '400px' })
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this._refreshMeters()),
      )
      .subscribe()
  }

  addReadings(meter: GroupMeter) {
    const data: UploadReadingsDialogData = { orgId: this.orgId, groupId: this.groupId, meter }
    this._dialog
      .open(UploadReadingsDialogComponent, { data, width: '500px' })
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this._refreshMeters()),
      )
      .subscribe()
  }

  viewMeterReadings(meter: GroupMeter) {
    const data: MeterReadingsDialogData = { orgId: this.orgId, meter }
    this._dialog.open(MeterReadingsDialogComponent, { data, width: '700px' })
  }

  ngOnDestroy() {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  private _getInventoryType(): string {
    return (
      [...this._route.pathFromRoot]
        .reverse()
        .map((route) => route.snapshot.paramMap.get('type'))
        .find((type): type is string => !!type) ?? 'properties'
    )
  }

  private _getMeterLabel(meter: GroupMeter): string {
    const source = meter.source ?? 'None'
    const sourceId = meter.source_id ?? 'None'
    return `${meter.type} - ${source} - ${sourceId}`
  }

  private _refreshMeters() {
    return this._groupsService.getMeters(this.orgId, this.groupId).pipe(
      tap((data) => {
        this.meters = data
        this.loadReadings()
      }),
    )
  }
}
