import { AsyncPipe } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { Router } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, ColDef, GridApi, GridReadyEvent, RowClassParams } from 'ag-grid-community'
import { BehaviorSubject, combineLatest, filter, finalize, Subject, switchMap, take, takeUntil, tap } from 'rxjs'
import type {
  Column,
  FacilitiesPlan,
  FacilitiesPlanRun,
  FacilitiesPlanRunColumnFilter,
  FacilitiesPlanRunColumnSort,
  FacilitiesPlanRunProperty,
} from '@seed/api'
import { ColumnService, FacilitiesPlanRunService, FacilitiesPlanService, UserService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import { BulkEditModalComponent } from './modal/bulk-edit-modal.component'
import { DeleteModalComponent } from './modal/delete-modal.component'
import { FormModalComponent } from './modal/form-modal.component'

@Component({
  selector: 'seed-facilities-plan',
  templateUrl: './facilities-plan.component.html',
  encapsulation: ViewEncapsulation.None,
  host: { class: 'flex flex-col flex-auto min-h-0' },
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, AsyncPipe, MaterialImports, PageComponent, SharedImports],
})
export class FacilitiesPlanComponent implements OnInit, OnDestroy {
  private _columnService = inject(ColumnService)
  private _configService = inject(ConfigService)
  private _dialog = inject(MatDialog)
  private _router = inject(Router)
  private _facilitiesPlanService = inject(FacilitiesPlanService)
  private _facilitiesPlanRunService = inject(FacilitiesPlanRunService)
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  readonly gridTheme$ = this._configService.gridTheme$

  facilitiesPlans: FacilitiesPlan[] = []
  facilitiesPlanRuns: FacilitiesPlanRun[] = []
  currentRun: FacilitiesPlanRun | null = null
  currentRunId$ = new BehaviorSubject<number | null>(null)
  orgId: number
  allColumns: Column[] = []
  columnDefs: ColDef[] = []
  rowData: FacilitiesPlanRunProperty[] = []
  gridApi: GridApi | null = null
  totalCount = 0
  activeFilters: FacilitiesPlanRunColumnFilter[] = []
  activeSorts: FacilitiesPlanRunColumnSort[] = []
  selectedViewIds: number[] = []
  isLoading = false

  readonly defaultColDef: ColDef = {
    sortable: true,
    filter: true,
    floatingFilter: true,
    resizable: true,
  }

  readonly gridOptions = {
    rowClassRules: {
      'fp-in-plan': (params: RowClassParams<FacilitiesPlanRunProperty>) => {
        const run = this.currentRun
        if (!run?.run_at || params.data?.running_percentage == null) return false
        const plan = this.facilitiesPlans.find((p) => p.id === run.facilities_plan)
        return !!plan && params.data.running_percentage <= plan.energy_running_sum_percentage
      },
    },
    rowSelection: { mode: 'multiRow' as const, checkboxes: true, headerCheckbox: true },
    selectionColumnDef: { pinned: 'left' as const, width: 44, maxWidth: 44 },
    onSelectionChanged: () => {
      const rows = this.gridApi?.getSelectedRows() ?? []
      this.selectedViewIds = rows.map((r) => (r as FacilitiesPlanRunProperty).property_view_id)
    },
  }

  ngOnInit(): void {
    combineLatest([
      this._userService.currentOrganizationId$,
      this._facilitiesPlanService.facilitiesPlans$,
      this._facilitiesPlanRunService.facilitiesPlanRuns$,
    ])
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe(([orgId, plans, runs]) => {
        this.orgId = orgId
        this.facilitiesPlans = plans
        this.facilitiesPlanRuns = runs

        // Restore last-selected run from localStorage
        const lastId = Number(localStorage.getItem('last_facilities_plan_run_id'))
        const restoredId = runs.find((r) => r.id === lastId)?.id ?? runs[0]?.id ?? null
        if (restoredId !== this.currentRunId$.value) {
          this.currentRunId$.next(restoredId)
        } else {
          this._syncCurrentRun()
        }
      })

    this.currentRunId$
      .pipe(
        tap((id) => {
          if (id != null) localStorage.setItem('last_facilities_plan_run_id', String(id))
          this._syncCurrentRun()
        }),
        filter((id): id is number => id != null),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()

    this._columnService.propertyColumns$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((cols) => {
      this.allColumns = cols
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  onGridReady(event: GridReadyEvent): void {
    this.gridApi = event.api
    this.gridApi.addEventListener('cellClicked', this.onCellClicked.bind(this) as (event: CellClickedEvent) => void)
    if (this.rowData.length > 0) {
      this.gridApi.setGridOption('rowData', this.rowData)
    }
  }

  onCellClicked(event: CellClickedEvent): void {
    if (event.colDef.field !== 'property_view_id') return
    const target = event.event?.target as HTMLElement
    if (target?.getAttribute('data-action') !== 'detail') return
    const viewId = (event.data as FacilitiesPlanRunProperty).property_view_id
    void this._router.navigate(['/properties', viewId])
  }

  onRunChange(runId: number): void {
    this.currentRunId$.next(runId)
  }

  openCreateModal(): void {
    const ref = this._dialog.open(FormModalComponent, {
      width: '600px',
      data: { facilitiesPlans: this.facilitiesPlans, allColumns: this.allColumns, existingRun: null },
    })
    ref.afterClosed().subscribe((created) => {
      if (created) this._facilitiesPlanRunService.list()
    })
  }

  openEditModal(): void {
    if (!this.currentRun) return
    const ref = this._dialog.open(FormModalComponent, {
      width: '600px',
      data: { facilitiesPlans: this.facilitiesPlans, allColumns: this.allColumns, existingRun: this.currentRun },
    })
    ref.afterClosed().subscribe((updated) => {
      if (updated) this._facilitiesPlanRunService.list()
    })
  }

  openDeleteModal(): void {
    if (!this.currentRun) return
    const ref = this._dialog.open(DeleteModalComponent, {
      data: { run: this.currentRun },
    })
    ref.afterClosed().subscribe((deleted) => {
      if (deleted) {
        this._facilitiesPlanRunService.list()
        this.currentRunId$.next(null)
      }
    })
  }

  openBulkEditModal(): void {
    if (!this.currentRun || !this.selectedViewIds.length) return
    const ref = this._dialog.open(BulkEditModalComponent, {
      width: '500px',
      data: { run: this.currentRun, propertyViewIds: this.selectedViewIds },
    })
    ref.afterClosed().subscribe((saved) => {
      if (saved) this._refreshGrid()
    })
  }

  calculatePlan(): void {
    if (!this.currentRun) return
    this.isLoading = true
    this._facilitiesPlanRunService
      .run(this.currentRun.id)
      .pipe(
        finalize(() => {
          this.isLoading = false
        }),
        switchMap(() => this._facilitiesPlanRunService.facilitiesPlanRuns$.pipe(take(1))),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe(() => {
        this._refreshGrid()
      })
  }

  exportPlan(): void {
    if (!this.currentRun) return
    const runName = this.currentRun.name ?? String(this.currentRun.id)
    this._facilitiesPlanRunService
      .export(this.currentRun.id)
      .pipe(take(1))
      .subscribe((blob) => {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `facilities_plan_${runName}.xlsx`
        a.click()
        URL.revokeObjectURL(url)
      })
  }

  selectAll(): void {
    this.selectedViewIds = this.rowData.map((r) => r.property_view_id)
    this.gridApi?.selectAll()
  }

  selectNone(): void {
    this.selectedViewIds = []
    this.gridApi?.deselectAll()
  }

  private _syncCurrentRun(): void {
    this.currentRun = this.facilitiesPlanRuns.find((r) => r.id === this.currentRunId$.value) ?? null
    if (this.currentRun) {
      this._buildColumnDefs()
      this._refreshGrid()
    }
  }

  private _buildColumnDefs(): void {
    if (!this.currentRun) return
    const run = this.currentRun
    const cols: ColDef[] = [
      {
        headerName: '',
        field: 'property_view_id',
        width: 50,
        maxWidth: 50,
        sortable: false,
        filter: false,
        floatingFilter: false,
        suppressMovable: true,
        cellRenderer: ({ value }: { value: number }) =>
          value
            ? '<div class="flex mt-2 align-center"><span class="material-icons-outlined cursor-pointer" title="Go to property detail" data-action="detail">info</span></div>'
            : '',
      },
      {
        headerName: run.property_display_field?.display_name || run.property_display_field?.column_name || 'Property',
        field: `${run.property_display_field?.column_name}_${run.property_display_field?.id}`,
      },
      ...Object.entries(run.columns ?? {})
        .filter(([k]) => k !== 'compliance_cycle_year_column')
        .map(([, col]) => ({
          headerName: col.display_name || col.column_name,
          field: `${col.column_name}_${col.id}`,
          ...(col.data_type === 'boolean'
            ? {
                cellDataType: 'text' as const,
                valueFormatter: (params: { value: unknown }) => {
                  if (params.value === true) return 'true'
                  if (params.value === false) return 'false'
                  return ''
                },
              }
            : {}),
        })),
      { headerName: 'Total Energy Usage', field: 'total_energy_usage', sortable: false, filter: false, floatingFilter: false },
      { headerName: '% of Total Energy', field: 'percentage_of_total_energy_usage', sortable: false, filter: false, floatingFilter: false },
      { headerName: 'Running %', field: 'running_percentage', sortable: false, filter: false, floatingFilter: false },
      { headerName: 'Running Sq Ft', field: 'running_square_footage', sortable: false, filter: false, floatingFilter: false },
    ]

    if (run.columns?.compliance_cycle_year_column) {
      const col = run.columns.compliance_cycle_year_column
      cols.push({ headerName: col.display_name || col.column_name, field: `${col.column_name}_${col.id}` })
    }

    for (const col of run.display_columns ?? []) {
      cols.push({ headerName: col.display_name || col.column_name, field: `${col.column_name}_${col.id}` })
    }

    this.columnDefs = cols
  }

  private _refreshGrid(): void {
    if (!this.currentRun) return
    const runId = this.currentRun.id
    this._facilitiesPlanRunService
      .getProperties(runId, 1, 1000, this.activeFilters, this.activeSorts)
      .pipe(take(1))
      .subscribe({
        next: (res) => {
          this.rowData = res.properties
          this.totalCount = res.pagination.total
          if (this.gridApi) {
            this.gridApi.setGridOption('rowData', this.rowData)
          }
        },
      })
  }
}
