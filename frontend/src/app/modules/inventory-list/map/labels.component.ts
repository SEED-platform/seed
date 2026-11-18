import type { OnChanges, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output } from '@angular/core'
import { FormsModule } from '@angular/forms'
import type { CurrentUser, Label, LabelOperator } from '@seed/api'
import { OrganizationService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { isOrderedSubset } from '@seed/utils/string-matching.util'

@Component({
  selector: 'seed-inventory-list-map-labels',
  templateUrl: './labels.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, FormsModule],
})
export class LabelsComponent implements OnChanges {
  @Input() labels: Label[]
  @Input() selectedLabels: Label[]
  @Input() currentUser: CurrentUser
  @Output() labelChange = new EventEmitter<{ selectedLabelIds: number[]; operator: LabelOperator }>()
  private _organizationService = inject(OrganizationService)
  colorMap = {
    blue: '#2563eb',
    gray: '#4b5563',
    green: '#059669',
    'light blue': '#0284c7',
    orange: '#ea580c',
    red: '#dc2626',
  }
  filteredLabels: Label[]
  labelInput = ''
  labelOperators: { name: string; value: LabelOperator }[] = [
    { name: 'Includes All', value: 'and' },
    { name: 'Includes Any', value: 'or' },
    { name: 'Excludes', value: 'exclude' },
  ]
  labelOperator: LabelOperator = 'and'
  selectedLabelIds: number[] = []

  ngOnChanges(changes: SimpleChanges) {
    if (changes.labels || changes.currentUser) {
      if (this.currentUser && this.labels) {
        const userLabelIds = this.currentUser?.settings?.labels?.ids || []
        this.selectedLabels = this.labels.filter((label) => userLabelIds.includes(label.id))
        this.labelOperator = this.currentUser?.settings?.labels?.operator || 'and'
      }
      this.filteredLabels = this.labels
    }
  }

  removeLabel(label: Label) {
    if (!this.selectedLabels.includes(label)) return

    this.selectedLabels = this.selectedLabels.filter((l) => l.id !== label.id)
    this.onLabelChange()
  }

  addLabel(label: Label) {
    this.labelInput = null
    if (this.selectedLabels.includes(label)) return

    this.selectedLabels.push(label)
    label = null
    this.onLabelChange()
  }

  selectLabelOperator(operator: LabelOperator) {
    this.labelOperator = operator
    this.onLabelChange()
  }

  labelInputChange(event: Event) {
    const value = (event.target as HTMLInputElement).value
    this.filteredLabels = this.labels.filter((label) => isOrderedSubset(value, label.name))
  }

  onLabelChange() {
    this.selectedLabelIds = this.selectedLabels.map((label) => label.id)
    this.updateOrgUserSettings()
    this.labelChange.emit({ selectedLabelIds: this.selectedLabelIds, operator: this.labelOperator })
  }

  updateOrgUserSettings() {
    this.currentUser.settings.labels = { ids: this.selectedLabelIds, operator: this.labelOperator }
    this._organizationService
      .updateOrganizationUser(this.currentUser.org_user_id, this.currentUser.org_id, this.currentUser.settings)
      .subscribe()
  }
}
