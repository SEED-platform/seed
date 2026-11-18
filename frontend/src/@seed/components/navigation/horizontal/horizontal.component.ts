import type { OnChanges, OnDestroy, OnInit, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, inject, input, model, ViewEncapsulation } from '@angular/core'
import { ReplaySubject, Subject } from 'rxjs'
import { Animations } from '@seed/animations'
import { SeedNavigationService } from '@seed/components/navigation/navigation.service'
import type { NavigationItem } from '@seed/components/navigation/navigation.types'
import { randomId } from '@seed/utils'
import { HorizontalNavigationBasicItemComponent } from './components/basic/basic.component'
import { HorizontalNavigationBranchItemComponent } from './components/branch/branch.component'
import { HorizontalNavigationSpacerItemComponent } from './components/spacer/spacer.component'

@Component({
  selector: 'seed-horizontal-navigation',
  templateUrl: './horizontal.component.html',
  styleUrl: './horizontal.component.scss',
  animations: Animations,
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
  exportAs: 'horizontalNavigation',
  imports: [HorizontalNavigationBasicItemComponent, HorizontalNavigationBranchItemComponent, HorizontalNavigationSpacerItemComponent],
})
export class HorizontalNavigationComponent implements OnChanges, OnInit, OnDestroy {
  private _changeDetectorRef = inject(ChangeDetectorRef)
  private _navigationService = inject(SeedNavigationService)

  name = model(randomId())
  navigation = input<NavigationItem[]>()

  onRefreshed = new ReplaySubject<boolean>(1)
  private readonly _unsubscribeAll$ = new Subject<void>()

  ngOnChanges(changes: SimpleChanges): void {
    // Navigation
    if ('navigation' in changes) {
      // Mark for check
      this._changeDetectorRef.markForCheck()
    }
  }

  ngOnInit(): void {
    // Make sure the name input is not an empty string
    if (this.name() === '') {
      this.name.set(randomId())
    }

    // Register the navigation component
    this._navigationService.registerComponent(this.name(), this)
  }

  ngOnDestroy(): void {
    // Deregister the navigation component from the registry
    this._navigationService.deregisterComponent(this.name())

    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  /**
   * Refresh the component to apply the changes
   */
  refresh(): void {
    // Mark for check
    this._changeDetectorRef.markForCheck()

    // Execute the observable
    this.onRefreshed.next(true)
  }
}
