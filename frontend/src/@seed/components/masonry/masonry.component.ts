import { CommonModule } from '@angular/common'
import type { AfterViewInit, OnChanges, SimpleChanges, TemplateRef } from '@angular/core'
import { ChangeDetectionStrategy, Component, input, ViewEncapsulation } from '@angular/core'
import { Animations } from '@seed/animations'

@Component({
  selector: 'seed-masonry',
  templateUrl: './masonry.component.html',
  encapsulation: ViewEncapsulation.None,
  animations: Animations,
  exportAs: 'seedMasonry',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule],
})
export class MasonryComponent implements OnChanges, AfterViewInit {
  columnsTemplate = input.required<TemplateRef<unknown>>()
  columns = input.required<number>()
  items = input.required<unknown[]>()
  distributedColumns: { items: unknown[] }[] = []

  ngOnChanges(changes: SimpleChanges): void {
    if ('columns' in changes || 'items' in changes) {
      this._distributeItems()
    }
  }

  ngAfterViewInit(): void {
    // Distribute the items for the first time
    this._distributeItems()
  }

  /**
   * Distribute items into columns
   */
  private _distributeItems(): void {
    // Return an empty array if there are no items
    if (this.items().length === 0) {
      this.distributedColumns = []
      return
    }

    // Prepare the distributed columns array
    this.distributedColumns = Array.from(Array(this.columns()), () => ({
      items: [],
    }))

    // Distribute the items to columns
    for (let i = 0; i < this.items().length; ++i) {
      this.distributedColumns[i % this.columns()].items.push(this.items()[i])
    }
  }
}
