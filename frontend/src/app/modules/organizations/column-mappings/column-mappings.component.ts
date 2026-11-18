import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import { ActivatedRoute, Router } from '@angular/router'
import { InventoryTabComponent, PageComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import type { InventoryType } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-organizations-column-mappings',
  templateUrl: './column-mappings.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [InventoryTabComponent, PageComponent, SharedImports],
})
export class ColumnMappingsComponent implements OnInit {
  private _route = inject(ActivatedRoute)
  private _router = inject(Router)

  readonly tabs: InventoryType[] = ['properties', 'taxlots']
  type = this._route.snapshot.paramMap.get('type') as InventoryType
  readonly urlSegment = 'column-mappings'
  readonly table_type = 'Column Mappings'

  ngOnInit(): void {
    console.log('organizations column mappings')
  }

  async toggleInventoryType(type: InventoryType) {
    if (type !== this.type) {
      const newRoute = `/organizations/column-mappings/${type}`
      await this._router.navigateByUrl(newRoute, { skipLocationChange: false })
      this.type = type
    }
  }
}
