import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core'
import type { Cycle } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import type { Profile } from '../../../inventory/inventory.types'

@Component({
  selector: 'seed-inventory-grid-config-selector',
  templateUrl: './config-selector.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports],
})
export class ConfigSelectorComponent {
  @Input() label = ''
  @Input() items: (Cycle | Profile)[]
  @Input() selectedId: number
  @Output() selectionChange = new EventEmitter<number>()

  onSelectionChange(value: number) {
    this.selectionChange.emit(value)
  }
}
