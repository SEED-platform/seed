import { booleanAttribute, ChangeDetectionStrategy, Component, HostBinding, input, ViewEncapsulation } from '@angular/core'
import { Animations } from '@seed/animations'
import type { CardFace } from '@seed/components'

@Component({
  selector: 'seed-card',
  templateUrl: './card.component.html',
  styleUrl: './card.component.scss',
  encapsulation: ViewEncapsulation.None,
  animations: Animations,
  changeDetection: ChangeDetectionStrategy.Eager,
  exportAs: 'card',
})
export class CardComponent {
  expanded = input(false, { transform: booleanAttribute })
  face = input<CardFace>('front')
  flippable = input(false, { transform: booleanAttribute })

  @HostBinding('class') get classList(): Record<string, boolean> {
    return {
      'card-expanded': this.expanded(),
      'card-face-back': this.flippable() && this.face() === 'back',
      'card-face-front': this.flippable() && this.face() === 'front',
      'card-flippable': this.flippable(),
    }
  }
}
