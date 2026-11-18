import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, inject, input } from '@angular/core'
import type { IsActiveMatchOptions } from '@angular/router'
import { RouterLink, RouterLinkActive } from '@angular/router'
import { Subject, takeUntil } from 'rxjs'
import type { HorizontalNavigationComponent } from '@seed/components/navigation/horizontal/horizontal.component'
import { SeedNavigationService } from '@seed/components/navigation/navigation.service'
import type { NavigationItem } from '@seed/components/navigation/navigation.types'
import { MaterialImports } from '@seed/materials'
import { exactMatchOptions, subsetMatchOptions } from '@seed/utils'

@Component({
  selector: 'seed-horizontal-navigation-basic-item',
  templateUrl: './basic.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, MaterialImports, RouterLink, RouterLinkActive],
})
export class HorizontalNavigationBasicItemComponent implements OnInit, OnDestroy {
  private _changeDetectorRef = inject(ChangeDetectorRef)
  private _navigationService = inject(SeedNavigationService)

  item = input<NavigationItem>()
  name = input<string>()

  // Set the equivalent of {exact: false} as default for active match options.
  // We are not assigning the item.isActiveMatchOptions directly to the
  // [routerLinkActiveOptions] because if it's "undefined" initially, the router
  // will throw an error and stop working.
  isActiveMatchOptions: IsActiveMatchOptions = subsetMatchOptions

  private _horizontalNavigationComponent: HorizontalNavigationComponent
  private readonly _unsubscribeAll$ = new Subject<void>()

  ngOnInit(): void {
    // Set the "isActiveMatchOptions" either from item's
    // "isActiveMatchOptions" or the equivalent form of
    // item's "exactMatch" option
    this.isActiveMatchOptions = this.item().isActiveMatchOptions ?? (this.item().exactMatch ? exactMatchOptions : subsetMatchOptions)

    // Get the parent navigation component
    this._horizontalNavigationComponent = this._navigationService.getComponent(this.name())

    // Mark for check
    this._changeDetectorRef.markForCheck()

    // Subscribe to onRefreshed on the navigation component
    this._horizontalNavigationComponent.onRefreshed.pipe(takeUntil(this._unsubscribeAll$)).subscribe(() => {
      // Mark for check
      this._changeDetectorRef.markForCheck()
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
