import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import type { FormControl, FormGroup } from '@angular/forms'
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { RouterLink } from '@angular/router'
import { finalize } from 'rxjs'
import { Animations } from '@seed/animations'
import type { Alert } from '@seed/components'
import { AlertComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { AuthService } from 'app/core/auth/auth.service'

@Component({
  selector: 'auth-forgot-password',
  templateUrl: './forgot-password.component.html',
  encapsulation: ViewEncapsulation.None,
  animations: Animations,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, FormsModule, MaterialImports, ReactiveFormsModule, RouterLink],
})
export class AuthForgotPasswordComponent implements OnInit {
  private _authService = inject(AuthService)
  private _formBuilder = inject(FormBuilder)

  alert: Alert
  forgotPasswordForm: FormGroup<{
    email: FormControl<string>;
  }>

  showAlert = false

  ngOnInit(): void {
    this.forgotPasswordForm = this._formBuilder.group({
      email: ['', [Validators.required, Validators.email]],
    })
  }

  /**
   * Send the reset link
   */
  sendResetLink(): void {
    // Return if the form is invalid
    if (this.forgotPasswordForm.invalid) {
      return
    }

    // Disable the form
    this.forgotPasswordForm.disable()

    // Hide the alert
    this.showAlert = false

    // Forgot password
    this._authService
      .forgotPassword(this.forgotPasswordForm.get('email').value)
      .pipe(
        finalize(() => {
          // Re-enable the form
          this.forgotPasswordForm.enable()

          this.forgotPasswordForm.reset()

          this.showAlert = true
        }),
      )
      .subscribe({
        next: () => {
          // Set the alert
          this.alert = {
            type: 'success',
            message: "Password reset sent! You'll receive an email if you are registered on our system.",
          }
        },
        error: (/* response */) => {
          // Set the alert
          this.alert = {
            type: 'error',
            message: 'Email does not found! Are you sure you are already a member?',
          }
        },
      })
  }
}
