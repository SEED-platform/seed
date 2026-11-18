// -----------------------------------------------------------------------------------------------------
// @ AUTH UTILITIES
//
// Methods are derivations of the Auth0 Angular-JWT helper service methods
// https://github.com/auth0/angular2-jwt
// -----------------------------------------------------------------------------------------------------
import { jwtDecode } from 'jwt-decode'
import type { UserToken } from './auth.types'

export class AuthUtils {
  static isTokenExpired(token: string): boolean {
    // Return if there is no token
    if (!token) {
      return true
    }

    // Get the expiration date
    const expiration = this._getTokenExpirationDate(token)

    if (expiration === null) {
      return true
    }

    // Check if the token is expired
    return expiration.valueOf() <= Date.now()
  }

  private static _decodeToken(token: string): UserToken | null {
    // Return null if there is no token
    return token ? jwtDecode<UserToken>(token) : null
  }

  /**
   * Get token expiration date
   *
   * @param token
   * @private
   */
  private static _getTokenExpirationDate(token: string): Date | null {
    // Return null if the decodedToken doesn't have an 'exp' field
    const { exp } = this._decodeToken(token) ?? {}
    return exp ? new Date(exp * 1_000) : null
  }
}
