import type { OnDestroy, OnInit } from '@angular/core'
import { Directive, ElementRef, HostListener, inject, input } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { Subject, takeUntil } from 'rxjs'
import { MediaWatcherService } from '@seed/services'
import { openInNewTab } from '@seed/utils'
import { OverlayImageComponent } from './dialog'
import type { ImageOverlayData } from './image-overlay.types'

@Directive({
  selector: 'img[imageOverlay]',
  host: {
    '[class.cursor-pointer]': 'true',
  },
})
export class ImageOverlayDirective implements OnInit, OnDestroy {
  private _mediaWatcherService = inject(MediaWatcherService)
  private _matDialog = inject(MatDialog)
  private _elementRef = inject<ElementRef<HTMLImageElement>>(ElementRef<HTMLImageElement>)

  private _isScreenSmall = true
  private readonly _unsubscribeAll$ = new Subject<void>()

  // TODO test this, with and without `alt` on the element
  // Optional: To allow passing a custom "src" via `[imageOverlay]="..."`
  imageOverlay = input<string>()

  private get _url(): string {
    return this.imageOverlay() || this._elementRef.nativeElement.src
  }

  @HostListener('click') onClick() {
    if (this._isScreenSmall) {
      openInNewTab(this._url)
    } else {
      this.showOverlay()
    }
  }

  ngOnInit(): void {
    this._mediaWatcherService.onMediaChange$.pipe(takeUntil(this._unsubscribeAll$)).subscribe(({ matchingAliases }) => {
      this._isScreenSmall = !matchingAliases.includes('md')
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  // TODO make private
  showOverlay(): void {
    this._matDialog.open(OverlayImageComponent, {
      autoFocus: false,
      data: {
        imageSrc: this._url,
        altText: this._elementRef.nativeElement.alt || 'Image preview',
      } satisfies ImageOverlayData,
    })
  }
}
