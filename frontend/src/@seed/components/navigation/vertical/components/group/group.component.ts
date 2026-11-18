import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, forwardRef, inject, input } from '@angular/core'
import { Subject, takeUntil } from 'rxjs'
import type { NavigationItem, VerticalNavigationComponent } from '@seed/components'
import {
  SeedNavigationService,
  VerticalNavigationBasicItemComponent,
  VerticalNavigationCollapsibleItemComponent,
  VerticalNavigationDividerItemComponent,
  VerticalNavigationSpacerItemComponent,
} from '@seed/components'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-vertical-navigation-group-item',
  templateUrl: './group.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    MaterialImports,
    VerticalNavigationBasicItemComponent,
    VerticalNavigationCollapsibleItemComponent,
    VerticalNavigationDividerItemComponent,
    forwardRef(() => VerticalNavigationGroupItemComponent),
    VerticalNavigationSpacerItemComponent,
  ],
})
export class VerticalNavigationGroupItemComponent implements OnInit, OnDestroy {
  private _changeDetectorRef = inject(ChangeDetectorRef)
  private _navigationService = inject(SeedNavigationService)

  autoCollapse = input<boolean>()
  item = input<NavigationItem>()
  name = input<string>()

  private _verticalNavigationComponent: VerticalNavigationComponent
  private readonly _unsubscribeAll$ = new Subject<void>()

  ngOnInit(): void {
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
}
