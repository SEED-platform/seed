import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import type { FormControl, FormGroup } from '@angular/forms'
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { Router, RouterLink } from '@angular/router'
import { TranslocoDirective } from '@jsverse/transloco'
import { take } from 'rxjs'
import { Animations } from '@seed/animations'
import type { Alert } from '@seed/components'
import { AlertComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { type SEEDConfig, TermsService } from '@seed/services'
import { ConfigService } from '@seed/services/config'
import { AuthService } from 'app/core/auth/auth.service'

@Component({
  selector: 'auth-sign-up',
  templateUrl: './sign-up.component.html',
  encapsulation: ViewEncapsulation.None,
  animations: Animations,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, FormsModule, MaterialImports, ReactiveFormsModule, RouterLink, TranslocoDirective],
})
export class AuthSignUpComponent implements OnInit {
  private _authService = inject(AuthService)
  private _configService = inject(ConfigService)
  private _formBuilder = inject(FormBuilder)
  private _router = inject(Router)
  private _termsOfServiceService = inject(TermsService)

  alert: Alert
  signUpForm: FormGroup<{
    email: FormControl<string>;
    password: FormControl<string>;
    terms: FormControl<boolean>;
  }>
  showAlert = false

  get isTermsInvalid() {
    return this.signUpForm.get('terms')?.invalid && this.signUpForm.get('terms')?.touched
  }

  ngOnInit(): void {
    this._configService.config$.pipe(take(1)).subscribe((config: SEEDConfig) => {
      this.signUpForm = this._formBuilder.group({
        email: ['', [Validators.required, Validators.email]],
        password: ['', [Validators.required, Validators.minLength(8), Validators.pattern(config.passwordPattern)]],
        terms: [false, Validators.requiredTrue],
      })
    })
  }

  showTermsOfService(): void {
    this._termsOfServiceService.showTermsOfService()
  }

  signUp(): void {
    this.signUpForm.markAllAsTouched()

    // Do nothing if the form is invalid
    if (this.signUpForm.invalid) {
      return
    }

    // Disable the form
    this.signUpForm.disable()

    // Hide the alert
    this.showAlert = false

    // Sign up
    this._authService.signUp(this.signUpForm.value).subscribe({
      next: () => {
        // Navigate to the confirmation required page
        void this._router.navigateByUrl('/confirmation-required')
      },
      error: (/* response */) => {
        // Re-enable the form
        this.signUpForm.enable()

        this.signUpForm.reset()

        // Set the alert
        this.alert = {
          type: 'error',
          message: 'Something went wrong, please try again.',
        }

        this.showAlert = true
      },
    })
  }
}
