import { Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { ReplaySubject } from 'rxjs'

@Injectable({ providedIn: 'root' })
export class AlertService {
  private readonly _onDismiss = new ReplaySubject<string>(1)
  private readonly _onShow = new ReplaySubject<string>(1)

  /**
   * Getter for onDismiss
   */
  get onDismiss(): Observable<string> {
    return this._onDismiss.asObservable()
  }

  /**
   * Getter for onShow
   */
  get onShow(): Observable<string> {
    return this._onShow.asObservable()
  }

  /**
   * Dismiss the alert
   *
   * @param name
   */
  dismiss(name: string): void {
    // Return if the name is not provided
    if (!name) {
      return
    }

    // Execute the observable
    this._onDismiss.next(name)
  }

  /**
   * Show the dismissed alert
   *
   * @param name
   */
  show(name: string): void {
    // Return if the name is not provided
    if (!name) {
      return
    }

    // Execute the observable
    this._onShow.next(name)
  }
}
