import { CommonModule } from '@angular/common'
import type { OnChanges, OnDestroy, OnInit, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, Input } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { Subject } from 'rxjs'
import { SharedImports } from '@seed/directives'
import type { InventoryType } from 'app/modules/inventory/inventory.types'
import type { Config } from './inventory-tab.types'

@Component({
  selector: 'seed-page-inventory-tab',
  templateUrl: './inventory-tab.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, SharedImports],
})
export class InventoryTabComponent implements OnChanges, OnDestroy, OnInit {
  private _route = inject(ActivatedRoute)
  @Input() config: Config
  @Input() inputType?: InventoryType // special case for organization columns
  type: InventoryType
  private readonly _unsubscribeAll$ = new Subject<void>()

  ngOnInit(): void {
    this._route.paramMap.subscribe((params) => {
      this.type = (params.get('type') as InventoryType) || this.inputType
    })
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.inputType && this.inputType) {
      this.type = this.inputType
    }
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
