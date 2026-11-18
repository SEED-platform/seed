import type { HttpRequest } from '@angular/common/http'
import { Observable, of, take, throwError } from 'rxjs'
import type { MockApiReplyCallback } from '@seed/mock-api/mock-api.types'

export class MockApiHandler {
  request!: HttpRequest<unknown>
  urlParams!: Record<string, string>

  // Private
  private _reply: MockApiReplyCallback = undefined
  private _replyCount = 0
  private _replied = 0

  constructor(
    public url: string,
    public delay?: number,
  ) {}

  /**
   * Getter for response callback
   */
  get response(): Observable<unknown> {
    // If the execution limit has been reached, throw an error
    if (this._replyCount > 0 && this._replyCount <= this._replied) {
      return throwError(() => new Error('Execution limit has been reached!'))
    }

    // If the response callback has not been set, throw an error
    if (!this._reply) {
      return throwError(() => new Error('Response callback function does not exist!'))
    }

    // If the request has not been set, throw an error
    if (!this.request) {
      return throwError(() => new Error('Request does not exist!'))
    }

    // Increase the replied count
    this._replied++

    // Execute the reply callback
    const replyResult = this._reply({
      request: this.request,
      urlParams: this.urlParams,
    })

    // If the result of the reply callback is an observable...
    if (replyResult instanceof Observable) {
      // Return the result as it is
      return replyResult.pipe(take(1))
    }

    // Otherwise, return the result as an observable
    return of(replyResult).pipe(take(1))
  }

  /**
   * Reply
   *
   * @param callback
   */
  reply(callback: MockApiReplyCallback): void {
    // Store the reply
    this._reply = callback
  }

  /**
   * Reply count
   *
   * @param count
   */
  replyCount(count: number): void {
    // Store the reply count
    this._replyCount = count
  }
}
