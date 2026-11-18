import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { MapComponent } from '../../../map/map.component'

@Component({
  selector: 'seed-group-map',
  template: '<seed-inventory-list-map [groupId]="groupId"></seed-inventory-list-map>',
  imports: [MapComponent],
  changeDetection: ChangeDetectionStrategy.Eager,
  host: { class: 'flex flex-col flex-auto min-h-0' },
})
export class GroupMapComponent {
  groupId = Number.parseInt(inject(ActivatedRoute).parent.snapshot.paramMap.get('groupId'))
}
