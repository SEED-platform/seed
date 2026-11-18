import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, inject, input } from '@angular/core'
import { NavigationEnd, Router, RouterLink, RouterLinkActive } from '@angular/router'
import { Subject, takeUntil } from 'rxjs'
import type { NavigationItem, VerticalNavigationComponent } from '@seed/components'
import { SeedNavigationService } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { exactMatchOptions, subsetMatchOptions } from '@seed/utils'

@Component({
  selector: 'seed-vertical-navigation-basic-item',
  templateUrl: './basic.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, MaterialImports, RouterLink, RouterLinkActive, SharedImports],
})
export class VerticalNavigationBasicItemComponent implements OnInit, OnDestroy {
  private _changeDetectorRef = inject(ChangeDetectorRef)
  private _navigationService = inject(SeedNavigationService)
  private _router = inject(Router)

  item = input<NavigationItem>()
  name = input<string>()

  // Default to the equivalent of {exact: false} because `isActiveMatchOptions` must be initialized
  isActiveMatchOptions = subsetMatchOptions

  currentUrl = this._router.url
  private _verticalNavigationComponent: VerticalNavigationComponent
  private readonly _unsubscribeAll$ = new Subject<void>()

  ngOnInit(): void {
    this._router.events.pipe(takeUntil(this._unsubscribeAll$)).subscribe((event) => {
      if (event instanceof NavigationEnd) {
        this.currentUrl = event.url
        if (this.item().regexMatch) {
          // Re-check active status
          this._changeDetectorRef.markForCheck()
        }
      }
    })

    // Set the "isActiveMatchOptions" either from item's
    // "isActiveMatchOptions" or the equivalent form of
    // item's "exactMatch" option
    this.isActiveMatchOptions = this.item().isActiveMatchOptions ?? (this.item().exactMatch ? exactMatchOptions : subsetMatchOptions)

    // Get the parent navigation component
    this._verticalNavigationComponent = this._navigationService.getComponent(this.name())

    // Mark for check
    this._changeDetectorRef.markForCheck()

    // Subscribe to onRefreshed on the navigation component
    this._verticalNavigationComponent.onRefreshed.pipe(takeUntil(this._unsubscribeAll$)).subscribe(() => {
      // Mark for check
      this._changeDetectorRef.markForCheck()
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
