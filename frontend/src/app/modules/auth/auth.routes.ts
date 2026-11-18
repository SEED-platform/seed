import type { Routes } from '@angular/router'
import { AuthSignUpComponent } from 'app/modules/auth/sign-up/sign-up.component'
import { SignUpGuard } from '../../core/auth'
import { AuthConfirmationRequiredComponent } from './confirmation-required/confirmation-required.component'
import { AuthForgotPasswordComponent } from './forgot-password/forgot-password.component'
import { AuthResetPasswordComponent } from './reset-password/reset-password.component'
import { AuthSignInComponent } from './sign-in/sign-in.component'

export default [
  {
    path: 'confirmation-required',
    title: 'Confirmation Required',
    component: AuthConfirmationRequiredComponent,
  },
  {
    path: 'forgot-password',
    title: 'Forgot Password',
    component: AuthForgotPasswordComponent,
  },
  {
    path: 'reset-password',
    title: 'Reset Password',
    component: AuthResetPasswordComponent,
  },
  {
    path: 'sign-in',
    title: 'Sign In',
    component: AuthSignInComponent,
  },
  {
    path: 'sign-up',
    canActivate: [SignUpGuard],
    title: 'Sign Up',
    component: AuthSignUpComponent,
  },
] satisfies Routes
