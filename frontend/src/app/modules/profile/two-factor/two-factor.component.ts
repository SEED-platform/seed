import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms'
import { MatDialog } from '@angular/material/dialog'
import { TranslocoService } from '@jsverse/transloco'
import type { Observable } from 'rxjs'
import { Subject, take, takeUntil } from 'rxjs'
import type { CurrentUser, Organization, TwoFactorMethod, TwoFactorMethods } from '@seed/api'
import { OrganizationService, TwoFactorService, UserService } from '@seed/api'
import { AlertComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { QrCodeModalComponent } from './modal/qr-code-modal.component'

@Component({
  selector: 'seed-profile-two-factor',
  templateUrl: './two-factor.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, MaterialImports, ReactiveFormsModule, SharedImports],
})
export class ProfileTwoFactorComponent implements OnInit, OnDestroy {
  private _dialog = inject(MatDialog)
  private _organizationService = inject(OrganizationService)
  private _snackBar = inject(SnackBarService)
  private _transloco = inject(TranslocoService)
  private _twoFactorService = inject(TwoFactorService)
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  loading = true
  saving = false
  emailSent = false
  user: CurrentUser
  requiresOrg2fa = false
  orgsRequiring2fa = ''

  methodForm = new FormGroup({
    method: new FormControl<TwoFactorMethod>('disabled', { nonNullable: true }),
  })

  ngOnInit(): void {
    this._userService.currentUser$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((user) => {
      this.user = user
      this.methodForm.get('method').setValue(user.two_factor_method)
      this.emailSent = false
    })
    ;(this._organizationService.get() as Observable<Organization[]>).pipe(take(1), takeUntil(this._unsubscribeAll$)).subscribe({
      next: (organizations) => {
        const requiring = organizations.filter((org) => org.user_role && org.require_2fa)
        this.requiresOrg2fa = requiring.length > 0
        this.orgsRequiring2fa = requiring.map((org) => org.name).join(', ')
        this.loading = false
      },
      error: () => {
        this.loading = false
      },
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  get methodUnchanged(): boolean {
    return !this.user || this.methodForm.value.method === this.user.two_factor_method
  }

  get emailHelpText(): string {
    // TWO_FACTOR_EMAIL_SELECTED_TEXT uses a legacy `{email}` placeholder (not Transloco's `{{}}`
    // interpolation syntax), so the substitution is done manually here.
    const template = this._transloco.translate('TWO_FACTOR_EMAIL_SELECTED_TEXT')
    return template.replace('{email}', this.user?.email ?? '')
  }

  save(): void {
    if (this.methodUnchanged || this.saving) return

    this.saving = true
    const method = this.methodForm.getRawValue().method
    const methods: TwoFactorMethods = {
      disabled: method === 'disabled',
      email: method === 'email',
      token: method === 'token',
    }

    this._twoFactorService
      .setMethod(this.user.org_id, this.user.email, methods)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe({
        next: (response) => {
          this.saving = false
          this._refreshUser()
          if (response.qr_code) {
            this._openQrCodeModal(response.qr_code)
          } else if (response.status === 'error') {
            this._snackBar.alert(response.message ?? this._transloco.translate('Error updating two-factor method'))
          } else {
            this._snackBar.success(this._transloco.translate('Changes Saved'))
          }
        },
        error: () => {
          this.saving = false
        },
      })
  }

  resendTokenEmail(): void {
    if (!confirm(`Resend a test email token to ${this.user.email}?`)) return

    this._twoFactorService
      .resendTokenEmail(this.user.org_id, this.user.email)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe(() => {
        this.emailSent = true
      })
  }

  regenerateQrCode(): void {
    this._twoFactorService
      .generateQrCode(this.user.org_id, this.user.email)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe((response) => {
        this._openQrCodeModal(response.qr_code)
      })
  }

  private _openQrCodeModal(qrCode: string): void {
    const dialogRef = this._dialog.open(QrCodeModalComponent, {
      width: '32rem',
      disableClose: true,
      data: {
        orgId: this.user.org_id,
        userEmail: this.user.email,
        qrCodeImg: `data:image/png;base64,${qrCode}`,
      },
    })

    dialogRef
      .afterClosed()
      .pipe(take(1), takeUntil(this._unsubscribeAll$))
      .subscribe((verified: boolean) => {
        if (verified) {
          this._refreshUser()
          return
        }

        // Not verified (cancelled or "select a different method"): fall back to a safe method,
        // respecting organization-enforced 2FA rather than leaving a half-configured token setup.
        const methods: TwoFactorMethods = { disabled: !this.requiresOrg2fa, email: this.requiresOrg2fa, token: false }
        this._twoFactorService
          .setMethod(this.user.org_id, this.user.email, methods)
          .pipe(takeUntil(this._unsubscribeAll$))
          .subscribe(() => {
            this._refreshUser()
          })
      })
  }

  private _refreshUser(): void {
    this._userService.getCurrentUser().pipe(takeUntil(this._unsubscribeAll$)).subscribe()
  }
}
