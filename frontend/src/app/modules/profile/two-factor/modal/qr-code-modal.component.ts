import type { OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { TranslocoService } from '@jsverse/transloco'
import { Subject, takeUntil } from 'rxjs'
import { TwoFactorService } from '@seed/api'
import { ModalHeaderComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-profile-two-factor-qr-code-modal',
  templateUrl: './qr-code-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ModalHeaderComponent, ReactiveFormsModule, SharedImports],
})
export class QrCodeModalComponent implements OnDestroy {
  private _dialogRef = inject(MatDialogRef<QrCodeModalComponent>)
  private _snackBar = inject(SnackBarService)
  private _transloco = inject(TranslocoService)
  private _twoFactorService = inject(TwoFactorService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  data = inject(MAT_DIALOG_DATA) as { orgId: number; userEmail: string; qrCodeImg: string }
  qrCodeImg = this.data.qrCodeImg
  verifying = false
  regenerating = false

  codeForm = new FormGroup({
    code: new FormControl('', [Validators.required, Validators.pattern(/^\d{6}$/)]),
  })

  verify(): void {
    if (this.codeForm.invalid || this.verifying) return

    this.verifying = true
    const code = this.codeForm.getRawValue().code

    this._twoFactorService
      .verifyCode(this.data.orgId, this.data.userEmail, code)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe({
        next: (response) => {
          this.verifying = false
          if (response.success) {
            this._snackBar.success(this._transloco.translate('Authenticator App Verified!'))
            this.close(true)
          } else {
            const errorMsg: string = response.error ?? this._transloco.translate('Unable to verify code. Please try again.')
            this.codeForm.controls.code.setErrors({ serverError: errorMsg })
          }
        },
        error: () => {
          this.verifying = false
        },
      })
  }

  regenerate(): void {
    this.regenerating = true
    this._twoFactorService
      .generateQrCode(this.data.orgId, this.data.userEmail)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe({
        next: (response) => {
          this.regenerating = false
          this.qrCodeImg = `data:image/png;base64,${response.qr_code}`
        },
        error: () => {
          this.regenerating = false
        },
      })
  }

  close(verified = false): void {
    this._dialogRef.close(verified)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
