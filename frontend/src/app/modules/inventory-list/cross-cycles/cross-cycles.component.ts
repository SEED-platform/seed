import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { TranslocoDirective } from '@jsverse/transloco'
import { PageComponent } from '@seed/components'
import { CrossCyclesGridComponent } from '@seed/components/cross-cycles-grid/cross-cycles-grid.component'
import type { InventoryType } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-inventory-list-cross-cycles',
  templateUrl: './cross-cycles.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CrossCyclesGridComponent, PageComponent, TranslocoDirective],
})
export class CrossCyclesComponent {
  private _route = inject(ActivatedRoute)
  type = this._route.snapshot.paramMap.get('type') as InventoryType
}
