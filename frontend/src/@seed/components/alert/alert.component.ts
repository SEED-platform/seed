import type { OnDestroy, OnInit } from '@angular/core'
import {
  booleanAttribute,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  HostBinding,
  inject,
  input,
  model,
  output,
  ViewEncapsulation,
} from '@angular/core'
import { filter, Subject, takeUntil } from 'rxjs'
import { Animations } from '@seed/animations'
import { MaterialImports } from '@seed/materials'
import { randomId } from '@seed/utils'
import { AlertService } from './alert.service'
import type { AlertAppearance, AlertType } from './alert.types'

@Component({
  selector: 'seed-alert',
  templateUrl: './alert.component.html',
  styleUrl: './alert.component.scss',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: Animations,
  exportAs: 'seedAlert',
  imports: [MaterialImports],
})
export class AlertComponent implements OnInit, OnDestroy {
  private _alertService = inject(AlertService)
  private _changeDetectorRef = inject(ChangeDetectorRef)

  appearance = input<AlertAppearance>('soft')
  dismissed = model(false)
  dismissible = input(false, { transform: booleanAttribute })
  name = input(randomId())
  showIcon = input(true, { transform: booleanAttribute })
  type = input<AlertType>('primary')
  dismissedChanged = output<boolean>()

  private readonly _unsubscribeAll$ = new Subject<void>()

  @HostBinding('class') get classList(): Record<string, boolean> {
    return {
      'seed-alert-appearance-border': this.appearance() === 'border',
      'seed-alert-appearance-fill': this.appearance() === 'fill',
      'seed-alert-appearance-outline': this.appearance() === 'outline',
      'seed-alert-appearance-soft': this.appearance() === 'soft',
      'seed-alert-dismissed': this.dismissed(),
      'seed-alert-dismissible': this.dismissible(),
      'seed-alert-show-icon': this.showIcon(),
      'seed-alert-type-primary': this.type() === 'primary',
      'seed-alert-type-accent': this.type() === 'accent',
      'seed-alert-type-warn': this.type() === 'warn',
      'seed-alert-type-basic': this.type() === 'basic',
      'seed-alert-type-info': this.type() === 'info',
      'seed-alert-type-success': this.type() === 'success',
      'seed-alert-type-warning': this.type() === 'warning',
      'seed-alert-type-error': this.type() === 'error',
    }
  }

  ngOnInit(): void {
    // Subscribe to the dismiss calls
    this._alertService.onDismiss
      .pipe(
        filter((name) => this.name() === name),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe(() => {
        // Dismiss the alert
        this.dismiss()
      })

    // Subscribe to the show calls
    this._alertService.onShow
      .pipe(
        filter((name) => this.name() === name),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe(() => {
        // Show the alert
        this.show()
      })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  /**
   * Dismiss the alert
   */
  dismiss(): void {
    // Return if the alert is already dismissed
    if (this.dismissed()) {
      return
    }

    // Dismiss the alert
    this._toggleDismiss(true)
  }

  /**
   * Show the dismissed alert
   */
  show(): void {
    // Return if the alert is already showing
    if (!this.dismissed()) {
      return
    }

    // Show the alert
    this._toggleDismiss(false)
  }

  /**
   * Dismiss/show the alert
   */
  private _toggleDismiss(dismissed: boolean): void {
    // Return if the alert is not dismissible
    if (!this.dismissible()) {
      return
    }

    // Set the dismissed
    this.dismissed.set(dismissed)

    // Emit the event
    this.dismissedChanged.emit(this.dismissed())

    // Notify the change detector
    this._changeDetectorRef.markForCheck()
  }
}
