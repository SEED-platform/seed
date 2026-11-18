import { ChangeDetectionStrategy, Component } from '@angular/core'
import type { IHeaderAngularComp } from 'ag-grid-angular'
import type { IHeaderParams } from 'ag-grid-community'

type IconHeaderParams = IHeaderParams & {
  icon: string;
  tooltip: string;
}

@Component({
  selector: 'seed-icon-header',
  template: ' <span class="material-icons-outlined text-base" [title]="tooltip" [attr.aria-label]="tooltip" role="img">{{ icon }}</span> ',
  changeDetection: ChangeDetectionStrategy.Eager,
  styles: `
    :host {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
    }
  `,
})
export class IconHeaderComponent implements IHeaderAngularComp {
  icon = ''
  tooltip = ''

  agInit(params: IconHeaderParams): void {
    this.icon = params.icon ?? ''
    this.tooltip = params.tooltip ?? params.displayName ?? ''
  }

  refresh(): boolean {
    return false
  }
}
