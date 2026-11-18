import { ChangeDetectionStrategy, Component } from '@angular/core'
import type { IHeaderAngularComp } from 'ag-grid-angular'
import type { IHeaderParams } from 'ag-grid-community'
import type { LabelColumnKey, PortfolioSummaryGridContext } from './portfolio-summary.types'

@Component({
  selector: 'seed-portfolio-summary-label-header',
  template: `
    <div class="flex w-full cursor-pointer items-center gap-2 overflow-hidden" (click)="toggle()">
      <span class="material-icons-outlined" style="font-size:14px;line-height:1;">{{ expanded ? 'chevron_left' : 'chevron_right' }}</span>
      @if (expanded) {
        <span class="my-auto truncate">{{ displayName }}</span>
      }
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.Eager,
  standalone: true,
})
export class PortfolioSummaryLabelHeaderComponent implements IHeaderAngularComp {
  displayName = ''
  expanded = false

  private _key: LabelColumnKey = 'baseline'
  private _params!: IHeaderParams<unknown, PortfolioSummaryGridContext>

  agInit(params: IHeaderParams<unknown, PortfolioSummaryGridContext>): void {
    this._params = params
    this.displayName = params.displayName
    this._key = params.column.getColId() === 'baseline_labels' ? 'baseline' : 'current'
    this.expanded = params.context?.labelsExpanded[this._key] ?? false
  }

  refresh(params: IHeaderParams<unknown, PortfolioSummaryGridContext>): boolean {
    this._params = params
    this.expanded = params.context?.labelsExpanded[this._key] ?? false
    return true
  }

  toggle(): void {
    this._params.context?.toggleLabels(this._key)
    this.expanded = this._params.context?.labelsExpanded[this._key] ?? false
  }
}
