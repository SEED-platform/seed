import { ChangeDetectionStrategy, Component } from '@angular/core'
import type { ICellRenderer, ICellRendererParams, IRowNode } from 'ag-grid-community'
import type { ColumnMapping } from '@seed/api'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-organizations-column-mappings-delete-action',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './action-buttons.component.html',
  imports: [MaterialImports],
})
export class ActionButtonsComponent implements ICellRenderer {
  data: ColumnMapping
  params: ICellRendererParams & {
    onDelete: (mapping: ColumnMapping, node: IRowNode) => void;
    onEdit: (mapping: ColumnMapping, node: IRowNode) => void;
  }

  agInit(
    params: ICellRendererParams & {
      onDelete: (mapping: ColumnMapping, node: IRowNode) => void;
      onEdit: (mapping: ColumnMapping, node: IRowNode) => void;
    },
  ) {
    this.params = params
    this.data = params.data as ColumnMapping
  }
  refresh(_params: ICellRendererParams) {
    return true
  }

  delete(_$event) {
    this.params.onDelete(this.data, this.params.node)
  }
  edit(_$event) {
    this.params.onEdit(this.data, this.params.node)
  }
}
