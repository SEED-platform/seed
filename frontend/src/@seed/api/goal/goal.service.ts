import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { BehaviorSubject, catchError, map, take, tap } from 'rxjs'
import { OrganizationService } from '@seed/api/organization'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type {
  CycleGoal,
  CycleGoalsResponse,
  Goal,
  GoalNote,
  GoalPropertiesResponse,
  GoalsResponse,
  HistoricalNote,
  PortfolioSummary,
  SalesforceSummaryResponse,
  weightedEUIsResponse,
} from './goal.types'

@Injectable({ providedIn: 'root' })
export class GoalService {
  private _httpClient = inject(HttpClient)
  private _organizationService = inject(OrganizationService)
  private _snackBar = inject(SnackBarService)
  private _errorService = inject(ErrorService)
  private _goals = new BehaviorSubject<Goal[]>([])
  private _portfolioSummary = new BehaviorSubject<PortfolioSummary | null>(null)
  orgId: number

  goals$ = this._goals.asObservable()

  constructor() {
    this._organizationService.currentOrganization$
      .pipe(
        tap(({ org_id }) => {
          this.get(org_id)
          this.orgId = org_id
        }),
      )
      .subscribe()
  }

  get(orgId: number) {
    const url = `/api/v3/goals/?organization_id=${orgId}`
    this._httpClient
      .get<GoalsResponse>(url)
      .pipe(
        take(1),
        map(({ goals }) => goals),
        tap((goals) => {
          this._goals.next(goals)
        }),
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching goals')
        }),
      )
      .subscribe()
  }

  getPortfolioSummary(goalId: number, cycleGoalId: number, orgId: number): Observable<PortfolioSummary> {
    const url = `/api/v3/goals/${goalId}/cycles/${cycleGoalId}/portfolio_summary?organization_id=${orgId}`
    return this._httpClient.get<PortfolioSummary>(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching summary: ${error.message}`)
      }),
    )
  }

  getWeightedEUIs(goalId: number, orgId: number): Observable<weightedEUIsResponse> {
    const url = `/api/v3/goals/${goalId}/get_weighted_euis/?organization_id=${orgId}`
    return this._httpClient.get<weightedEUIsResponse>(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching summary: ${error.message}`)
      }),
    )
  }

  editGoal(goalId: number, editedGoal, orgId: number): Observable<Goal> {
    const url = `/api/v3/goals/${goalId}/?organization_id=${orgId}`
    return this._httpClient.put<Goal>(url, editedGoal).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching summary: ${error.message}`)
      }),
    )
  }

  createGoal(newGoal, orgId: number): Observable<Goal> {
    const url = `/api/v3/goals/?organization_id=${orgId}`
    return this._httpClient.post<Goal>(url, { ...newGoal, organization: orgId }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching summary: ${error.message}`)
      }),
    )
  }

  createCycleGoal(goalId: number, cycleId: number, annual_report_id?: string, annual_report_name?: string): Observable<CycleGoal> {
    const url = `/api/v3/goals/${goalId}/cycles/?organization_id=${this.orgId}`
    return this._httpClient
      .post<CycleGoal>(url, {
        current_cycle: cycleId,
        salesforce_annual_report_id: annual_report_id,
        salesforce_annual_report_name: annual_report_name,
      })
      .pipe(
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, `Error fetching summary: ${error.message}`)
        }),
      )
  }

  getCycleGoals(goalId: number, orgId: number): Observable<CycleGoal[]> {
    const url = `/api/v3/goals/${goalId}/cycles/?organization_id=${orgId}`
    return this._httpClient.get<CycleGoalsResponse>(url).pipe(
      map(({ cycle_goals }) => cycle_goals),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, `Error fetching cycle goals: ${error.message}`)
      }),
    )
  }

  deleteGoal(goalId: number, orgId: number): Observable<unknown> {
    const url = `/api/v3/goals/${goalId}/?organization_id=${orgId}`
    return this._httpClient.delete(url).pipe(
      tap(() => {
        this._goals.next(this._goals.value.filter((g) => g.id !== goalId))
        this._snackBar.success('Goal deleted')
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting goal')
      }),
    )
  }

  deleteCycleGoal(goalId: number, cycleGoalId: number): Observable<unknown> {
    const url = `/api/v3/goals/${goalId}/cycles/${cycleGoalId}/?organization_id=${this.orgId}`
    return this._httpClient.delete(url).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error deleting cycle goal')
      }),
    )
  }

  editCycleGoal(
    goalId: number,
    cycleGoalId: number,
    cycleId: number,
    annualReportId?: string,
    annualReportName?: string,
  ): Observable<CycleGoal> {
    const url = `/api/v3/goals/${goalId}/cycles/${cycleGoalId}/?organization_id=${this.orgId}`
    return this._httpClient
      .put<CycleGoal>(url, {
        current_cycle: cycleId,
        salesforce_annual_report_id: annualReportId,
        salesforce_annual_report_name: annualReportName,
      })
      .pipe(
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error updating cycle goal')
        }),
      )
  }

  getProperties(goalId: number, cycleGoalId: number, orgId: number, page = 1, perPage = 50): Observable<GoalPropertiesResponse> {
    const url = `/api/v3/goals/${goalId}/cycles/${cycleGoalId}/data/?organization_id=${orgId}`
    const accessLevelInstanceId = this._goals.value.find((g) => g.id === goalId)?.access_level_instance
    return this._httpClient
      .put<GoalPropertiesResponse>(url, {
        goal_id: goalId,
        cycle_goal_id: cycleGoalId,
        per_page: perPage,
        page,
        baseline_first: true,
        access_level_instance_id: accessLevelInstanceId,
      })
      .pipe(
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error fetching properties')
        }),
      )
  }

  updateGoalNote(
    propertyId: number,
    goalNoteId: number,
    data: Partial<Pick<GoalNote, 'question' | 'resolution' | 'passed_checks' | 'new_or_acquired'>>,
  ): Observable<GoalNote> {
    const url = `/api/v3/properties/${propertyId}/goal_notes/${goalNoteId}/?organization_id=${this.orgId}`
    return this._httpClient.put<GoalNote>(url, data).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating goal note')
      }),
    )
  }

  getPropertyViewIds(goalId: number, cycleGoalId: number, orgId: number): Observable<number[]> {
    const url = `/api/v4/goals/${goalId}/cycles/${cycleGoalId}/property_view_ids/?organization_id=${orgId}`
    return this._httpClient.get<{ property_view_ids: number[] }>(url).pipe(
      map(({ property_view_ids }) => property_view_ids),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching property view IDs')
      }),
    )
  }

  updateHistoricalNote(propertyId: number, historicalNoteId: number, data: { text: string }): Observable<HistoricalNote> {
    const url = `/api/v3/properties/${propertyId}/historical_notes/${historicalNoteId}/?organization_id=${this.orgId}`
    const payload = { id: historicalNoteId, property: propertyId, text: data.text }
    return this._httpClient.put<HistoricalNote>(url, payload).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating historical note')
      }),
    )
  }

  bulkUpdateGoalNotes(
    goalId: number,
    propertyViewIds: number[],
    data: Partial<{
      question: string | null;
      resolution: string | null;
      historical_note: string;
      passed_checks: boolean;
      new_or_acquired: boolean;
    }>,
  ): Observable<{ status: string; message: string }> {
    const url = `/api/v3/goals/${goalId}/bulk_update_goal_notes/?organization_id=${this.orgId}`
    return this._httpClient.put<{ status: string; message: string }>(url, { property_view_ids: propertyViewIds, data }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error bulk updating goal notes')
      }),
    )
  }

  getSalesforceSummary(goalId: number, orgId: number): Observable<SalesforceSummaryResponse> {
    const url = `/api/v3/goals/${goalId}/salesforce_summary/?organization_id=${orgId}`
    return this._httpClient.get<SalesforceSummaryResponse>(url)
  }

  updateSalesforceCurrent(
    goalId: number,
    cycleGoalId: number,
    reportStatus: string | null,
    reviewStatus: string | null,
    orgId: number,
  ): Observable<{ status: string }> {
    const url = `/api/v3/goals/${goalId}/update_salesforce_current/?organization_id=${orgId}`
    return this._httpClient
      .put<{ status: string }>(url, { cycle_goal_id: cycleGoalId, report_status: reportStatus, review_status: reviewStatus })
      .pipe(
        catchError((error: HttpErrorResponse) => {
          return this._errorService.handleError(error, 'Error syncing current report to Salesforce')
        }),
      )
  }

  updateSalesforceHistorical(goalId: number, cycleGoalIds: number[], orgId: number): Observable<{ status: string }> {
    const url = `/api/v3/goals/${goalId}/update_salesforce_historical/?organization_id=${orgId}`
    return this._httpClient.put<{ status: string }>(url, { cycle_goal_ids: cycleGoalIds }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error syncing historical reports to Salesforce')
      }),
    )
  }
}
