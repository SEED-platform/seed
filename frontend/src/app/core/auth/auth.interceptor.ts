import type { HttpEvent, HttpHandlerFn, HttpRequest } from '@angular/common/http'
import { HttpErrorResponse } from '@angular/common/http'
import { inject } from '@angular/core'
import { Router } from '@angular/router'
import type { Observable } from 'rxjs'
import { catchError, switchMap, throwError } from 'rxjs'
import { AuthService } from './auth.service'

const currentPath = (router: Router) => {
  const urlTree = router.parseUrl(router.url)
  const primarySegments = urlTree.root.children.primary?.segments ?? []
  return primarySegments.map((segment) => segment.toString()).join('/')
}

export const authInterceptor = (req: HttpRequest<unknown>, next: HttpHandlerFn): Observable<HttpEvent<unknown>> => {
  const authService = inject(AuthService)
  const router = inject(Router)

  const isApiRequest = /^\/?api\/(?!token\/refresh\/)/.test(req.url)

  // Skip auth for non-api requests and token refresh
  if (!isApiRequest) {
    return next(req)
  }

  // First refresh the token if necessary
  return authService.isAuthenticated().pipe(
    switchMap((isAuthenticated) => {
      if (isAuthenticated) {
        const newReq = req.clone({
          headers: req.headers.set('Authorization', `Bearer ${authService.accessToken}`),
        })

        return next(newReq).pipe(
          catchError((error: HttpErrorResponse) => {
            return throwError(() => error)
          }),
        )
      } else {
        // Unauthenticated API request
        return next(req).pipe(
          catchError((error) => {
            // Handle "401 Unauthorized" responses (except on sign-in page)
            if (error instanceof HttpErrorResponse && error.status === 401 && currentPath(router) !== 'sign-in') {
              // Sign out
              authService.signOut()

              // Reload the app
              location.reload()
            }

            return throwError(() => new Error(`Failed unauthenticated request ${req.method} ${req.url}`))
          }),
        )
      }
    }),
  )
}
