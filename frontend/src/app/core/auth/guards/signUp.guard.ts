import { inject } from '@angular/core'
import type { CanActivateFn } from '@angular/router'
import { Router } from '@angular/router'
import { map } from 'rxjs'
import { ConfigService } from '@seed/api'

export const SignUpGuard: CanActivateFn = () => {
  const configService = inject(ConfigService)
  const router = inject(Router)

  // Check the allowSignUp status
  return configService.config$.pipe(
    map(({ allow_signup: allowSignUp }) => {
      if (!allowSignUp) {
        // Redirect to the sign-in page
        return router.parseUrl('sign-in')
      }

      // Allow the access
      return true
    }),
  )
}
