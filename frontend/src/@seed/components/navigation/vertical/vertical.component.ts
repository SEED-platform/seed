import type { AnimationPlayer } from '@angular/animations'
import { animate, AnimationBuilder, style } from '@angular/animations'
import type { ScrollStrategy } from '@angular/cdk/overlay'
import { ScrollStrategyOptions } from '@angular/cdk/overlay'
import type { AfterViewInit, OnChanges, OnDestroy, OnInit, QueryList, SimpleChanges } from '@angular/core'
import {
  booleanAttribute,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  DOCUMENT,
  ElementRef,
  HostBinding,
  HostListener,
  inject,
  input,
  model,
  output,
  Renderer2,
  viewChild,
  ViewChildren,
  ViewEncapsulation,
} from '@angular/core'
import { NavigationEnd, Router } from '@angular/router'
import type { Subscription } from 'rxjs'
import { delay, filter, merge, ReplaySubject, Subject, takeUntil } from 'rxjs'
import { Animations } from '@seed/animations'
import type { NavigationItem, VerticalNavigationAppearance, VerticalNavigationMode, VerticalNavigationPosition } from '@seed/components'
import {
  SeedNavigationService,
  VerticalNavigationAsideItemComponent,
  VerticalNavigationBasicItemComponent,
  VerticalNavigationCollapsibleItemComponent,
  VerticalNavigationDividerItemComponent,
  VerticalNavigationGroupItemComponent,
  VerticalNavigationSpacerItemComponent,
} from '@seed/components'
import { ScrollbarDirective } from '@seed/directives'
import { randomId } from '@seed/utils'

@Component({
  selector: 'seed-vertical-navigation',
  templateUrl: './vertical.component.html',
  styleUrl: './vertical.component.scss',
  animations: Animations,
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
  exportAs: 'verticalNavigation',
  imports: [
    ScrollbarDirective,
    VerticalNavigationAsideItemComponent,
    VerticalNavigationBasicItemComponent,
    VerticalNavigationCollapsibleItemComponent,
    VerticalNavigationDividerItemComponent,
    VerticalNavigationGroupItemComponent,
    VerticalNavigationSpacerItemComponent,
  ],
})
export class VerticalNavigationComponent implements OnChanges, OnInit, AfterViewInit, OnDestroy {
  private _animationBuilder = inject(AnimationBuilder)
  private _changeDetectorRef = inject(ChangeDetectorRef)
  private _document = inject(DOCUMENT)
  private _elementRef = inject<ElementRef<HTMLElement>>(ElementRef)
  private _renderer2 = inject(Renderer2)
  private _router = inject(Router)
  private _scrollStrategyOptions = inject(ScrollStrategyOptions)
  private _navigationService = inject(SeedNavigationService)

  appearance = input<VerticalNavigationAppearance>('default')
  autoCollapse = input(true, { transform: booleanAttribute })
  inner = input(false, { transform: booleanAttribute })
  mode = input<VerticalNavigationMode>('side')
  name = model(randomId())
  navigation = input.required<NavigationItem[]>()
  opened = model(true)
  position = input<VerticalNavigationPosition>('left')
  transparentOverlay = input(false, { transform: booleanAttribute })
  appearanceChanged = output<VerticalNavigationAppearance>()
  modeChanged = output<VerticalNavigationMode>()
  openedChanged = output<boolean>()
  positionChanged = output<VerticalNavigationPosition>()
  private readonly _navigationContentEl = viewChild.required<ElementRef<HTMLElement>>('navigationContent')

  activeAsideItemId: string | null = null
  onCollapsibleItemCollapsed = new ReplaySubject<NavigationItem>(1)
  onCollapsibleItemExpanded = new ReplaySubject<NavigationItem>(1)
  onRefreshed = new ReplaySubject<boolean>(1)
  showScrollbar: boolean

  private _animationsEnabled = false
  private _asideOverlay: HTMLElement
  private _hovered = false
  private _mutationObserver: MutationObserver
  private _overlay: HTMLElement
  private _player: AnimationPlayer
  private _scrollStrategy: ScrollStrategy = this._scrollStrategyOptions.block()
  private _scrollbarDirectives!: QueryList<ScrollbarDirective>
  private _scrollbarDirectivesSubscription: Subscription
  private readonly _unsubscribeAll$ = new Subject<void>()

  @HostBinding('class') get classList(): Record<string, boolean> {
    return {
      'seed-vertical-navigation-animations-enabled': this._animationsEnabled,
      [`seed-vertical-navigation-appearance-${this.appearance()}`]: true,
      'seed-vertical-navigation-hover': this._hovered,
      'seed-vertical-navigation-inner': this.inner(),
      'seed-vertical-navigation-mode-over': this.mode() === 'over',
      'seed-vertical-navigation-mode-side': this.mode() === 'side',
      'seed-vertical-navigation-opened': this.opened(),
      'seed-vertical-navigation-position-left': this.position() === 'left',
      'seed-vertical-navigation-position-right': this.position() === 'right',
    }
  }

  @HostBinding('style') get styleList(): Record<string, string> {
    return {
      visibility: this.opened() ? 'visible' : 'hidden',
    }
  }

  /**
   * Setter for seedScrollbarDirectives
   */
  @ViewChildren(ScrollbarDirective) set seedScrollbarDirectives(seedScrollbarDirectives: QueryList<ScrollbarDirective>) {
    // Store the directives
    this._scrollbarDirectives = seedScrollbarDirectives

    // Return if there are no directives
    if (seedScrollbarDirectives.length === 0) {
      return
    }

    if (this._scrollbarDirectivesSubscription) {
      this._scrollbarDirectivesSubscription.unsubscribe()
    }

    // Update the scrollbars on collapsible items' collapse/expand
    this._scrollbarDirectivesSubscription = merge(this.onCollapsibleItemCollapsed, this.onCollapsibleItemExpanded)
      .pipe(takeUntil(this._unsubscribeAll$), delay(250))
      .subscribe(() => {
        for (const seedScrollbarDirective of seedScrollbarDirectives) {
          seedScrollbarDirective.update()
        }
      })
  }

  @HostListener('mouseenter') handleMouseEnter(): void {
    this._enableAnimations()
    this._hovered = true
  }

  @HostListener('mouseleave') handleMouseLeave(): void {
    this._enableAnimations()
    this._hovered = false
  }

  @HostListener('window:resize') handleResize(): void {
    this.checkScrollNeeded()
  }

  checkScrollNeeded() {
    const el = document.querySelector('#navigationContent')
    if (!el) return

    this.showScrollbar = el.scrollHeight > el.clientHeight
  }

  ngOnInit(): void {
    // Make sure the name input is not an empty string
    if (this.name() === '') {
      this.name.set(randomId())
    }

    // Register the navigation component
    this._navigationService.registerComponent(this.name(), this)

    // Subscribe to the 'NavigationEnd' event
    this._router.events
      .pipe(
        filter((event) => event instanceof NavigationEnd),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe(() => {
        // If the mode is 'over' and the navigation is opened...
        if (this.mode() === 'over' && this.opened()) {
          // Close the navigation
          this.close()
        }

        // If the mode is 'side' and the aside is active...
        if (this.mode() === 'side' && this.activeAsideItemId) {
          // Close the aside
          this.closeAside()
        }
      })
  }

  ngAfterViewInit(): void {
    // Fix for Firefox.
    //
    // Because 'position: sticky' doesn't work correctly inside a 'position: fixed' parent,
    // adding the '.cdk-global-scrollblock' to the html element breaks the navigation's position.
    // This fixes the problem by reading the 'top' value from the html element and adding it as a
    // 'marginTop' to the navigation itself.
    this._mutationObserver = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        const mutationTarget = mutation.target as HTMLElement
        if (mutation.attributeName === 'class') {
          if (mutationTarget.classList.contains('cdk-global-scrollblock')) {
            const top = parseInt(mutationTarget.style.top, 10)
            this._renderer2.setStyle(this._elementRef.nativeElement, 'margin-top', `${Math.abs(top)}px`)
          } else {
            this._renderer2.setStyle(this._elementRef.nativeElement, 'margin-top', null)
          }
        }
      }
    })
    this._mutationObserver.observe(this._document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    })

    setTimeout(() => {
      // Return if 'navigation content' element does not exist
      const _navigationContentEl = this._navigationContentEl()
      if (!_navigationContentEl) {
        return
      }

      // If 'navigation content' element doesn't have
      // perfect scrollbar activated on it...
      if (!_navigationContentEl.nativeElement.classList.contains('ps')) {
        // Find the active item
        const activeItem = _navigationContentEl.nativeElement.querySelector('.seed-vertical-navigation-item-active')

        // If the active item exists, scroll it into view
        if (activeItem) {
          activeItem.scrollIntoView()
        }
      } else {
        // Go through all the scrollbar directives
        for (const seedScrollbarDirective of this._scrollbarDirectives) {
          // Skip if not enabled
          if (!seedScrollbarDirective.isEnabled()) {
            return
          }

          // Scroll to the active element
          seedScrollbarDirective.scrollToElement('.seed-vertical-navigation-item-active', -120, true)
        }
      }
    })

    this.checkScrollNeeded()
  }

  ngOnChanges(changes: SimpleChanges): void {
    // Appearance
    if ('appearance' in changes) {
      // Emit the event
      this.appearanceChanged.emit(this.appearance())
    }

    // Mode
    if ('mode' in changes) {
      // Get the previous and current values
      const currentMode = changes.mode.currentValue as VerticalNavigationMode
      const previousMode = changes.mode.previousValue as VerticalNavigationMode

      // Disable the animations
      this._disableAnimations()

      // If the mode changes: 'over -> side'
      if (previousMode === 'over' && currentMode === 'side') {
        // Hide the overlay
        this._hideOverlay()
      }

      // If the mode changes: 'side -> over'
      if (previousMode === 'side' && currentMode === 'over') {
        // Close the aside
        this.closeAside()

        // If the navigation is opened
        if (this.opened()) {
          // Show the overlay
          this._showOverlay()
        }
      }

      // Emit the event
      this.modeChanged.emit(currentMode)

      // Enable the animations after a delay
      // The delay must be bigger than the current transition-duration
      // to make sure nothing will be animated while the mode changing
      setTimeout(() => {
        this._enableAnimations()
      }, 500)
    }

    // Navigation
    if ('navigation' in changes) {
      // Mark for check
      this._changeDetectorRef.markForCheck()
    }

    // Opened
    if ('opened' in changes) {
      // Open/close the navigation
      this._toggleOpened(this.opened())
    }

    // Position
    if ('position' in changes) {
      // Emit the event
      this.positionChanged.emit(this.position())
    }
  }

  ngOnDestroy(): void {
    // Disconnect the mutation observer
    this._mutationObserver.disconnect()

    // Forcefully close the navigation and aside in case they are opened
    this.close()
    this.closeAside()

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

  /**
   * Open the navigation
   */
  open(): void {
    // Return if the navigation is already open
    if (this.opened()) {
      return
    }

    // Set the opened
    this._toggleOpened(true)
  }

  /**
   * Close the navigation
   */
  close(): void {
    // Return if the navigation is already closed
    if (!this.opened()) {
      return
    }

    // Close the aside
    this.closeAside()

    // Set the opened
    this._toggleOpened(false)
  }

  /**
   * Toggle the navigation
   */
  toggle(): void {
    // Toggle
    if (this.opened()) {
      this.close()
    } else {
      this.open()
    }
  }

  /**
   * Open the aside
   *
   * @param item
   */
  openAside(item: NavigationItem): void {
    // Return if the item is disabled
    if (item.disabled || !item.id) {
      return
    }

    // Open
    this.activeAsideItemId = item.id

    // Show the aside overlay
    this._showAsideOverlay()

    // Mark for check
    this._changeDetectorRef.markForCheck()
  }

  /**
   * Close the aside
   */
  closeAside(): void {
    // Close
    this.activeAsideItemId = null

    // Hide the aside overlay
    this._hideAsideOverlay()

    // Mark for check
    this._changeDetectorRef.markForCheck()
  }

  /**
   * Toggle the aside
   *
   * @param item
   */
  toggleAside(item: NavigationItem): void {
    // Toggle
    if (this.activeAsideItemId === item.id) {
      this.closeAside()
    } else {
      this.openAside(item)
    }
  }

  private _handleAsideOverlayClick = () => {
    this.closeAside()
  }

  private _handleOverlayClick = () => {
    this.close()
  }

  private _enableAnimations(): void {
    this._animationsEnabled = true
  }

  private _disableAnimations(): void {
    this._animationsEnabled = false
  }

  private _showOverlay(): void {
    // Return if there is already an overlay
    if (this._asideOverlay) {
      return
    }

    // Create the overlay element
    this._overlay = this._renderer2.createElement('div') as HTMLDivElement

    // Add a class to the overlay element
    this._overlay.classList.add('seed-vertical-navigation-overlay')

    // Add a class depending on the transparentOverlay option
    if (this.transparentOverlay()) {
      this._overlay.classList.add('seed-vertical-navigation-overlay-transparent')
    }

    // Append the overlay to the parent of the navigation
    this._renderer2.appendChild(this._elementRef.nativeElement.parentElement, this._overlay)

    // Enable block scroll strategy
    this._scrollStrategy.enable()

    // Create the enter animation and attach it to the player
    this._player = this._animationBuilder
      .build([animate('300ms cubic-bezier(0.25, 0.8, 0.25, 1)', style({ opacity: 1 }))])
      .create(this._overlay)

    // Play the animation
    this._player.play()

    // Add an event listener to the overlay
    this._overlay.addEventListener('click', this._handleOverlayClick)
  }

  private _hideOverlay(): void {
    if (!this._overlay) {
      return
    }

    // Create the leave animation and attach it to the player
    this._player = this._animationBuilder
      .build([animate('300ms cubic-bezier(0.25, 0.8, 0.25, 1)', style({ opacity: 0 }))])
      .create(this._overlay)

    // Play the animation
    this._player.play()

    // Once the animation is done...
    this._player.onDone(() => {
      // If the overlay still exists...
      if (this._overlay) {
        // Remove the event listener
        this._overlay.removeEventListener('click', this._handleOverlayClick)

        // Remove the overlay
        this._overlay.parentNode.removeChild(this._overlay)
        this._overlay = null
      }

      // Disable block scroll strategy
      this._scrollStrategy.disable()
    })
  }

  /**
   * Show the aside overlay
   *
   * @private
   */
  private _showAsideOverlay(): void {
    // Return if there is already an overlay
    if (this._asideOverlay) {
      return
    }

    // Create the aside overlay element
    this._asideOverlay = this._renderer2.createElement('div') as HTMLDivElement

    // Add a class to the aside overlay element
    this._asideOverlay.classList.add('seed-vertical-navigation-aside-overlay')

    // Append the aside overlay to the parent of the navigation
    this._renderer2.appendChild(this._elementRef.nativeElement.parentElement, this._asideOverlay)

    // Create the enter animation and attach it to the player
    this._player = this._animationBuilder
      .build([animate('300ms cubic-bezier(0.25, 0.8, 0.25, 1)', style({ opacity: 1 }))])
      .create(this._asideOverlay)

    // Play the animation
    this._player.play()

    // Add an event listener to the aside overlay
    this._asideOverlay.addEventListener('click', this._handleAsideOverlayClick)
  }

  /**
   * Hide the aside overlay
   *
   * @private
   */
  private _hideAsideOverlay(): void {
    if (!this._asideOverlay) {
      return
    }

    // Create the leave animation and attach it to the player
    this._player = this._animationBuilder
      .build([animate('300ms cubic-bezier(0.25, 0.8, 0.25, 1)', style({ opacity: 0 }))])
      .create(this._asideOverlay)

    // Play the animation
    this._player.play()

    // Once the animation is done...
    this._player.onDone(() => {
      // If the aside overlay still exists...
      if (this._asideOverlay) {
        // Remove the event listener
        this._asideOverlay.removeEventListener('click', this._handleAsideOverlayClick)

        // Remove the aside overlay
        this._asideOverlay.parentNode.removeChild(this._asideOverlay)
        this._asideOverlay = null
      }
    })
  }

  /**
   * Open/close the navigation
   *
   * @param open
   * @private
   */
  private _toggleOpened(open: boolean): void {
    // Set the opened
    this.opened.set(open)

    // Enable the animations
    this._enableAnimations()

    // If the navigation opened, and the mode
    // is 'over', show the overlay
    if (this.mode() === 'over') {
      if (this.opened()) {
        this._showOverlay()
      } else {
        this._hideOverlay()
      }
    }

    // Emit the event
    this.openedChanged.emit(open)
  }
}
