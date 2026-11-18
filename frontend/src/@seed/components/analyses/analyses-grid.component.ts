import { CommonModule } from '@angular/common'
import type { AfterViewInit, OnChanges, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, Input } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { Router } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, ColDef, GridApi, GridReadyEvent } from 'ag-grid-community'
import { filter, switchMap, take } from 'rxjs'
import type { Analysis, CurrentUser, Cycle, Highlight } from '@seed/api'
import { AnalysisService, UserService } from '@seed/api'
import { DeleteModalComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'

@Component({
  selector: 'seed-analyses-grid',
  templateUrl: './analyses-grid.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MaterialImports],
})
export class AnalysesGridComponent implements AfterViewInit, OnChanges {
  @Input() orgId: number
  @Input() analyses: Analysis[] = []
  @Input() cycles: Cycle[] = []
  @Input() parentRef!: HTMLDivElement
  @Input() highlights = false
  private _analysisService = inject(AnalysisService)
  private _configService = inject(ConfigService)
  private _userService = inject(UserService)
  private _router = inject(Router)
  private _dialog = inject(MatDialog)
  currentUser: CurrentUser

  gridApi: GridApi
  gridTheme$ = this._configService.gridTheme$
  gridHeight = 0
  columnDefs: ColDef[] = []

  ngAfterViewInit(): void {
    this._userService.currentUser$.pipe(take(1)).subscribe((user) => {
      this.currentUser = user
      this.setColumnDefs()
      this.gridApi?.refreshCells({ force: true })
    })
    this._analysisService.pollStatuses(this.orgId)
  }

  ngOnChanges(changes: SimpleChanges): void {
    if ((changes.analyses?.currentValue as Analysis[])?.length) {
      this.getGridHeight()
    }
    if (changes.cycles) {
      this.setColumnDefs()
    }
  }

  setColumnDefs() {
    this.columnDefs = [
      { field: 'id', hide: true },
      { field: 'name', headerName: 'Name', cellRenderer: this.nameRenderer },
      { field: 'status', headerName: 'Status', cellRenderer: this.statusRenderer },
      { field: 'service', headerName: 'Service' },
      // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
      { field: 'cycles', headerName: 'Cycle', valueFormatter: this.getCycle.bind(this) },
      { field: 'number_of_analysis_property_views', headerName: 'Property Count' },
      {
        field: 'created_at',
        headerName: 'Created At',
        valueFormatter: ({ value }: { value: string }) => new Date(value).toLocaleDateString(),
      },
      { field: 'run_duration', headerName: 'Run Duration', valueGetter: this._analysisService.getRunDuration },
      { field: 'actions', headerName: 'Actions', cellRenderer: this.actionRenderer },
    ]

    if (this.highlights) {
      const highlightsCol = {
        field: 'highlights',
        headerName: 'Highlights',
        cellRenderer: this.highlightsRenderer,
        valueFormatter: () => '', // suppress datatype warning
      }
      this.columnDefs.splice(3, 0, highlightsCol)

      const resultsCol = {
        field: 'results',
        headerName: 'Results',
        cellRenderer: this.resultsRenderer,
      }

      this.columnDefs.splice(3, 0, resultsCol)
    }
  }

  nameRenderer({ value }: { value: string }) {
    return `
      <div class="text-primary dark:text-primary-300 cursor-pointer" title="Analysis Detail" data-action="detail">
        ${value}
        <span class="material-icons text-secondary text-sm">open_in_new</span>
      </div>
    `
  }

  statusRenderer = ({ value }: { value: string }) => {
    const styleMap: Record<string, string> = {
      Completed: 'background-color: #198754; color: white;',
      Failed: 'background-color: #dc3545; color: white;',
      Running: '',
      Creating: '',
    }
    const classMap: Record<string, string> = {
      Running: 'bg-primary text-white animate-pulse',
      Creating: 'bg-primary text-white animate-pulse',
    }

    const style = styleMap[value] ?? ''
    const classes = classMap[value] ?? ''

    return `<div class="overflow-hidden ${classes} px-2" style="${style}">${value}</div>`
  }

  resultsRenderer = ({ data }: { data: Analysis }) => {
    if (!data.views.length) return ''
    return `
      <div class="flex gap-4">
        <div class="text-primary dark:text-primary-300 cursor-pointer" title="View Results" data-action="viewResults">
          Results
          <span class="material-icons text-secondary text-sm">open_in_new</span>
        </div>
      </div>
    `
  }

  highlightsRenderer = ({ value }: { value: Highlight[] }) => {
    if (!value?.length) return ''

    return `
        <ul class="">
          ${value
            .map(
              (highlight) => `
            <li class="list-disc pl-4 space-y-1 text leading-snug">
              <div class="truncate max-w-full whitespace-nowrap overflow-hidden"><span class="text-secondary">${highlight.name}:</span> ${highlight.value}</div>
            </li>
          `,
            )
            .join('')}
        </ul>
    `
  }

  actionRenderer = ({ data }: { data: Analysis }) => {
    if (this.currentUser?.org_role === 'viewer') return ''

    const runningStatuses = new Set(['Pending Creation', 'Creating', 'Queued', 'Running'])
    const isRunning = runningStatuses.has(data.status)

    return `
      <div class="flex gap-2 mt-2 align-center">
      <span class="material-icons action-icon cursor-pointer text-secondary" title="Delete" data-action="delete">clear</span>
      ${isRunning ? ' <span class="material-icons action-icon cursor-pointer text-secondary" title="Stop" data-action="stop">dangerous</span>' : ''}
      ${data.status === 'Ready' ? ' <span class="material-icons action-icon cursor-pointer text-secondary" title="Start" data-action="start">play_circle_filled</span>' : ''}
      </div>
    `
  }

  getCycle(params: { value: number[] }): string {
    if (!params.value?.length || !this.cycles.length) return ''
    const cycleId = params.value[0]
    return this.cycles.find((c) => c.id === cycleId)?.name ?? ''
  }

  getGridHeight() {
    if (!this.parentRef || !this.analyses?.length) return

    const divHeight = this.parentRef.getBoundingClientRect().height ?? 1
    this.gridHeight = Math.min(this.analyses.length * 42 + 52, divHeight * 0.9)
  }

  getRowHeight = (params: { data: Analysis }) => {
    if (!this.highlights) return undefined

    const height = params.data.highlights?.length * 20 + 10
    return Math.max(42, height)
  }

  onGridReady(agGrid: GridReadyEvent) {
    this.gridApi = agGrid.api
    this.gridApi.addEventListener('cellClicked', this.onCellClicked.bind(this) as (event: CellClickedEvent) => void)
  }

  onCellClicked(event: CellClickedEvent) {
    if (!['actions', 'name', 'results'].includes(event.colDef.field)) return

    const target = event.event.target as HTMLElement
    const action = target.getAttribute('data-action')
    const { id } = event.data as { id: number }

    const analysis = this.analyses.find((a) => a.id === id)

    if (action === 'delete') {
      this.deleteAnalysis(analysis)
    } else if (action === 'stop') {
      this._analysisService.stopAnalysis(this.orgId, id).pipe(take(1)).subscribe()
    } else if (action === 'start') {
      this._analysisService.startAnalysis(this.orgId, id).pipe(take(1)).subscribe()
    } else if (action === 'detail') {
      void this._router.navigate([`/analyses/${id}`])
    } else if (action === 'viewResults') {
      void this._router.navigate([`/analyses/${id}/views/${analysis.views[0]}`])
    }
  }

  deleteAnalysis(analysis: Analysis) {
    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { model: 'Analysis', instance: analysis.name },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this._analysisService.delete(this.orgId, analysis.id)),
      )
      .subscribe()
  }
}
