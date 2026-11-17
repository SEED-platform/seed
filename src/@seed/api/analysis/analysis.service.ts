import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable, Subscription } from 'rxjs'
import { BehaviorSubject, catchError, interval, map, Subject, takeUntil, takeWhile, tap, withLatestFrom } from 'rxjs'
import type { FullProgressResponse } from '@seed/api'
import { OrganizationService } from '@seed/api'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { UserService } from '../user'
import type {
  AnalysesMessage,
  Analysis,
  AnalysisCreateData,
  AnalysisResponse,
  AnalysisServiceType,
  AnalysisSummary,
  AnalysisView,
  AnalysisViews,
  ListAnalysesResponse,
  ListMessagesResponse,
  PropertyAnalysesResponse,
  UsedColumn,
  UsedColumnsResponse,
  View,
} from './analysis.types'

@Injectable({ providedIn: 'root' })
export class AnalysisService {
  private _httpClient = inject(HttpClient)
  private _organizationService = inject(OrganizationService)
  private _userService = inject(UserService)
  private _snackBar = inject(SnackBarService)
  private _errorService = inject(ErrorService)
  private _analyses = new BehaviorSubject<Analysis[]>([])
  private _analysis = new BehaviorSubject<Analysis>(null)
  private _views = new BehaviorSubject<View[]>([])
  private _view = new BehaviorSubject<View>(null)
  private _originalView = new BehaviorSubject<number>(null)
  private _originalViews = new BehaviorSubject<Record<number, number>>(null)
  private _messages = new BehaviorSubject<AnalysesMessage[]>([])
  private readonly _unsubscribeAll$ = new Subject<void>()
  orgId: number
  analyses$ = this._analyses.asObservable()
  analysis$ = this._analysis.asObservable()
  views$ = this._views.asObservable()
  view$ = this._view.asObservable()
  originalView$ = this._originalView.asObservable()
  originalViews$ = this._originalViews.asObservable()
  messages$ = this._messages.asObservable()
  pollingStatuses?: Subscription

  constructor() {
    this._userService.currentOrganizationId$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((orgId) => {
          this.orgId = orgId
          this.getAnalyses(orgId)
        }),
      )
      .subscribe()
  }

  // Method to update the analyses list
  updateAnalyses(analyses: Analysis[]): void {
    this._analyses.next(analyses)
  }

  getAnalyses(orgId: number) {
    // Views come from `getAnalysisViews` instead: the list endpoint's output files are server paths rather than URLs,
    // and pushing its views into `views$` could replace an analysis's views (e.g., while polling statuses)
    const url = `/api/v3/analyses/?organization_id=${orgId}&include_views=false`
    this._httpClient
      .get<ListAnalysesResponse>(url)
      .pipe(
        tap((response) => {
          this._analyses.next(response.analyses)
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching analyses')
        }),
      )
      .subscribe()
  }

  // get AnalysesMessages (for all analyses or for a single one)
  getMessages(orgId: number, analysisId: number) {
    const url = `/api/v3/analyses/${analysisId}/messages/?organization_id=${orgId}`
    this._httpClient
      .get<ListMessagesResponse>(url)
      .pipe(
        map((response) => response.messages),
        tap((response) => {
          this._messages.next(response)
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching analyses messages')
        }),
      )
      .subscribe()
  }

  // get single analysis
  getAnalysis(orgId: number, analysisId: number) {
    const url = `/api/v3/analyses/${analysisId}?organization_id=${orgId}`
    this._httpClient
      .get<AnalysisResponse>(url)
      .pipe(
        map((response) => response.analysis),
        tap((analysis) => {
          this._analysis.next(analysis)
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching analyses')
        }),
      )
      .subscribe()
  }

  // get analyses for a property (by property ID)
  getPropertyAnalyses(_propertyId): Observable<Analysis[]> {
    const url = `/api/v3/properties/${_propertyId}/analyses/?organization_id=${this.orgId}`
    return this._httpClient.get<PropertyAnalysesResponse>(url).pipe(
      map((response) => response.analyses),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching analyses for this property')
      }),
    )
  }

  // get analysis views
  getAnalysisViews(orgId: number, analysisId: number) {
    const url = `/api/v3/analyses/${analysisId}/views?organization_id=${orgId}`
    this._httpClient
      .get<AnalysisViews>(url)
      .pipe(
        tap((response) => {
          this._views.next(response.views)
          this._originalViews.next(response.original_views)
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching analyses')
        }),
      )
      .subscribe()
  }

  // get analysis view
  getAnalysisView(orgId: number, analysisId: number, viewId: number): Observable<AnalysisView> {
    const url = `/api/v3/analyses/${analysisId}/views/${viewId}/?organization_id=${orgId}`
    return this._httpClient.get<AnalysisView>(url).pipe(
      tap(({ view, original_view }) => {
        this._view.next(view)
        this._originalView.next(original_view)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching analysis view')
      }),
    )
  }

  // delete analysis
  delete(orgId: number, id: number) {
    const url = `/api/v3/analyses/${id}/?organization_id=${this.orgId}`
    return this._httpClient.delete(url).pipe(
      tap(() => {
        this._snackBar.success('Analysis deleted successfully')
        this.getAnalyses(orgId)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting analysis')
      }),
    )
  }

  create(orgId: number, data: AnalysisCreateData): Observable<FullProgressResponse> {
    const url = `/api/v3/analyses/?organization_id=${orgId}&start_analysis=true`
    return this._httpClient.post<FullProgressResponse>(url, data).pipe(
      tap((response) => {
        if (response.status === 'error') {
          return this._errorService.handleError(response.errors as HttpErrorResponse, 'Error creating analysis')
        }
        this._snackBar.success('Running Analysis')
        this.getAnalyses(orgId)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating analysis')
      }),
    )
  }

  // Get all property and taxlot columns that have data in them for an org (used by Public Data Sharing)
  getUsedColumns(orgId: number): Observable<UsedColumn[]> {
    const url = `/api/v3/analyses/used_columns/?organization_id=${orgId}`
    return this._httpClient.get<UsedColumnsResponse>(url).pipe(
      map((response) => response.columns),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching used columns')
      }),
    )
  }

  summary(orgId: number, cycleId: number): Observable<AnalysisSummary> {
    const url = `/api/v4/analyses/stats/?cycle_id=${cycleId}&organization_id=${orgId}`
    return this._httpClient.get<AnalysisSummary>(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching analysis summary')
      }),
    )
  }

  stopAnalysis(orgId: number, analysisId: number): Observable<Analysis> {
    const url = `/api/v3/analyses/${analysisId}/stop/?organization_id=${orgId}`
    return this._httpClient.post<Analysis>(url, {}).pipe(
      tap((data) => {
        console.log('Analysis stopped:', data)
        this._snackBar.success('Analysis stopped successfully')
        this.getAnalyses(orgId)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error stopping analysis')
      }),
    )
  }

  startAnalysis(orgId: number, analysisId: number): Observable<Analysis> {
    const url = `/api/v3/analyses/${analysisId}/start/?organization_id=${orgId}`
    return this._httpClient.post<Analysis>(url, {}).pipe(
      tap((data) => {
        console.log('Analysis started:', data)
        this._snackBar.success('Analysis started')
        this.getAnalyses(orgId)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error starting analysis')
      }),
    )
  }

  /*
   * Poll for analysis statuses
   * Fetch analyses every 5 seconds until all analyses are in a terminal state
   */
  pollStatuses(orgId: number) {
    const isPolling = this.pollingStatuses && !this.pollingStatuses.closed
    if (isPolling) return

    const runningStatuses = new Set(['Pending Creation', 'Creating', 'Queued', 'Running'])
    this.pollingStatuses = interval(5000)
      .pipe(
        withLatestFrom(this.analyses$),
        takeWhile(([_, analyses]) => analyses.some((a) => runningStatuses.has(a.status)), true),
        tap(() => {
          this.getAnalyses(orgId)
        }),
      )
      .subscribe()
  }

  getAnalysisDescription(analysis: Analysis): string {
    const descriptionMap: Record<AnalysisServiceType, string> = {
      BETTER:
        "The BETTER analysis leverages better.lbl.gov to calculate energy, cost, and GHG emission savings by comparing the property's change point model with a benchmarked model. The results include saving potential and a list of recommended high-level energy conservation measures.",
      BSyncr:
        'The BSyncr analysis leverages the Normalized Metered Energy Consumption (NMEC) analysis to calculate a change point model. The data are passed to the analysis using BuildingSync. The result of the analysis are the coefficients of the change point model.',
      'Building Upgrade Recommendation':
        'The Building Upgrade Recommendation analysis implements a workflow to identify buildings that may need a deep energy retrofit, equipment replaced or re-tuning based on building attributes such as energy use, year built, and square footage. If your organization contains elements, the Element Statistics Analysis should be run prior to running this analysis.',
      CO2: "This analysis calculates the average annual CO2 emissions for the property's meter data. The analysis requires an eGRID Subregion to be defined in order to accurately determine the emission rates.",
      EEEJ: "The EEEJ Analysis uses each property's address to identify the 2010 census tract. Based on census tract, disadvantaged community classification and energy burden information can be retrieved from the CEJST dataset. The number of affordable housing locations is retrieved from HUD datasets. Location is used to generate a link to view an EJScreen Report providing more demographic indicators.",
      EUI: "The EUI analysis will sum the property's meter readings for the last twelve months to calculate the energy use per square footage per year. If there are missing meter readings, then the analysis will return a less that 100% coverage to alert the user that there is a missing meter reading.",
      'Element Statistics':
        "The Element Statistics analysis looks through a property's element data (if any) to count the number of elements of type 'D.D.C. Control Panel'. It also generates the aggregated (average) condition index values for scope 1 emission elements and saves those quantities to the property.",
      'HVAC Metrics':
        'The HVAC Metrics analysis calculates HVAC-related metrics for the property based on floor area and available meter data.',
    }
    return descriptionMap[analysis.service] ?? 'No description available for this analysis.'
  }

  getRunDuration({ data }: { data: Analysis }) {
    if (!data.start_time || !data.end_time) return ''

    const start = new Date(data.start_time)
    const end = new Date(data.end_time)
    const duration = Math.abs(end.getTime() - start.getTime())
    const minutes = Math.floor((duration % (1000 * 60 * 60)) / (1000 * 60))
    const seconds = Math.floor((duration % (1000 * 60)) / 1000)
    return `${minutes}m ${seconds}s`
  }
}
