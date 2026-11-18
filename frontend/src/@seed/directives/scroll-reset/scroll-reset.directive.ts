import type { OnDestroy, OnInit } from '@angular/core'
import { Directive, ElementRef, inject } from '@angular/core'
import { NavigationEnd, Router } from '@angular/router'
import { filter, Subject, takeUntil } from 'rxjs'

@Directive({
  selector: '[scrollReset]',
  exportAs: 'scrollReset',
})
export class ScrollResetDirective implements OnInit, OnDestroy {
  private _elementRef = inject<ElementRef<HTMLElement>>(ElementRef)
  private _router = inject(Router)

  private readonly _unsubscribeAll$ = new Subject<void>()

  ngOnInit(): void {
    // Subscribe to NavigationEnd event
    this._router.events
      .pipe(
        filter((event) => event instanceof NavigationEnd),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe(() => {
        // Reset the element's scroll position to the top
        this._elementRef.nativeElement.scrollTop = 0
      })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
