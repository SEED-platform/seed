import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import type { SafeHtml } from '@angular/platform-browser'
import { DomSanitizer } from '@angular/platform-browser'
import { ActivatedRoute, RouterModule } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { ColDef, GridApi, GridReadyEvent } from 'ag-grid-community'
import type { Observable } from 'rxjs'
import { catchError, combineLatest, distinctUntilChanged, filter, forkJoin, map, of, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { AnalysesMessage, Analysis, AnalysisOutputFile, Cycle, View } from '@seed/api'
import { AnalysisService, CycleService, MediaService, OrganizationService, UserService } from '@seed/api'
import { NotFoundComponent, PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { InventoryType } from 'app/modules/inventory'

// Resolves a report's URLs against the report itself (see `_withSrcdocBase`)
const SRCDOC_BASE = '<base href="about:srcdoc">'
const HEAD_TAG = /<head(?:\s[^>]*)?>/i
const DOCTYPE = /<!doctype[^>]*>/i

// An output file fetched for display
type DisplayedOutputFile = { id: number; kind: 'html'; html: SafeHtml } | { id: number; kind: 'image'; src: string }

@Component({
  selector: 'seed-analysis-view',
  templateUrl: './analysis-view.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, MaterialImports, NotFoundComponent, PageComponent, RouterModule],
})
export class AnalysisViewComponent implements OnDestroy, OnInit {
  private _route = inject(ActivatedRoute)
  private _analysisService = inject(AnalysisService)
  private _configService = inject(ConfigService)
  private _mediaService = inject(MediaService)
  private _organizationService = inject(OrganizationService)
  private _sanitizer = inject(DomSanitizer)
  private _userService = inject(UserService)
  private _cycleService = inject(CycleService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  analysisId = Number(this._route.snapshot.paramMap.get('id'))
  analysis: Partial<Analysis> = {}
  analyses: Analysis[] = []
  cycles: Cycle[] = []
  cycle: Partial<Cycle> = {}
  messages: AnalysesMessage[] = []
  orgId: number
  apvId = Number(this._route.snapshot.paramMap.get('viewId')) // analysis_property_view_id
  view: Partial<View> = {}
  outputFiles: DisplayedOutputFile[] = []
  propertyViewId: number
  gridApi: GridApi
  viewDisplayField$: Observable<string>
  type: InventoryType = 'properties'
  rowData: Record<string, unknown>[] = []
  gridTheme$ = this._configService.gridTheme$
  columnDefs: ColDef[] = [
    { field: 'key', headerName: 'Field' },
    { field: 'value', headerName: 'Value', cellDataType: 'text' },
  ]

  ngOnInit() {
    this._userService.currentOrganizationId$
      .pipe(
        tap((orgId) => {
          this.orgId = orgId
        }),
        tap(() => {
          this._analysisService.getAnalysis(this.orgId, this.analysisId)
          this._analysisService.getMessages(this.orgId, this.analysisId)
        }),
        switchMap(() => combineLatest([this._analysisService.analysis$, this._cycleService.cycles$, this._analysisService.messages$])),
        // The shared `analysis$` can still hold a previously viewed analysis until this one loads
        filter(([analysis, cycles]) => analysis?.id === this.analysisId && cycles.length > 0),
        switchMap(([analysis, cycles, messages]) => this.getAnalysisView(analysis, cycles, messages)),
        // The analysis and messages outlive this page, so stop refetching this view into the shared `view$` on destroy
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()

    this.loadOutputFiles()
  }

  getAnalysisView(analysis: Analysis, cycles: Cycle[], messages: AnalysesMessage[]) {
    this.analysis = analysis
    this.messages = messages.filter((m) => m.analysis_property_view === this.apvId)

    return this._analysisService.getAnalysisView(this.orgId, this.analysisId, this.apvId).pipe(
      switchMap(() => combineLatest([this._analysisService.view$, this._analysisService.originalView$])),
      // `view$` is shared, so it can hold another analysis property view's response (e.g., a previous page's)
      filter(([view]) => view?.id === this.apvId),
      takeUntil(this._unsubscribeAll$),
      tap(([view, originalView]) => {
        this.view = view
        this.propertyViewId = originalView
        this.cycle = cycles.find((c) => c.id === view.cycle)
        this.viewDisplayField$ = this._organizationService.getViewDisplayField(this.propertyViewId, this.type)
        this.formatTableResults()
      }),
    )
  }

  /*
   * Fetch the view's HTML reports and images with the user's token, which iframes and images can't send.
   * The view is fetched again whenever the analysis or messages change, so only reload when its files change
   */
  loadOutputFiles() {
    this._analysisService.view$
      .pipe(
        filter((view) => view?.id === this.apvId),
        map((view) => view.output_files ?? []),
        distinctUntilChanged((previous, current) => this._outputFilesKey(previous) === this._outputFilesKey(current)),
        switchMap((files) => this._fetchOutputFiles(files)),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe((outputFiles) => {
        this.outputFiles = outputFiles
      })
  }

  formatTableResults() {
    // ignore if no parsed results or service is BETTER
    if (!Object.keys(this.view.parsed_results).length || this.analysis.service === 'BETTER') return
    this.rowData = Object.entries(this.view.parsed_results).map(([key, value]) => ({ key, value }))
  }

  onGridReady(event: GridReadyEvent) {
    this.gridApi = event.api
    this.gridApi.sizeColumnsToFit()
  }

  downloadOutputFile() {
    this._mediaService.download(this.view.output_files?.[0]?.file).subscribe()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  private _fetchOutputFiles(files: AnalysisOutputFile[]): Observable<DisplayedOutputFile[]> {
    // Other files (e.g., BuildingSync) are only downloaded
    const displayedFiles = files.filter(({ content_type }) => content_type === 'html' || content_type === 'PNG')
    if (!displayedFiles.length) return of<DisplayedOutputFile[]>([])

    const outputFiles$: Observable<DisplayedOutputFile | null>[] = displayedFiles.map((file) => this._fetchOutputFile(file))
    return forkJoin(outputFiles$).pipe(map((outputFiles) => outputFiles.filter((outputFile) => outputFile !== null)))
  }

  private _fetchOutputFile(file: AnalysisOutputFile): Observable<DisplayedOutputFile | null> {
    const outputFile$ = file.content_type === 'html' ? this._fetchReport(file) : this._fetchImage(file)
    // The media service reports the error, so still show the other files
    return outputFile$.pipe(catchError(() => of<DisplayedOutputFile | null>(null)))
  }

  private _fetchReport(file: AnalysisOutputFile): Observable<DisplayedOutputFile> {
    return this._mediaService.getText(file.file).pipe(
      // Angular's sanitizer would strip the report's scripts and styles. The iframe's sandbox isolates them instead
      map((html) => ({ id: file.id, kind: 'html', html: this._sanitizer.bypassSecurityTrustHtml(this._withSrcdocBase(html)) })),
    )
  }

  /*
   * A srcdoc document resolves URLs against the app's base href (e.g., /ng-app/), so the report's fragment links
   * (e.g., `#savings`) would navigate the frame to the app instead of scrolling. Resolve them against the report instead.
   * The base goes in the head, or after the doctype without one, since content before the doctype triggers quirks mode
   */
  private _withSrcdocBase(html: string): string {
    const tag = HEAD_TAG.exec(html) ?? DOCTYPE.exec(html)
    const index = tag ? tag.index + tag[0].length : 0
    return `${html.slice(0, index)}${SRCDOC_BASE}${html.slice(index)}`
  }

  private _fetchImage(file: AnalysisOutputFile): Observable<DisplayedOutputFile> {
    return this._mediaService.getDataUrl(file.file).pipe(map((src) => ({ id: file.id, kind: 'image', src })))
  }

  private _outputFilesKey(files: AnalysisOutputFile[]): string {
    return files.map(({ id, file }) => `${id}:${file}`).join('\n')
  }
}
