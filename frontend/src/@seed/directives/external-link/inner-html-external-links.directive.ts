import type { AfterViewInit } from '@angular/core'
import { Directive, ElementRef, inject, Renderer2 } from '@angular/core'
import { ExternalLinkDirective } from './external-link.directive'

// This class currently assumes that `innerHTML` doesn't change
@Directive({
  selector: '[innerHTMLExternalLinks]',
})
export class InnerHTMLExternalLinksDirective implements AfterViewInit {
  private _elementRef = inject<ElementRef<HTMLElement>>(ElementRef)
  private _renderer = inject(Renderer2)

  ngAfterViewInit(): void {
    const anchors = this._elementRef.nativeElement.querySelectorAll('a')
    for (const anchor of anchors) {
      const href = anchor.getAttribute('href')
      if (ExternalLinkDirective.isLinkExternal(href)) {
        this._renderer.setAttribute(anchor, 'rel', 'noopener noreferrer')
        this._renderer.setAttribute(anchor, 'target', '_blank')
      }
    }
  }
}
