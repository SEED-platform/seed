import { inject, Injectable } from '@angular/core'
import type { WordArray } from 'crypto-es'
import { Base64, HmacSHA256, Utf8 } from 'crypto-es'
import type { CurrentUser } from '@seed/api'
import { MockApiService } from '@seed/mock-api'
import { user as userData } from 'app/mock-api/common/user/data'

@Injectable({ providedIn: 'root' })
export class AuthMockApi {
  private _mockApiService = inject(MockApiService)

  private readonly _secret: string
  private _user: CurrentUser = userData

  constructor() {
    // Set the mock-api
    this._secret = 'YOUR_VERY_CONFIDENTIAL_SECRET_FOR_SIGNING_JWT_TOKENS!!!'

    // Register Mock API handlers
    this.registerHandlers()
  }

  /**
   * Register Mock API handlers
   */
  registerHandlers(): void {
    // -----------------------------------------------------------------------------------------------------
    // @ Forgot password - POST
    // -----------------------------------------------------------------------------------------------------
    this._mockApiService.onPost('api/auth/forgot-password', 1000).reply(() => [200, true])

    // -----------------------------------------------------------------------------------------------------
    // @ Reset password - POST
    // -----------------------------------------------------------------------------------------------------
    this._mockApiService.onPost('api/auth/reset-password', 1000).reply(() => [200, true])

    // -----------------------------------------------------------------------------------------------------
    // @ Sign in - POST
    // -----------------------------------------------------------------------------------------------------
    this._mockApiService.onPost('api/auth/sign-in', 1500).reply(({ request }) => {
      // Sign in successful
      const body = request.body as Record<string, string>
      if (body.email === 'alex.swindler@nlr.gov' && body.password === 'password') {
        return [
          200,
          {
            user: structuredClone(this._user),
            accessToken: this._generateJWTToken(),
            tokenType: 'bearer',
          },
        ]
      }

      // Invalid credentials
      return [404, false]
    })

    // -----------------------------------------------------------------------------------------------------
    // @ Sign in using the access token - POST
    // -----------------------------------------------------------------------------------------------------
    this._mockApiService.onPost('api/auth/sign-in-with-token').reply(({ request }) => {
      // Get the access token
      const { accessToken } = request.body as Record<string, string>

      // Verify the token
      if (this._verifyJWTToken(accessToken)) {
        return [
          200,
          {
            user: structuredClone(this._user),
            accessToken: this._generateJWTToken(),
            tokenType: 'bearer',
          },
        ]
      }

      // Invalid token
      return [
        401,
        {
          error: 'Invalid token',
        },
      ]
    })

    // -----------------------------------------------------------------------------------------------------
    // @ Sign up - POST
    // -----------------------------------------------------------------------------------------------------
    this._mockApiService.onPost('api/auth/sign-up', 1500).reply(() =>
      // Simply return true
      [200, true],
    )
  }

  /**
   * Return base64 encoded version of the given string
   *
   * @param source
   * @private
   */
  private _base64url(source: WordArray): string {
    // Encode in classical base64
    let encodedSource = Base64.stringify(source)

    // Remove padding equal characters
    encodedSource = encodedSource.replace(/=+$/, '')

    // Replace characters according to base64url specifications
    encodedSource = encodedSource.replace(/\+/g, '-')
    encodedSource = encodedSource.replace(/\//g, '_')

    // Return the base64 encoded string
    return encodedSource
  }

  /**
   * Generates a JWT token using CryptoJS library.
   *
   * This generator is for mocking purposes only and it is NOT
   * safe to use it in production frontend applications!
   *
   * @private
   */
  private _generateJWTToken(): string {
    // Define token header
    const header = {
      alg: 'HS256',
      typ: 'JWT',
    }

    // Calculate the issued at and expiration dates
    const date = new Date()
    const iat = Math.floor(date.getTime() / 1000)
    const exp = Math.floor(date.setDate(date.getDate() + 7) / 1000)

    // Define token payload
    const payload = {
      iat,
      iss: 'SEED',
      exp,
    }

    // Stringify and encode the header
    const stringifiedHeader = Utf8.parse(JSON.stringify(header))
    const encodedHeader = this._base64url(stringifiedHeader)

    // Stringify and encode the payload
    const stringifiedPayload = Utf8.parse(JSON.stringify(payload))
    const encodedPayload = this._base64url(stringifiedPayload)

    // Sign the encoded header and mock-api
    let signature: WordArray | string = `${encodedHeader}.${encodedPayload}`
    signature = HmacSHA256(signature, this._secret)
    signature = this._base64url(signature)

    // Build and return the token
    return `${encodedHeader}.${encodedPayload}.${signature}`
  }

  /**
   * Verify the given token
   *
   * @param token
   * @private
   */
  private _verifyJWTToken(token: string): boolean {
    // Split the token into parts
    const parts = token.split('.')
    const header = parts[0]
    const payload = parts[1]
    const signature = parts[2]

    // Re-sign and encode the header and payload using the secret
    const signatureCheck = this._base64url(HmacSHA256(`${header}.${payload}`, this._secret))

    // Verify that the resulting signature is valid
    return signature === signatureCheck
  }
}
