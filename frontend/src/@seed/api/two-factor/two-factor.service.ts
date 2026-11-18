import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError } from 'rxjs'
import { ErrorService } from '@seed/services'
import type {
  GenerateTwoFactorQrCodeResponse,
  ResendTwoFactorTokenEmailResponse,
  SetTwoFactorMethodResponse,
  TwoFactorMethods,
  VerifyTwoFactorCodeResponse,
} from './two-factor.types'

@Injectable({ providedIn: 'root' })
export class TwoFactorService {
  private _httpClient = inject(HttpClient)
  private _errorService = inject(ErrorService)

  /**
   * Sets the current user's two-factor method. When enabling the token method for the first
   * time, the response includes a `qr_code` to be verified before the change takes effect.
   */
  setMethod(orgId: number, userEmail: string, methods: TwoFactorMethods): Observable<SetTwoFactorMethodResponse> {
    const url = '/api/v3/two_factor/set_method/'
    const params = { organization_id: orgId }
    return this._httpClient
      .post<SetTwoFactorMethodResponse>(url, { user_email: userEmail, methods }, { params })
      .pipe(catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error updating two-factor method')))
  }

  /**
   * Sends a new two-factor email token to the user (email method only).
   */
  resendTokenEmail(orgId: number, userEmail: string): Observable<ResendTwoFactorTokenEmailResponse> {
    const url = '/api/v3/two_factor/resend_token_email/'
    const params = { organization_id: orgId }
    return this._httpClient
      .post<ResendTwoFactorTokenEmailResponse>(url, { user_email: userEmail }, { params })
      .pipe(catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error resending token email')))
  }

  /**
   * Generates a new QR code to be scanned by an authenticator app before verifying the token method.
   */
  generateQrCode(orgId: number, userEmail: string): Observable<GenerateTwoFactorQrCodeResponse> {
    const url = '/api/v3/two_factor/generate_qr_code/'
    const params = { organization_id: orgId }
    return this._httpClient
      .post<GenerateTwoFactorQrCodeResponse>(url, { user_email: userEmail }, { params })
      .pipe(catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error generating QR code')))
  }

  /**
   * Verifies a 6-digit authenticator app code against the session's pending QR code secret.
   */
  verifyCode(orgId: number, userEmail: string, code: string): Observable<VerifyTwoFactorCodeResponse> {
    const url = '/api/v3/two_factor/verify_code/'
    const params = { organization_id: orgId }
    return this._httpClient
      .post<VerifyTwoFactorCodeResponse>(url, { user_email: userEmail, code }, { params })
      .pipe(catchError((error: HttpErrorResponse) => this._errorService.handleError(error, 'Error verifying code')))
  }
}
