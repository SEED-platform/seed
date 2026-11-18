import { CommonModule } from '@angular/common'
import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { type Observable, tap } from 'rxjs'
import { OrganizationService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { ColumnProfilesComponent } from '@seed/components/column-profiles/column-profiles.component'
import type { InventoryDisplayType, InventoryType } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-inventory-detail-profiles',
  templateUrl: './column-detail-profiles.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [ColumnProfilesComponent, CommonModule, PageComponent],
})
export class ColumnDetailProfilesComponent implements OnInit {
  @ViewChild('columnProfiles') columnProfiles: ColumnProfilesComponent
  private _organizationService = inject(OrganizationService)
  private _route = inject(ActivatedRoute)
  viewId: number
  type: InventoryType
  displayName: InventoryDisplayType
  viewDisplayField$: Observable<string>

  ngOnInit(): void {
    this.getParams().subscribe()
  }

  getParams() {
    return this._route.parent.paramMap.pipe(
      tap((params) => {
        this.viewId = parseInt(params.get('id'))
        this.type = params.get('type') as InventoryType
        this.displayName = this.type === 'taxlots' ? 'Tax Lot' : 'Property'
        this.viewDisplayField$ = this._organizationService.getViewDisplayField(this.viewId, this.type)
      }),
    )
  }

  onSave = () => {
    this.columnProfiles.onSave()
  }
}
