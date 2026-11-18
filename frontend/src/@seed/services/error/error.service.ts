import type { HttpErrorResponse } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import { throwError } from 'rxjs'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Injectable({ providedIn: 'root' })
export class ErrorService {
  private _snackBar = inject(SnackBarService)

  handleError(error: HttpErrorResponse, defaultMessage: string) {
    let errorMessage = defaultMessage
    const errorData = this.getErrorData(error, defaultMessage)

    if (typeof errorData === 'string') {
      errorMessage = errorData
    } else if (this.isObjOfArrayStrings(errorData)) {
      errorMessage = this.formatObjOrArrayStrings(errorData)
    }

    errorMessage = this.formatErrorMessage(errorMessage)
    this._snackBar.alert(errorMessage)
    return throwError(() => new Error(error?.message || defaultMessage))
  }

  getErrorData(error: HttpErrorResponse, defaultMessage: string) {
    // Handle different error response structures
    const err: unknown = error.error
    const status = error.status ? `${error.status}: ` : ''

    const isStr = typeof err === 'string'

    // If the string is too long (likely html '<!DOCTYPE html>...'), return the default message
    if (isStr && (err.length > 1000 || err.startsWith('<!DOCTYPE html>'))) {
      return `${status}${defaultMessage}`
    }
    if (isStr) return err

    const isObj = typeof err === 'object' && err !== null
    if (isObj) {
      const e = err as Record<string, unknown>
      return e.message ?? e.error ?? e.errors ?? null
    }

    return `${status}${defaultMessage}`
  }

  isObjOfArrayStrings(obj: unknown): obj is Record<string, string[]> {
    // is it an object of string arrays?
    // e.g. { x: ['y', 'z']} => true
    return (
      typeof obj === 'object'
      && obj !== null
      && Object.values(obj).every((value) => Array.isArray(value) && value.every((item) => typeof item === 'string'))
    )
  }

  formatObjOrArrayStrings(obj: Record<string, string[]>): string {
    // format if error is an object of string arrays
    // e.g. { x: ['y', 'z']} => 'x: y, z'
    return Object.entries(obj)
      .map(([key, value]) => `${key}: ${value.join(', ')}`)
      .join(' ')
  }

  formatErrorMessage(error: unknown): string {
    const formatted = JSON.stringify(error)
      // eslint-disable-next-line no-useless-escape
      .replace(/[{}\[\]"]/g, '') // remove brackets and quotes
      .replace(/,/g, '\n') // put newlines after commas
      .replace(/:/g, ': ') // space after colon
    return formatted
  }
}
