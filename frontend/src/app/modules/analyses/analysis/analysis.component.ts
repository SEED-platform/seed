import type { KeyValue } from '@angular/common'
import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { ActivatedRoute, Router } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, ColDef, GridApi, GridReadyEvent } from 'ag-grid-community'
import { combineLatest, filter, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { AnalysesMessage, Analysis, AnalysisOutputFile, CurrentUser, Cycle, View } from '@seed/api'
import { AnalysisService, CycleService, MediaService, OrganizationService, UserService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials/material.module'
import { ConfigService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-analyses-analysis',
  templateUrl: './analysis.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MaterialImports, PageComponent, SharedImports],
})
export class AnalysisComponent implements OnDestroy, OnInit {
  private _route = inject(ActivatedRoute)
  private _router = inject(Router)
  private _analysisService = inject(AnalysisService)
  private _configService = inject(ConfigService)
  private _cycleService = inject(CycleService)
  private _dialog = inject(MatDialog)
  private _mediaService = inject(MediaService)
  private _organizationService = inject(OrganizationService)
  private _snackBar = inject(SnackBarService)
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  analysisId = Number(this._route.snapshot.paramMap.get('id'))
  analysis: Analysis | null = null
  analysisDescription: string
  columnDefs: { analysis: ColDef[]; views: ColDef[] }
  columnsToDisplay = ['id', 'property', 'messages', 'outputs', 'actions']
  currentUser: CurrentUser
  cycles: Cycle[]
  gridApi: GridApi
  gridTheme$ = this._configService.gridTheme$
  gridHeight = 0
  messages: AnalysesMessage[]
  originalViews: Record<number, number>
  orgId: number
  views: View[] = []
  gridViews: (View & { messages?: string[] })[] = []

  ngOnInit() {
    this._userService.currentOrganizationId$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((orgId) => {
          this.orgId = orgId
        }),
        switchMap(() => this.getCycles()),
        tap(() => {
          this.getAnalysis()
        }),
      )
      .subscribe()
  }

  getCycles() {
    return this._cycleService.cycles$.pipe(
      takeUntil(this._unsubscribeAll$),
      tap((cycles) => {
        this.cycles = cycles
      }),
    )
  }

  getAnalysis() {
    this._analysisService.getAnalysis(this.orgId, this.analysisId)
    this._analysisService.getAnalysisViews(this.orgId, this.analysisId)
    this._analysisService.getMessages(this.orgId, this.analysisId)

    combineLatest([
      this._analysisService.analysis$,
      this._analysisService.views$,
      this._analysisService.messages$,
      this._analysisService.originalViews$,
    ])
      .pipe(
        // Don't wait for views: an analysis that failed or is still being created can have none.
        // `formatViews` skips views from another analysis
        filter(([analysis]) => analysis?.id === this.analysisId),
        takeUntil(this._unsubscribeAll$),
        tap(([analysis, views, messages, originalViews]) => {
          this.analysis = analysis
          this.views = views
          this.messages = messages
          this.originalViews = originalViews
          this.analysisDescription = this._analysisService.getAnalysisDescription(analysis)
          this.formatViews()
          this.setColumnDefs()
        }),
      )
      .subscribe()
  }

  formatViews() {
    this.gridViews = []
    for (const view of this.views) {
      // skip views that are not associated with the current analysis
      if (view.analysis !== this.analysisId) continue

      const messages = this.messages.filter((m) => m.analysis_property_view === view.id).map((m) => m.user_message)

      this.gridViews.push({ ...view, messages })
    }
    this.getViewGridHeight()
  }

  setColumnDefs() {
    this.columnDefs = {
      analysis: [
        { field: 'status', headerName: 'Status', cellRenderer: this.statusRenderer },
        { field: 'number_of_analysis_property_views', headerName: 'Property Count' },
        {
          field: 'created_at',
          headerName: 'Created At',
          valueFormatter: ({ value }: { value: string }) => new Date(value).toLocaleDateString(),
        },
        // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
        { field: 'cycles', headerName: 'Cycle', valueFormatter: this.getCycle.bind(this) },
        { field: 'run_duration', headerName: 'Run Duration', valueGetter: this._analysisService.getRunDuration },
      ],
      views: [
        { field: 'display_name', headerName: 'Property', cellRenderer: this.propertyRenderer },
        { field: 'results', headerName: 'Results', cellRenderer: this.resultsRenderer },
        { field: 'messages', headerName: 'Messages', cellRenderer: this.messagesRenderer, valueFormatter: () => null },
      ],
    }
  }

  statusRenderer = ({ value }: { value: string }) => {
    const style
      = value === 'Completed'
        ? 'background-color: #198754; color: white;'
        : value === 'Failed'
          ? 'background-color: #dc3545; color: white;'
          : ''
    return `<div class="overflow-hidden px-2" style="${style}">${value}</div>`
  }

  getCycle(params: { value: number[] }): string {
    if (!params.value?.length || !this.cycles.length) return ''
    const cycleId = params.value[0]
    return this.cycles.find((c) => c.id === cycleId)?.name ?? ''
  }

  propertyRenderer = (params: { value: string; data: View }) => {
    const { value, data } = params
    const name = value ?? `Property ${data.property}`
    return `
      <div class="text-primary dark:text-primary-300 cursor-pointer" title="View Property" data-action="viewProperty">
        ${name}
        <span class="material-icons text-secondary text-sm">open_in_new</span>
      </div>
    `
  }

  resultsRenderer = ({ data }: { data: View }) => {
    const downloadHTML = data.output_files.length
      ? '<span class="material-icons cursor-pointer text-secondary mt-1" data-action="download">cloud_download</span>'
      : ''

    return `
      <div class="flex gap-4">
        <div class="text-primary dark:text-primary-300 cursor-pointer" title="View Results" data-action="viewResults">
          Results
          <span class="material-icons text-secondary text-sm">open_in_new</span>
        </div>
        ${downloadHTML}
      </div>
    `
  }

  messagesRenderer({ value }: { value: string[] }) {
    if (!value) return ''
    return `
        <ul class="text-secondary">
          ${value
            .map(
              (message) => `
            <li class="list-disc pl-4 space-y-1 text-sm leading-snug">
              <div class="truncate max-w-full whitespace-nowrap overflow-hidden">${message}</div>
            </li>
          `,
            )
            .join('')}
        </ul>
      `
  }

  getViewGridHeight() {
    const div = document.querySelector('#content')
    if (!div || !this.gridViews?.length) return

    const divHeight = div.getBoundingClientRect().height ?? 500
    this.gridHeight = Math.min(this.gridViews.length * 42 + 50, divHeight * 0.9)
  }

  getRowHeight = (params: { data: View & { messages?: string[] } }) => {
    const messageHeight = params.data.messages?.length * 18 + 10
    return Math.max(42, messageHeight)
  }

  get latestMessage() {
    if (!this.messages?.length) return ''
    return this.messages[0].user_message ?? ''
  }

  onGridReady(event: GridReadyEvent) {
    this.gridApi = event.api
    this.gridApi.sizeColumnsToFit()
    this.gridApi.addEventListener('cellClicked', this.onCellClicked.bind(this) as (event: CellClickedEvent) => void)
  }

  onCellClicked(event: CellClickedEvent) {
    if (event.colDef.field === 'messages') return

    const target = event.event.target as HTMLElement
    const action = target.getAttribute('data-action')
    const { id, output_files } = event.data as View

    if (action === 'viewProperty') {
      // map viewId to propertyViewId
      const propertyViewId: number = this.originalViews[id]
      void this._router.navigate([`/properties/${propertyViewId}`])
    } else if (action === 'viewResults') {
      void this._router.navigate([`/analyses/${this.analysisId}/views/${id}`])
      // this.viewResults(id)
    } else if (action === 'download') {
      this.downloadResult(output_files)
    }
  }

  downloadResult(output_files: AnalysisOutputFile[]) {
    this._mediaService.download(output_files[0]?.file).subscribe()
  }

  meterConfig(item: KeyValue<string, unknown>) {
    const { value } = item
    const isObj = typeof value === 'object' && value !== null
    if (!isObj) return null

    const formatDate = (dateStr: string) => {
      return new Date(dateStr).toLocaleDateString()
    }

    const obj = value as Record<string, unknown>
    return `
    ${'start_date' in obj ? `<li>start_date: ${formatDate(obj.start_date as string)}</li>` : ''}
    ${'end_date' in obj ? `<li>end_date: ${formatDate(obj.end_date as string)}</li>` : ''}
    `
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
