import { ChangeDetectionStrategy, Component, Input } from '@angular/core'
import { type Label } from '@seed/api'
import { SharedImports } from '@seed/directives'

@Component({
  selector: 'seed-label',
  templateUrl: './label.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [SharedImports],
})
export class LabelComponent {
  @Input() label: Label
}
