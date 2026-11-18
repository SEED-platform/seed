import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core'
import type { FormGroup } from '@angular/forms'
import { FormBuilder, FormControl, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { Subject, take, takeUntil } from 'rxjs'
import type { CurrentUser } from '@seed/api'
import { UserService } from '@seed/api'
import type { Alert } from '@seed/components'
import { AlertComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import type { SEEDConfig } from '@seed/services'
import { ConfigService } from '@seed/services'
import { SEEDValidators } from '@seed/validators'

@Component({
  selector: 'seed-profile-security',
  templateUrl: './security.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, FormsModule, MaterialImports, ReactiveFormsModule, SharedImports],
})
export class ProfileSecurityComponent implements OnInit, OnDestroy {
  private _configService = inject(ConfigService)
  private _formBuilder = inject(FormBuilder)
  private _userService = inject(UserService)

  alert: Alert
  showAlert = false
  user: CurrentUser

  passwordForm: FormGroup<{
    currentPassword: FormControl<string>;
    newPassword: FormControl<string>;
    confirmNewPassword: FormControl<string>;
  }>

  hide = signal(true)

  private readonly _unsubscribeAll$ = new Subject<void>()

  ngOnInit(): void {
    // Subscribe to user changes
    this._userService.currentUser$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((currentUser) => {
      this.user = currentUser
    })

    this._configService.config$.pipe(take(1)).subscribe((config: SEEDConfig) => {
      this.passwordForm = this._formBuilder.group(
        {
          currentPassword: new FormControl('', Validators.required),
          newPassword: new FormControl('', [Validators.required, Validators.minLength(8), Validators.pattern(config.passwordPattern)]),
          confirmNewPassword: new FormControl('', Validators.required),
        },
        {
          validators: SEEDValidators.mustMatch('newPassword', 'confirmNewPassword'),
        },
      )
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  onSubmit() {
    // Handle form submission
    if (this.passwordForm.valid) {
      const passwordData = {
        current_password: this.passwordForm.value.currentPassword,
        password_1: this.passwordForm.value.newPassword,
        password_2: this.passwordForm.value.confirmNewPassword,
      }

      this._userService.updatePassword(passwordData).subscribe({
        error: (error: { error?: { message?: string } }) => {
          const error_msg = error.error?.message || 'An unknown error occurred.'
          this.alert = {
            type: 'error',
            message: `Error Updating Password: ${error_msg}`,
          }
          this.showAlert = true
        },
        complete: () => {
          this.alert = {
            type: 'success',
            message: 'Changes saved!',
          }
          this.showAlert = true
        },
      })
    }
  }

  clickEvent(event: MouseEvent) {
    this.hide.set(!this.hide())
    event.stopPropagation()
  }
}
