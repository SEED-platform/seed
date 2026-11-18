import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import {
  booleanAttribute,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  forwardRef,
  inject,
  input,
  viewChild,
} from '@angular/core'
import type { MatMenu } from '@angular/material/menu'
import { Subject, takeUntil } from 'rxjs'
import { HorizontalNavigationBasicItemComponent } from '@seed/components/navigation/horizontal/components/basic/basic.component'
import { HorizontalNavigationDividerItemComponent } from '@seed/components/navigation/horizontal/components/divider/divider.component'
import type { HorizontalNavigationComponent } from '@seed/components/navigation/horizontal/horizontal.component'
import { SeedNavigationService } from '@seed/components/navigation/navigation.service'
import type { NavigationItem } from '@seed/components/navigation/navigation.types'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-horizontal-navigation-branch-item',
  templateUrl: './branch.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    HorizontalNavigationBasicItemComponent,
    forwardRef(() => HorizontalNavigationBranchItemComponent),
    HorizontalNavigationDividerItemComponent,
    MaterialImports,
  ],
})
export class HorizontalNavigationBranchItemComponent implements OnInit, OnDestroy {
  private _changeDetectorRef = inject(ChangeDetectorRef)
  private _navigationService = inject(SeedNavigationService)

  child = input(false, { transform: booleanAttribute })
  item = input<NavigationItem>()
  name = input<string>()
  readonly matMenu = viewChild.required<MatMenu>('matMenu')

  private _horizontalNavigationComponent: HorizontalNavigationComponent
  private readonly _unsubscribeAll$ = new Subject<void>()

  ngOnInit(): void {
    // Get the parent navigation component
    this._horizontalNavigationComponent = this._navigationService.getComponent(this.name())

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

  triggerChangeDetection(): void {
    // Mark for check
    this._changeDetectorRef.markForCheck()
  }
}
