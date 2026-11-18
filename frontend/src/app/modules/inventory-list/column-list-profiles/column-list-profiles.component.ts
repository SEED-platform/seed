import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { PageComponent } from '@seed/components'
import { ColumnProfilesComponent } from '@seed/components/column-profiles/column-profiles.component'
import type { InventoryType } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-inventory-list-profiles',
  templateUrl: './column-list-profiles.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [ColumnProfilesComponent, PageComponent],
})
export class ColumnListProfilesComponent {
  @ViewChild('columnProfiles') columnProfiles: ColumnProfilesComponent
  private _route = inject(ActivatedRoute)
  type = this._route.snapshot.paramMap.get('type') as InventoryType

  onSave = () => {
    this.columnProfiles.onSave()
  }
}
