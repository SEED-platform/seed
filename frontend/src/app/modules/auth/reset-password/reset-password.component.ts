import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import type { FormControl, FormGroup } from '@angular/forms'
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { RouterLink } from '@angular/router'
import { finalize, take } from 'rxjs'
import { Animations } from '@seed/animations'
import type { Alert } from '@seed/components'
import { AlertComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import type { SEEDConfig } from '@seed/services'
import { ConfigService } from '@seed/services'
import { SEEDValidators } from '@seed/validators'
import { AuthService } from 'app/core/auth/auth.service'

@Component({
  selector: 'auth-reset-password',
  templateUrl: './reset-password.component.html',
  encapsulation: ViewEncapsulation.None,
  animations: Animations,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, FormsModule, MaterialImports, ReactiveFormsModule, RouterLink],
})
export class AuthResetPasswordComponent implements OnInit {
  private _authService = inject(AuthService)
  private _configService = inject(ConfigService)
  private _formBuilder = inject(FormBuilder)

  alert: Alert
  resetPasswordForm: FormGroup<{
    password: FormControl<string>;
    passwordConfirm: FormControl<string>;
  }>
  showAlert = false

  ngOnInit(): void {
    this._configService.config$.pipe(take(1)).subscribe((config: SEEDConfig) => {
      this.resetPasswordForm = this._formBuilder.group(
        {
          password: ['', [Validators.required, Validators.minLength(8), Validators.pattern(config.passwordPattern)]],
          passwordConfirm: ['', Validators.required],
        },
        {
          validators: SEEDValidators.mustMatch('password', 'passwordConfirm'),
        },
      )
    })
  }

  /**
   * Reset password
   */
  resetPassword(): void {
    // Return if the form is invalid
    if (this.resetPasswordForm.invalid) {
      return
    }

    // Disable the form
    this.resetPasswordForm.disable()

    // Hide the alert
    this.showAlert = false

    // Send the request to the server
    this._authService
      .resetPassword(this.resetPasswordForm.get('password').value)
      .pipe(
        finalize(() => {
          // Re-enable the form
          this.resetPasswordForm.enable()

          this.resetPasswordForm.reset()

          this.showAlert = true
        }),
      )
      .subscribe({
        next: () => {
          // Set the alert
          this.alert = {
            type: 'success',
            message: 'Your password has been reset.',
          }
        },
        error: (/* response */) => {
          // Set the alert
          this.alert = {
            type: 'error',
            message: 'Something went wrong, please try again.',
          }
        },
      })
  }
}
