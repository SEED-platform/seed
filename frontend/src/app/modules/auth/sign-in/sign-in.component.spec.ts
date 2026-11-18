import type { ComponentFixture } from '@angular/core/testing'
import { TestBed } from '@angular/core/testing'
import { ActivatedRoute, Router } from '@angular/router'
import { of } from 'rxjs'
import { ConfigService } from '@seed/api'
import { TermsService } from '@seed/services'
import { AuthService } from 'app/core/auth/auth.service'
import { AuthSignInComponent } from './sign-in.component'

describe('AuthSignInComponent', () => {
  let fixture: ComponentFixture<AuthSignInComponent>
  let component: AuthSignInComponent
  let hasAcceptedTerms: jasmine.Spy
  let recordTermsAcceptance: jasmine.Spy
  let signIn: jasmine.Spy
  let navigateByUrl: jasmine.Spy

  beforeEach(async () => {
    hasAcceptedTerms = jasmine.createSpy('hasAcceptedTerms').and.returnValue(false)
    recordTermsAcceptance = jasmine.createSpy('recordTermsAcceptance')
    signIn = jasmine.createSpy('signIn').and.returnValue(of({ access: 'access', refresh: 'refresh' }))
    navigateByUrl = jasmine.createSpy('navigateByUrl').and.returnValue(Promise.resolve(true))

    await TestBed.configureTestingModule({
      imports: [AuthSignInComponent],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: { get: () => null } } } },
        { provide: Router, useValue: { navigateByUrl } },
        { provide: ConfigService, useValue: { config$: of({ allow_signup: false }) } },
        { provide: AuthService, useValue: { signIn } },
        {
          provide: TermsService,
          useValue: { hasAcceptedTerms, recordTermsAcceptance, showTermsOfService: jasmine.createSpy('showTermsOfService') },
        },
      ],
    })
      .overrideComponent(AuthSignInComponent, { set: { template: '' } })
      .compileComponents()
  })

  afterEach(() => {
    fixture?.destroy()
  })

  function createComponent(): void {
    fixture = TestBed.createComponent(AuthSignInComponent)
    component = fixture.componentInstance
    fixture.detectChanges()
  }

  it('requires terms acceptance when the cached acceptance has expired', () => {
    createComponent()
    component.signInForm.patchValue({ email: 'user@example.com', password: 'password' })

    expect(component.termsPreviouslyAccepted).toBeFalse()
    expect(component.signInForm.invalid).toBeTrue()

    component.signInForm.controls.terms.setValue(true)
    expect(component.signInForm.valid).toBeTrue()
  })

  it('uses a current cached acceptance without recording a new timestamp', () => {
    hasAcceptedTerms.and.returnValue(true)
    createComponent()
    component.signInForm.setValue({ email: 'user@example.com', password: 'password', terms: true })

    component.signIn()

    expect(recordTermsAcceptance).not.toHaveBeenCalled()
    expect(navigateByUrl).toHaveBeenCalledOnceWith('/signed-in-redirect')
  })

  it('records a new acceptance after sign-in succeeds', () => {
    createComponent()
    component.signInForm.setValue({ email: 'user@example.com', password: 'password', terms: true })

    component.signIn()

    expect(recordTermsAcceptance).toHaveBeenCalledTimes(1)
    expect(component.termsPreviouslyAccepted).toBeTrue()
    expect(navigateByUrl).toHaveBeenCalledOnceWith('/signed-in-redirect')
  })

  it('waits for successful two-factor verification before recording acceptance', () => {
    signIn.and.returnValues(of({ two_factor_required: true, two_factor_method: 'email' }), of({ access: 'access', refresh: 'refresh' }))
    createComponent()
    component.signInForm.setValue({ email: 'user@example.com', password: 'password', terms: true })

    component.signIn()
    expect(recordTermsAcceptance).not.toHaveBeenCalled()

    component.otpForm.controls.otp_token.setValue('123456')
    component.submitOtp()

    expect(recordTermsAcceptance).toHaveBeenCalledTimes(1)
    expect(navigateByUrl).toHaveBeenCalledOnceWith('/signed-in-redirect')
  })
})
