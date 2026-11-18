import { inject } from '@angular/core'
import type { CanActivateChildFn, CanActivateFn } from '@angular/router'
import { Router } from '@angular/router'
import { map } from 'rxjs'
import { AuthService } from 'app/core/auth/auth.service'

export const AuthGuard: CanActivateFn | CanActivateChildFn = (_route, state) => {
  const authService = inject(AuthService)
  const router = inject(Router)

  // Check the authentication status
  return authService.isAuthenticated().pipe(
    map((authenticated) => {
      // If the user is not authenticated...
      if (!authenticated) {
        // Redirect to the sign-in page with a redirectUrl param
        const redirectURL = state.url === '/sign-out' ? '' : `?redirectURL=${state.url}`
        return router.parseUrl(`sign-in${redirectURL}`)
      }

      // Allow the access
      return true
    }),
  )
}
