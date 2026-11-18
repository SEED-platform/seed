import { DOCUMENT, inject, Injectable } from '@angular/core'
import { NavigationEnd, Router } from '@angular/router'
import { filter, take } from 'rxjs'

@Injectable({ providedIn: 'root' })
export class SplashScreenService {
  private _document = inject(DOCUMENT)
  private _router = inject(Router)

  constructor() {
    // Fade out, then remove the splash screen on the first NavigationEnd event
    this._router.events
      .pipe(
        filter((event) => event instanceof NavigationEnd),
        take(1),
      )
      .subscribe(() => {
        this._document.body.classList.add('seed-splash-screen-hidden')

        setTimeout(() => {
          this._document.querySelector('body > seed-splash-screen')?.remove()
          this._document.body.classList.remove('seed-splash-screen-hidden')
        }, 400)
      })
  }
}
