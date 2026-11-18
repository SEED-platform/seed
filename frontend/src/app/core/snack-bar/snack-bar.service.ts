import { inject, Injectable } from '@angular/core'
import { MatSnackBar } from '@angular/material/snack-bar'

@Injectable({ providedIn: 'root' })
export class SnackBarService {
  private _snackBar = inject(MatSnackBar)

  alert(message: string, timeout = false, button = 'OK', timeoutLength = 3000) {
    this._displaySnackBar(message, button, 'alert', timeout, timeoutLength)
  }

  warning(message: string, timeout = true, button = 'OK', timeoutLength = 3000) {
    this._displaySnackBar(message, button, 'warning', timeout, timeoutLength)
  }

  success(message: string, timeout = true, button = 'OK', timeoutLength = 3000) {
    this._displaySnackBar(message, button, 'success', timeout, timeoutLength)
  }

  info(message: string, timeout = true, button = 'OK', timeoutLength = 3000) {
    this._displaySnackBar(message, button, 'info', timeout, timeoutLength)
  }

  private _displaySnackBar(message: string, button: string, css_class: string, timeout: boolean, timeoutLength: number) {
    if (timeout) {
      this._snackBar.open(message, button, {
        panelClass: `soft-${css_class}-snackbar`,
        duration: timeoutLength,
        horizontalPosition: 'center',
        verticalPosition: 'top',
      })
    } else {
      this._snackBar.open(message, button, {
        panelClass: `soft-${css_class}-snackbar`,
        horizontalPosition: 'center',
        verticalPosition: 'top',
      })
    }
  }
}
