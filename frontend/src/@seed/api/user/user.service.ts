import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, distinctUntilChanged, map, ReplaySubject, switchMap, take, tap } from 'rxjs'
import type {
  Action,
  CreateUserRequest,
  CurrentUser,
  GenerateApiKeyResponse,
  PasswordUpdateRequest,
  PasswordUpdateResponse,
  SetDefaultOrganizationResponse,
  UserAuth,
  UserAuthResponse,
  UserBrief,
  UserUpdateRequest,
} from '@seed/api'
import { ErrorService } from '@seed/services'
import { type OrganizationUserSettings } from '../organization'

@Injectable({ providedIn: 'root' })
export class UserService {
  private _httpClient = inject(HttpClient)
  private _currentOrganizationId = new ReplaySubject<number>(1)
  private _currentUser = new ReplaySubject<CurrentUser>(1)
  private _auth = new ReplaySubject<UserAuth>(1)
  private _errorService = inject(ErrorService)

  currentOrganizationId$ = this._currentOrganizationId.asObservable().pipe(distinctUntilChanged())
  currentUser$ = this._currentUser.asObservable()
  auth$ = this._auth.asObservable()

  constructor() {
    this.currentUser$
      .pipe(
        switchMap(({ id, org_id }) => {
          const actions: Action[] = ['can_invite_member', 'can_remove_member', 'requires_owner', 'requires_member', 'requires_superuser']
          return this.getUserAuthorization(org_id, id, actions)
        }),
      )
      .subscribe()
  }

  /**
   * Get the current signed-in user data
   */
  getCurrentUser(): Observable<CurrentUser> {
    return this._httpClient.get<CurrentUser>('/api/v3/users/current/').pipe(
      tap((user) => {
        this.checkUserSettings(user.settings)
        this._currentUser.next(user)
        this._currentOrganizationId.next(user.org_id)
      }),
    )
  }

  /**
   * Set default org
   */
  setDefaultOrganization(organizationId: number): Observable<SetDefaultOrganizationResponse> {
    return this.currentUser$.pipe(
      take(1),
      switchMap(({ id: userId }) => {
        return this._httpClient.put<SetDefaultOrganizationResponse>(
          `/api/v3/users/${userId}/default_organization/?organization_id=${organizationId}`,
          {},
        )
      }),
      tap(() => {
        // Refresh user info after changing the organization
        this.getCurrentUser().subscribe()
      }),
    )
  }

  /*
   * Create user
   */
  createUser(orgId: number, params: CreateUserRequest): Observable<CurrentUser> {
    return this._httpClient.post<CurrentUser>(`/api/v3/users/?organization_id=${orgId}`, params).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error creating user')
      }),
    )
  }

  /**
   * Update user
   */
  updateUser(userId: number, params: UserUpdateRequest): Observable<CurrentUser> {
    return this._httpClient.put<CurrentUser>(`/api/v3/users/${userId}/`, params).pipe(
      tap((user) => {
        this._currentUser.next(user)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating user')
      }),
    )
  }

  /**
   * Update user role
   */
  updateUserRole(userId: number, orgId: number, role: string): Observable<{ status: string }> {
    const url = `/api/v3/users/${userId}/role/?organization_id=${orgId}`
    return this._httpClient.put<{ status: string }>(url, { role }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating user role')
      }),
    )
  }

  updateUserAccessLevelInstance(userId: number, orgId: number, accessLevelInstanceId: number): Observable<{ status: string }> {
    const url = `/api/v3/users/${userId}/access_level_instance/?organization_id=${orgId}`
    return this._httpClient.put<{ status: string }>(url, { access_level_instance_id: accessLevelInstanceId }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating user access level instance')
      }),
    )
  }

  /**
   * Update user
   */
  updatePassword(params: PasswordUpdateRequest): Observable<PasswordUpdateResponse> {
    return this.currentUser$.pipe(
      take(1),
      switchMap(({ id: userId }) => {
        return this._httpClient.put<PasswordUpdateResponse>(`/api/v3/users/${userId}/set_password/`, params)
      }),
      tap(() => {
        this.getCurrentUser().subscribe()
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error updating password')
      }),
    )
  }

  /**
   * Generate API Key
   */
  generateApiKey(): Observable<GenerateApiKeyResponse> {
    return this.currentUser$.pipe(
      take(1),
      switchMap(({ id: userId }) => {
        return this._httpClient.post<GenerateApiKeyResponse>(`/api/v3/users/${userId}/generate_api_key/`, {})
      }),
      tap(() => {
        // Refresh user info after changing the API key
        this.getCurrentUser().subscribe()
      }),
    )
  }

  getUserAuthorization(orgId: number, userId: number, actions: Action[]): Observable<UserAuth> {
    const url = `/api/v3/users/${userId}/is_authorized/?organization_id=${orgId}`
    return this._httpClient.post(url, { actions }).pipe(
      map((response: UserAuthResponse) => response.auth),
      tap((auth) => {
        this._auth.next(auth)
      }),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error checking user authorization')
      }),
    )
  }

  /**
   * Get all users (superuser endpoint)
   */
  getAllUsers(): Observable<UserBrief[]> {
    return this._httpClient.get<{ users: UserBrief[] }>('/api/v3/users/').pipe(
      map((response) => response.users),
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, 'Error fetching all users')
      }),
    )
  }

  // applies defaults to an org users settings
  checkUserSettings(userSettings: OrganizationUserSettings) {
    userSettings ??= {}

    userSettings.crossCycles ??= {}
    userSettings.crossCycles.properties ??= null
    userSettings.crossCycles.taxlots ??= null

    userSettings.cycleId ??= null

    userSettings.filters ??= {}
    userSettings.filters.properties ??= {}
    userSettings.filters.taxlots ??= {}

    userSettings.labels ??= { ids: [], operator: 'and' }

    userSettings.profile ??= {}
    userSettings.profile.detail ??= {}
    userSettings.profile.detail.properties ??= null
    userSettings.profile.detail.taxlots ??= null

    userSettings.profile.list ??= {}
    userSettings.profile.list.properties ??= null
    userSettings.profile.list.taxlots ??= null

    userSettings.sorts ??= {}
    userSettings.sorts.properties ??= []
    userSettings.sorts.taxlots ??= []

    userSettings.pins ??= {}
    userSettings.pins.properties ??= { left: [], right: [] }
    userSettings.pins.taxlots ??= { left: [], right: [] }

    userSettings.insights ??= {}
    userSettings.insights.propertyInsights ??= {}
    userSettings.insights.propertyInsights.datasetVisibility ??= ['compliant', 'non-compliant', 'unknown', 'whisker']
  }
}
