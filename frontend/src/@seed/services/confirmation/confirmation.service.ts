import { inject, Injectable } from '@angular/core'
import type { MatDialogRef } from '@angular/material/dialog'
import { MatDialog } from '@angular/material/dialog'
import type { ConfirmationConfig } from '@seed/services'
import { ConfirmationDialogComponent } from './dialog'

@Injectable({ providedIn: 'root' })
export class ConfirmationService {
  private _matDialog: MatDialog = inject(MatDialog)
  private _defaultConfig: ConfirmationConfig = {
    title: 'Confirm action',
    message: 'Are you sure you want to confirm this action?',
    width: 'normal',
    icon: {
      show: true,
      name: 'heroicons-outline:exclamation-triangle',
      color: 'warn',
    },
    actions: {
      confirm: {
        show: true,
        label: 'Confirm',
        color: 'warn',
      },
      cancel: {
        show: true,
        label: 'Cancel',
      },
    },
    dismissible: false,
  }

  open(config: ConfirmationConfig = {}): MatDialogRef<ConfirmationDialogComponent> {
    // Deep merge the user config with the default config
    const userConfig = {
      ...this._defaultConfig,
      ...config,
      icon: {
        ...this._defaultConfig.icon,
        ...config.icon,
      },
      actions: {
        confirm: {
          ...this._defaultConfig.actions.confirm,
          ...config.actions?.confirm,
        },
        cancel: {
          ...this._defaultConfig.actions.cancel,
          ...config.actions?.cancel,
        },
      },
    }

    // Open the dialog
    return this._matDialog.open(ConfirmationDialogComponent, {
      width: userConfig.width === 'wide' ? '1024px' : undefined,
      autoFocus: false,
      disableClose: !userConfig.dismissible,
      data: userConfig,
      panelClass: 'seed-confirmation-dialog-panel',
    })
  }
}
