import type { OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component } from '@angular/core'
import type { IHeaderAngularComp } from 'ag-grid-angular'
import type { IHeaderParams } from 'ag-grid-community'

type LabelGridContext = {
  labelsExpanded: boolean;
  toggleLabels: () => void;
}

@Component({
  selector: 'seed-inventory-label-header',
  template: `
    <div class="flex w-full cursor-pointer items-center gap-2 overflow-hidden" (click)="toggle()">
      <span class="material-icons-outlined" style="font-size:14px;line-height:1;" aria-hidden="true">{{
        expanded ? 'chevron_left' : 'chevron_right'
      }}</span>
      @if (expanded) {
        <span class="my-auto truncate">{{ displayName }}</span>
      }
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.Eager,
  standalone: true,
})
export class InventoryLabelHeaderComponent implements IHeaderAngularComp, OnDestroy {
  displayName = ''
  expanded = false

  private _params!: IHeaderParams<unknown, LabelGridContext>

  agInit(params: IHeaderParams<unknown, LabelGridContext>): void {
    this._params = params
    this.displayName = params.displayName
    this.expanded = params.context?.labelsExpanded ?? false
    // ag-grid owns header focus, so listen on the header cell itself for keyboard toggling
    params.eGridHeader.addEventListener('keydown', this._onKeyDown)
    this._updateHeaderAria()
  }

  refresh(params: IHeaderParams<unknown, LabelGridContext>): boolean {
    this._params = params
    this.expanded = params.context?.labelsExpanded ?? false
    this._updateHeaderAria()
    return true
  }

  ngOnDestroy(): void {
    this._params?.eGridHeader.removeEventListener('keydown', this._onKeyDown)
  }

  toggle(): void {
    this._params.context?.toggleLabels()
    this.expanded = this._params.context?.labelsExpanded ?? false
    this._updateHeaderAria()
  }

  private _onKeyDown = (event: KeyboardEvent) => {
    if (event.key !== 'Enter' && event.key !== ' ') return
    event.preventDefault()
    this.toggle()
  }

  private _updateHeaderAria(): void {
    const header = this._params.eGridHeader
    header.setAttribute('aria-expanded', String(this.expanded))
    header.setAttribute('aria-label', this.displayName)
  }
}
