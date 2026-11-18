import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import { FormBuilder, FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { ActivatedRoute, Router, RouterLink } from '@angular/router'
import { TranslocoDirective } from '@jsverse/transloco'
import { Subject, takeUntil } from 'rxjs'
import { Animations } from '@seed/animations'
import { ConfigService } from '@seed/api'
import type { Alert } from '@seed/components'
import { AlertComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { TermsService } from '@seed/services'
import { AuthService } from 'app/core/auth/auth.service'

@Component({
  selector: 'auth-sign-in',
  templateUrl: './sign-in.component.html',
  encapsulation: ViewEncapsulation.None,
  animations: Animations,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, FormsModule, MaterialImports, ReactiveFormsModule, RouterLink, TranslocoDirective],
})
export class AuthSignInComponent implements OnInit, OnDestroy {
  private _route = inject(ActivatedRoute)
  private _authService = inject(AuthService)
  private _configService = inject(ConfigService)
  private _formBuilder = inject(FormBuilder)
  private _router = inject(Router)
  private _termsOfServiceService = inject(TermsService)

  private readonly _unsubscribeAll$ = new Subject<void>()

  alert: Alert
  allowSignUp = false
  showAlert = false
  termsPreviouslyAccepted = false
  twoFactorStep = false
  twoFactorMethod: 'email' | 'token' = 'token'
  signInForm: FormGroup<{
    email: FormControl<string>;
    password: FormControl<string>;
    terms: FormControl<boolean>;
  }>
  otpForm: FormGroup<{ otp_token: FormControl<string> }>
  private _pendingCredentials: { username: string; password: string } | null = null

  ngOnInit(): void {
    this._configService.config$.pipe(takeUntil(this._unsubscribeAll$)).subscribe(({ allow_signup: allowSignUp }) => {
      this.allowSignUp = allowSignUp
    })

    this.signInForm = this._formBuilder.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', Validators.required],
      terms: [false, Validators.requiredTrue],
    })

    this.signInForm.controls.email.valueChanges.pipe(takeUntil(this._unsubscribeAll$)).subscribe((email) => {
      const accepted = !this.signInForm.controls.email.hasError('email') && this._termsOfServiceService.hasAcceptedTerms(email)
      if (accepted !== this.termsPreviouslyAccepted) {
        this.termsPreviouslyAccepted = accepted
        this.signInForm.controls.terms.setValue(accepted)
      }
    })

    this.otpForm = new FormGroup({
      otp_token: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  showTermsOfService(): void {
    this._termsOfServiceService.showTermsOfService()
  }

  get isTermsInvalid() {
    return this.signInForm.get('terms')?.invalid && this.signInForm.get('terms')?.touched
  }

  signIn(): void {
    this.signInForm.markAllAsTouched()

    // Return if the form is invalid
    if (this.signInForm.invalid) {
      return
    }

    // Disable the form
    this.signInForm.disable()

    // Hide the alert
    this.showAlert = false

    // Sign in
    const { email, password } = this.signInForm.value as { email: string; password: string; terms: boolean }
    this._authService.signIn({ username: email.toLowerCase(), password }).subscribe({
      next: (response) => {
        if (response.two_factor_required) {
          this._pendingCredentials = { username: email.toLowerCase(), password }
          this.twoFactorMethod = response.two_factor_method ?? 'token'
          this.twoFactorStep = true
          this.signInForm.enable()
          return
        }

        // Set the redirect url.
        // The '/signed-in-redirect' is a dummy url to catch the request and redirect the user
        // to the correct page after a successful sign in. This way, that url can be set via
        // routing file and we don't have to touch here.

        const redirectURL = this._route.snapshot.queryParamMap.get('redirectURL') || '/signed-in-redirect'

        this._recordTermsAcceptance()

        // Navigate to the redirect url
        void this._router.navigateByUrl(redirectURL)
      },
      error: (/* response */) => {
        // Re-enable the form
        this.signInForm.enable()

        this.signInForm.reset({ email: '', password: '', terms: this.termsPreviouslyAccepted })

        // Set the alert
        this.alert = {
          type: 'error',
          message: 'Incorrect email or password',
        }
        this.showAlert = true
      },
    })
  }

  submitOtp(): void {
    this.otpForm.markAllAsTouched()

    if (this.otpForm.invalid || !this._pendingCredentials) {
      return
    }

    this.otpForm.disable()
    this.showAlert = false

    const { otp_token } = this.otpForm.getRawValue()
    this._authService.signIn({ ...this._pendingCredentials, otp_token }).subscribe({
      next: () => {
        const redirectURL = this._route.snapshot.queryParamMap.get('redirectURL') || '/signed-in-redirect'
        this._recordTermsAcceptance()
        void this._router.navigateByUrl(redirectURL)
      },
      error: () => {
        this.otpForm.enable()
        this.alert = {
          type: 'error',
          message: 'Invalid verification code',
        }
        this.showAlert = true
      },
    })
  }

  resendCode(): void {
    if (!this._pendingCredentials) {
      return
    }
    this._authService.signIn(this._pendingCredentials).subscribe({
      next: () => {
        this.alert = {
          type: 'success',
          message: 'A new code has been sent to your email address.',
        }
        this.showAlert = true
      },
    })
  }

  backToSignIn(): void {
    this.twoFactorStep = false
    this._pendingCredentials = null
    this.otpForm.reset()
    this.showAlert = false
  }

  private _recordTermsAcceptance(): void {
    if (this.termsPreviouslyAccepted) return

    this._termsOfServiceService.recordTermsAcceptance(this.signInForm.value.email)
    this.termsPreviouslyAccepted = true
  }
}
