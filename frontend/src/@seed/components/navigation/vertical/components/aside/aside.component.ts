import { CommonModule } from '@angular/common'
import type { OnChanges, OnDestroy, OnInit, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, inject, input, untracked } from '@angular/core'
import { isActive, NavigationEnd, Router } from '@angular/router'
import { filter, Subject, takeUntil } from 'rxjs'
import type { NavigationItem, VerticalNavigationComponent } from '@seed/components'
import {
  SeedNavigationService,
  VerticalNavigationBasicItemComponent,
  VerticalNavigationCollapsibleItemComponent,
  VerticalNavigationDividerItemComponent,
  VerticalNavigationGroupItemComponent,
  VerticalNavigationSpacerItemComponent,
} from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { exactMatchOptions, subsetMatchOptions } from '@seed/utils'

@Component({
  selector: 'seed-vertical-navigation-aside-item',
  templateUrl: './aside.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    MaterialImports,
    VerticalNavigationBasicItemComponent,
    VerticalNavigationCollapsibleItemComponent,
    VerticalNavigationDividerItemComponent,
    VerticalNavigationGroupItemComponent,
    VerticalNavigationSpacerItemComponent,
  ],
})
export class VerticalNavigationAsideItemComponent implements OnChanges, OnInit, OnDestroy {
  private _changeDetectorRef = inject(ChangeDetectorRef)
  private _router = inject(Router)
  private _navigationService = inject(SeedNavigationService)

  activeItemId = input<string>()
  autoCollapse = input<boolean>()
  item = input<NavigationItem>()
  name = input<string>()
  skipChildren = input<boolean>()

  active = false
  private _verticalNavigationComponent: VerticalNavigationComponent
  private readonly _unsubscribeAll$ = new Subject<void>()

  ngOnChanges(changes: SimpleChanges): void {
    // Active item id
    if ('activeItemId' in changes) {
      // Mark if active
      this._markIfActive(this._router.url)
    }
  }

  ngOnInit(): void {
    // Mark if active
    this._markIfActive(this._router.url)

    // Attach a listener to the NavigationEnd event
    this._router.events
      .pipe(
        filter((event): event is NavigationEnd => event instanceof NavigationEnd),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe((event: NavigationEnd) => {
        // Mark if active
        this._markIfActive(event.urlAfterRedirects)
      })

    // Get the parent navigation component
    this._verticalNavigationComponent = this._navigationService.getComponent(this.name())

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

  /**
   * Check if the given item has the given url
   * in one of its children
   *
   * @param item
   * @param currentUrl
   * @private
   */
  private _hasActiveChild(item: NavigationItem, currentUrl: string): boolean {
    const children = item.children

    if (!children) {
      return false
    }

    for (const child of children) {
      if (child.children) {
        if (this._hasActiveChild(child, currentUrl)) {
          return true
        }
      }

      // Skip items other than 'basic'
      if (child.type !== 'basic') {
        continue
      }

      // Check if the child has a link and is active
      if (child.link && untracked(isActive(child.link, this._router, child.exactMatch ? exactMatchOptions : subsetMatchOptions))) {
        return true
      }
    }

    return false
  }

  /**
   * Decide and mark if the item is active
   *
   * @private
   */
  private _markIfActive(currentUrl: string): void {
    // Check if the activeItemId is equals to this item id
    this.active = this.activeItemId() === this.item().id

    // If the aside has a children that is active,
    // always mark it as active
    if (this._hasActiveChild(this.item(), currentUrl)) {
      this.active = true
    }

    // Mark for check
    this._changeDetectorRef.markForCheck()
  }
}
