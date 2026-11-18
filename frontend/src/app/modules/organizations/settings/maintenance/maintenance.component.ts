import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { OrganizationService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-organizations-settings-maintenance',
  templateUrl: './maintenance.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, PageComponent],
})
export class MaintenanceComponent {
  private _organizationService = inject(OrganizationService)
  organization$ = this._organizationService.currentOrganization$
}
