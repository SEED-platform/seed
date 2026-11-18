import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-menu-item',
  templateUrl: './menu-item.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports],
})
export class MenuItemComponent {
  @Input() label = ''
  @Input() icon?: string
  @Input() disabled = false
  @Output() action = new EventEmitter<void>()

  onClick() {
    if (!this.disabled) {
      this.action.emit()
    }
  }
}
