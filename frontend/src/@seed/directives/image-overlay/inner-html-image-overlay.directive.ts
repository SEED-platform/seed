import type { AfterViewInit, OnDestroy, OnInit } from '@angular/core'
import { Directive, ElementRef, inject } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { Subject, takeUntil } from 'rxjs'
import { openInNewTab } from '@seed/utils'
import { MediaWatcherService } from '../../services'
import { OverlayImageComponent } from './dialog'
import type { ImageOverlayData } from './image-overlay.types'

// This class currently assumes that `innerHTML` doesn't change
@Directive({
  selector: '[innerHTMLImageOverlay]',
})
export class InnerHTMLImageOverlayDirective implements OnInit, OnDestroy, AfterViewInit {
  private _matDialog = inject(MatDialog)
  private _mediaWatcherService = inject(MediaWatcherService)
  private _elementRef = inject<ElementRef<HTMLElement>>(ElementRef)

  private _isScreenSmall = true
  private readonly _unsubscribeAll$ = new Subject<void>()

  ngOnInit(): void {
    this._mediaWatcherService.onMediaChange$.pipe(takeUntil(this._unsubscribeAll$)).subscribe(({ matchingAliases }) => {
      this._isScreenSmall = !matchingAliases.includes('md')
    })
  }

  ngAfterViewInit(): void {
    const nativeElement: HTMLElement = this._elementRef.nativeElement
    const images = nativeElement.querySelectorAll('img')
    for (const image of images) {
      image.classList.add('cursor-pointer')
      const imageSrc = image.getAttribute('src')
      image.onclick = () => {
        if (this._isScreenSmall) {
          openInNewTab(imageSrc)
        } else {
          this.showOverlay(imageSrc)
        }
      }
    }
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  // TODO add alt text
  showOverlay(imageSrc: string): void {
    this._matDialog.open(OverlayImageComponent, {
      autoFocus: false,
      data: {
        imageSrc,
        altText: 'Image preview',
      } satisfies ImageOverlayData,
    })
  }
}
