import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core'
import { TranslocoDirective } from '@jsverse/transloco'
import { MaterialImports } from '@seed/materials'
import type { FilterSortChip } from 'app/modules/inventory/inventory.types'

/*
 * Renders one green badge per active column filter, each with an X button that emits `removed`.
 * The host uses `display: contents` so the badges flow inside the parent's flex/gap layout.
 */
@Component({
  selector: 'seed-filter-chips',
  templateUrl: './filter-chips.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  host: { class: 'contents' },
  imports: [MaterialImports, TranslocoDirective],
})
export class FilterChipsComponent {
  @Input() chips: FilterSortChip[] = []
  @Output() removed = new EventEmitter<FilterSortChip>()
}
