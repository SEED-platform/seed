import { inject } from '@angular/core'
import type { CanActivateChildFn, CanActivateFn } from '@angular/router'
import { Router } from '@angular/router'
import { map } from 'rxjs'
import { AuthService } from 'app/core/auth/auth.service'

export const NoAuthGuard: CanActivateFn | CanActivateChildFn = () => {
  const authService = inject(AuthService)
  const router = inject(Router)

  // Check the authentication status
  return authService.isAuthenticated().pipe(
    map((authenticated) => {
      // If the user is authenticated...
      if (authenticated) {
        return router.parseUrl('')
      }

      // Allow the access
      return true
    }),
  )
}
