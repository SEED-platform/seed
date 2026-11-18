import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { InventoryComponent } from '../../../list/inventory.component'

@Component({
  selector: 'seed-group-properties',
  template: '<seed-inventory [groupId]="groupId"></seed-inventory>',
  imports: [InventoryComponent],
  changeDetection: ChangeDetectionStrategy.Eager,
  host: { class: 'flex flex-col flex-auto min-h-0' },
})
export class GroupPropertiesComponent {
  groupId = Number.parseInt(inject(ActivatedRoute).parent.snapshot.paramMap.get('groupId'))
}
