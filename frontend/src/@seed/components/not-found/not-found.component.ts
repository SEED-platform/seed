import { ChangeDetectionStrategy, Component, Input } from '@angular/core'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-not-found',
  templateUrl: './not-found.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports],
})
export class NotFoundComponent {
  @Input() message: string
  @Input() icon: string
}
