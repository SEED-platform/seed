import type { BooleanInput } from '@angular/cdk/coercion'
import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, forwardRef, HostBinding, inject, input, untracked } from '@angular/core'
import { isActive, NavigationEnd, Router } from '@angular/router'
import { filter, Subject, takeUntil } from 'rxjs'
import { Animations } from '@seed/animations'
import type { NavigationItem, VerticalNavigationComponent } from '@seed/components'
import {
  SeedNavigationService,
  VerticalNavigationBasicItemComponent,
  VerticalNavigationDividerItemComponent,
  VerticalNavigationGroupItemComponent,
  VerticalNavigationSpacerItemComponent,
} from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { exactMatchOptions, subsetMatchOptions } from '@seed/utils'

@Component({
  selector: 'seed-vertical-navigation-collapsible-item',
  templateUrl: './collapsible.component.html',
  animations: Animations,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    MaterialImports,
    VerticalNavigationBasicItemComponent,
    forwardRef(() => VerticalNavigationCollapsibleItemComponent),
    VerticalNavigationDividerItemComponent,
    VerticalNavigationGroupItemComponent,
    VerticalNavigationSpacerItemComponent,
  ],
})
export class VerticalNavigationCollapsibleItemComponent implements OnInit, OnDestroy {
  static ngAcceptInputType_autoCollapse: BooleanInput

  private _changeDetectorRef = inject(ChangeDetectorRef)
  private _router = inject(Router)
  private _navigationService = inject(SeedNavigationService)

  autoCollapse = input<boolean>()
  item = input<NavigationItem>()
  name = input<string>()

  isCollapsed = true
  isExpanded = false
  private _verticalNavigationComponent: VerticalNavigationComponent
  private readonly _unsubscribeAll$ = new Subject<void>()

  /**
   * Host binding for component classes
   */
  @HostBinding('class') get classList(): Record<string, boolean> {
    return {
      'seed-vertical-navigation-item-collapsed': this.isCollapsed,
      'seed-vertical-navigation-item-expanded': this.isExpanded,
    }
  }

  ngOnInit(): void {
    // Get the parent navigation component
    this._verticalNavigationComponent = this._navigationService.getComponent(this.name())

    // If the item has a children that has a matching url with the current url, expand...
    if (this._hasActiveChild(this.item(), this._router.url)) {
      this.expand()
    } else {
      // If the autoCollapse is on, collapse...
      if (this.autoCollapse) {
        this.collapse()
      }
    }

    // Listen for the onCollapsibleItemCollapsed from the service
    this._verticalNavigationComponent.onCollapsibleItemCollapsed.pipe(takeUntil(this._unsubscribeAll$)).subscribe((collapsedItem) => {
      // Check if the collapsed item is null
      if (collapsedItem === null) {
        return
      }

      // Collapse if this is a children of the collapsed item
      if (this._isChildrenOf(collapsedItem, this.item())) {
        this.collapse()
      }
    })

    // Listen for the onCollapsibleItemExpanded from the service if the autoCollapse is on
    if (this.autoCollapse) {
      this._verticalNavigationComponent.onCollapsibleItemExpanded.pipe(takeUntil(this._unsubscribeAll$)).subscribe((expandedItem) => {
        // Check if the expanded item is null
        if (expandedItem === null) {
          return
        }

        // Check if this is a parent of the expanded item
        if (this._isChildrenOf(this.item(), expandedItem)) {
          return
        }

        // Check if this has a children with a matching url with the current active url
        if (this._hasActiveChild(this.item(), this._router.url)) {
          return
        }

        // Check if this is the expanded item
        if (this.item() === expandedItem) {
          return
        }

        // If none of the above conditions are matched, collapse this item
        this.collapse()
      })
    }

    // Attach a listener to the NavigationEnd event
    this._router.events
      .pipe(
        filter((event): event is NavigationEnd => event instanceof NavigationEnd),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe((event: NavigationEnd) => {
        // If the item has a children that has a matching url with the current url, expand...
        if (this._hasActiveChild(this.item(), event.urlAfterRedirects)) {
          this.expand()
        } else {
          // If the autoCollapse is on, collapse...
          if (this.autoCollapse) {
            this.collapse()
          }
        }
      })

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
   * Collapse
   */
  collapse(): void {
    // Return if the item is disabled
    if (this.item().disabled) {
      return
    }

    // Return if the item is already collapsed
    if (this.isCollapsed) {
      return
    }

    // Collapse it
    this.isCollapsed = true
    this.isExpanded = !this.isCollapsed

    // Mark for check
    this._changeDetectorRef.markForCheck()

    // Execute the observable
    this._verticalNavigationComponent.onCollapsibleItemCollapsed.next(this.item())
  }

  /**
   * Expand
   */
  expand(): void {
    // Return if the item is disabled
    if (this.item().disabled) {
      return
    }

    // Return if the item is already expanded
    if (!this.isCollapsed) {
      return
    }

    // Expand it
    this.isCollapsed = false
    this.isExpanded = !this.isCollapsed

    // Mark for check
    this._changeDetectorRef.markForCheck()

    // Execute the observable
    this._verticalNavigationComponent.onCollapsibleItemExpanded.next(this.item())
  }

  /**
   * Toggle collapsible
   */
  toggleCollapsible(): void {
    // Toggle collapse/expand
    if (this.isCollapsed) {
      this.expand()
    } else {
      this.collapse()
    }
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

      // Check if the child has a link and is active
      if (child.link && untracked(isActive(child.link, this._router, child.exactMatch ? exactMatchOptions : subsetMatchOptions))) {
        return true
      }
    }

    return false
  }

  /**
   * Check if this is a children
   * of the given item
   *
   * @param parent
   * @param item
   * @private
   */
  private _isChildrenOf(parent: NavigationItem, item: NavigationItem): boolean {
    const children = parent.children

    if (!children) {
      return false
    }

    if (children.includes(item)) {
      return true
    }

    for (const child of children) {
      if (child.children) {
        if (this._isChildrenOf(child, item)) {
          return true
        }
      }
    }

    return false
  }
}
