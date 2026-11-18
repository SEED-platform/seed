import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import { Router } from '@angular/router'
import type { Observable } from 'rxjs'
import { from, map, of, tap, throwError } from 'rxjs'
import { AuthUtils } from 'app/core/auth/auth.utils'
import type { TokenResponse } from './auth.types'

@Injectable({ providedIn: 'root' })
export class AuthService {
  private _httpClient = inject(HttpClient)
  private _router = inject(Router)

  private _authenticated = false

  get accessToken(): string {
    return localStorage.getItem('accessToken') ?? ''
  }

  set accessToken(token: string) {
    localStorage.setItem('accessToken', token)
  }

  get refreshToken(): string {
    return localStorage.getItem('refreshToken') ?? ''
  }

  set refreshToken(token: string) {
    localStorage.setItem('refreshToken', token)
  }

  // TODO
  forgotPassword(email: string): Observable<unknown> {
    return this._httpClient.post('api/auth/forgot-password', email)
  }

  // TODO
  resetPassword(password: string): Observable<unknown> {
    return this._httpClient.post('api/auth/reset-password', password)
  }

  signIn(credentials: { username: string; password: string; otp_token?: string }): Observable<TokenResponse> {
    // Throw error if the user is already logged in
    if (this._authenticated) {
      return throwError(() => new Error('User is already logged in.'))
    }

    // Strip empty otp_token so the backend treats a blank field as absent
    const payload: Record<string, string> = { username: credentials.username, password: credentials.password }
    if (credentials.otp_token) payload.otp_token = credentials.otp_token

    return this._httpClient.post<TokenResponse>('/api/token/', payload).pipe(
      tap((response) => {
        if (response.access && response.refresh) {
          this.handleTokenResponse({ access: response.access, refresh: response.refresh })
        }
      }),
    )
  }

  refreshAccessToken(): Observable<boolean> {
    return this._httpClient.post<TokenResponse>('/api/token/refresh/', { refresh: this.refreshToken }).pipe(
      map((response) => {
        // The refresh endpoint always returns access + refresh tokens (no 2FA challenge).
        this.handleTokenResponse(response as { access: string; refresh: string })
        return true
      }),
    )
  }

  handleTokenResponse(response: { access: string; refresh: string }) {
    this.accessToken = response.access
    this.refreshToken = response.refresh

    // Set the authenticated flag to true
    this._authenticated = true
  }

  signOut(): Observable<boolean> {
    // Remove the tokens from the local storage
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')

    // Set the authenticated flag to false
    this._authenticated = false
    return from(this._router.navigate(['sign-in']))
  }

  // TODO
  signUp(user: { email?: string; password?: string; terms?: boolean }): Observable<unknown> {
    return this._httpClient.post('api/auth/sign-up', user)
  }

  isAuthenticated(): Observable<boolean> {
    // Check if the user is logged in
    if (this._authenticated && !AuthUtils.isTokenExpired(this.accessToken)) {
      return of(true)
    }

    // Check the access token availability
    if (!this.accessToken) {
      return of(false)
    }

    if (!this._authenticated && !AuthUtils.isTokenExpired(this.accessToken)) {
      this.handleTokenResponse({
        access: this.accessToken,
        refresh: this.refreshToken,
      })
      return of(true)
    }

    // Check the token expirations
    if (AuthUtils.isTokenExpired(this.accessToken)) {
      if (AuthUtils.isTokenExpired(this.refreshToken)) {
        return of(false)
      }

      return this.refreshAccessToken()
    }
  }
}
