import { Platform } from '@angular/cdk/platform'
import type { OnChanges, OnDestroy, OnInit, SimpleChanges } from '@angular/core'
import { Directive, ElementRef, inject, input, model } from '@angular/core'
import PerfectScrollbar from 'perfect-scrollbar'
import { debounceTime, fromEvent, Subject, takeUntil } from 'rxjs'
import { ScrollbarGeometry, ScrollbarPosition } from './scrollbar.types'

/**
 * Wrapper directive for Perfect Scrollbar: https://github.com/mdbootstrap/perfect-scrollbar
 */
@Directive({
  selector: '[seedScrollbar]',
  exportAs: 'seedScrollbar',
})
export class ScrollbarDirective implements OnChanges, OnInit, OnDestroy {
  private _elementRef = inject<ElementRef<HTMLElement>>(ElementRef)
  private _platform = inject(Platform)

  seedScrollbar = model(true)
  seedScrollbarOptions = input<PerfectScrollbar.Options>()

  private _animation: number
  private _options: PerfectScrollbar.Options
  private _ps: PerfectScrollbar
  private readonly _unsubscribeAll$ = new Subject<void>()

  /**
   * Getter for _elementRef
   */
  get elementRef(): ElementRef {
    return this._elementRef
  }

  /**
   * Getter for _ps
   */
  get ps(): PerfectScrollbar | null {
    return this._ps
  }

  ngOnChanges(changes: SimpleChanges): void {
    // Enabled
    if ('seedScrollbar' in changes) {
      // If enabled, init the directive
      if (this.seedScrollbar()) {
        this._init()
      } else {
        this._destroy()
      }
    }

    // Scrollbar options
    if ('seedScrollbarOptions' in changes) {
      // Merge the options
      this._options = {
        ...this._options,
        ...(changes.seedScrollbarOptions.currentValue as PerfectScrollbar.Options),
      }

      // Return if not initialized
      if (!this._ps) {
        return
      }

      // Destroy and re-init the PerfectScrollbar to update its options
      setTimeout(() => {
        this._destroy()
      })

      setTimeout(() => {
        this._init()
      })
    }
  }

  ngOnInit(): void {
    // Subscribe to window resize event
    fromEvent(window, 'resize')
      .pipe(takeUntil(this._unsubscribeAll$), debounceTime(150))
      .subscribe(() => {
        // Update the PerfectScrollbar
        this.update()
      })
  }

  ngOnDestroy(): void {
    this._destroy()

    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  /**
   * Is enabled
   */
  isEnabled(): boolean {
    return this.seedScrollbar()
  }

  /**
   * Update the scrollbar
   */
  update(): void {
    // Return if not initialized
    if (!this._ps) {
      return
    }

    // Update the PerfectScrollbar
    this._ps.update()
  }

  /**
   * Destroy the scrollbar
   */
  destroy(): void {
    this.ngOnDestroy()
  }

  /**
   * Returns the geometry of the scrollable element
   *
   * @param prefix
   */
  geometry(prefix = 'scroll'): ScrollbarGeometry {
    return new ScrollbarGeometry(
      Number(this._elementRef.nativeElement[`${prefix}Left`]),
      Number(this._elementRef.nativeElement[`${prefix}Top`]),
      Number(this._elementRef.nativeElement[`${prefix}Width`]),
      Number(this._elementRef.nativeElement[`${prefix}Height`]),
    )
  }

  /**
   * Returns the position of the scrollable element
   *
   * @param absolute
   */
  position(absolute = false): ScrollbarPosition {
    if (!absolute && this._ps) {
      return new ScrollbarPosition(this._ps.reach.x || 0, this._ps.reach.y || 0)
    } else {
      return new ScrollbarPosition(this._elementRef.nativeElement.scrollLeft, this._elementRef.nativeElement.scrollTop)
    }
  }

  /**
   * Scroll to
   *
   * @param x
   * @param y
   * @param speed
   */
  scrollTo(x: number, y?: number, speed?: number): void {
    if (y == null && speed == null) {
      this.animateScrolling('scrollTop', x, speed)
    } else {
      if (x != null) {
        this.animateScrolling('scrollLeft', x, speed)
      }

      if (y != null) {
        this.animateScrolling('scrollTop', y, speed)
      }
    }
  }

  /**
   * Scroll to X
   *
   * @param x
   * @param speed
   */
  scrollToX(x: number, speed?: number): void {
    this.animateScrolling('scrollLeft', x, speed)
  }

  /**
   * Scroll to Y
   *
   * @param y
   * @param speed
   */
  scrollToY(y: number, speed?: number): void {
    this.animateScrolling('scrollTop', y, speed)
  }

  /**
   * Scroll to top
   *
   * @param offset
   * @param speed
   */
  scrollToTop(offset = 0, speed?: number): void {
    this.animateScrolling('scrollTop', offset, speed)
  }

  /**
   * Scroll to bottom
   *
   * @param offset
   * @param speed
   */
  scrollToBottom(offset = 0, speed?: number): void {
    const top = this._elementRef.nativeElement.scrollHeight - this._elementRef.nativeElement.clientHeight
    this.animateScrolling('scrollTop', top - offset, speed)
  }

  /**
   * Scroll to left
   *
   * @param offset
   * @param speed
   */
  scrollToLeft(offset = 0, speed?: number): void {
    this.animateScrolling('scrollLeft', offset, speed)
  }

  /**
   * Scroll to right
   *
   * @param offset
   * @param speed
   */
  scrollToRight(offset = 0, speed?: number): void {
    const left = this._elementRef.nativeElement.scrollWidth - this._elementRef.nativeElement.clientWidth
    this.animateScrolling('scrollLeft', left - offset, speed)
  }

  /**
   * Scroll to element
   *
   * @param qs
   * @param offset
   * @param ignoreVisible If true, scrollToElement won't happen if element is already inside the current viewport
   * @param speed
   */
  scrollToElement(qs: string, offset = 0, ignoreVisible = false, speed?: number): void {
    const element = this._elementRef.nativeElement.querySelector(qs)

    if (!element) {
      return
    }

    const elementPos = element.getBoundingClientRect()
    const scrollerPos = this._elementRef.nativeElement.getBoundingClientRect()

    if (this._elementRef.nativeElement.classList.contains('ps--active-x')) {
      if (ignoreVisible && elementPos.right <= scrollerPos.right - Math.abs(offset)) {
        return
      }

      const currentPos = this._elementRef.nativeElement.scrollLeft
      const position = elementPos.left - scrollerPos.left + currentPos

      this.animateScrolling('scrollLeft', position + offset, speed)
    }

    if (this._elementRef.nativeElement.classList.contains('ps--active-y')) {
      if (ignoreVisible && elementPos.bottom <= scrollerPos.bottom - Math.abs(offset)) {
        return
      }

      const currentPos = this._elementRef.nativeElement.scrollTop
      const position = elementPos.top - scrollerPos.top + currentPos

      this.animateScrolling('scrollTop', position + offset, speed)
    }
  }

  /**
   * Animate scrolling
   *
   * @param target
   * @param value
   * @param speed
   */
  animateScrolling(target: 'scrollTop' | 'scrollLeft', value: number, speed?: number): void {
    if (this._animation) {
      window.cancelAnimationFrame(this._animation)
      this._animation = null
    }

    if (!speed || typeof window === 'undefined') {
      this._elementRef.nativeElement[target] = value
    } else if (value !== this._elementRef.nativeElement[target]) {
      let newValue = 0
      let scrollCount = 0

      let oldTimestamp = performance.now()
      let oldValue = this._elementRef.nativeElement[target]

      const cosParameter = (oldValue - value) / 2

      const step = (newTimestamp: number): void => {
        scrollCount += Math.PI / (speed / (newTimestamp - oldTimestamp))
        newValue = Math.round(value + cosParameter + cosParameter * Math.cos(scrollCount))

        // Only continue animation if scroll position has not changed
        if (this._elementRef.nativeElement[target] === oldValue) {
          if (scrollCount >= Math.PI) {
            this.animateScrolling(target, value, 0)
          } else {
            this._elementRef.nativeElement[target] = newValue

            // On a zoomed out page the resulting offset may differ
            oldValue = this._elementRef.nativeElement[target]
            oldTimestamp = newTimestamp

            this._animation = window.requestAnimationFrame(step)
          }
        }
      }

      window.requestAnimationFrame(step)
    }
  }

  private _init(): void {
    // Return if already initialized
    if (this._ps) {
      return
    }

    // Return if on mobile or not on browser
    if (this._platform.ANDROID || this._platform.IOS || !this._platform.isBrowser) {
      this.seedScrollbar.set(false)
      return
    }

    // Initialize the PerfectScrollbar
    this._ps = new PerfectScrollbar(this._elementRef.nativeElement, {
      ...this._options,
    })
  }

  private _destroy(): void {
    // Return if not initialized
    if (!this._ps) {
      return
    }

    // Destroy the PerfectScrollbar
    this._ps.destroy()

    // Clean up
    this._ps = null
  }
}
