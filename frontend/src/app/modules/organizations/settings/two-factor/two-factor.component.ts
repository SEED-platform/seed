import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms'
import { Subject, takeUntil } from 'rxjs'
import type { Organization } from '@seed/api'
import { OrganizationService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-organizations-settings-two-factor',
  templateUrl: './two-factor.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, PageComponent, ReactiveFormsModule, SharedImports],
})
export class TwoFactorComponent implements OnDestroy, OnInit {
  private _organizationService = inject(OrganizationService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  betterVerifiedIcon = ''
  betterVerifiedIconColor = 'primary'
  organization: Organization
  twoFactorForm = new FormGroup({
    require_2fa: new FormControl(false),
  })

  ngOnInit(): void {
    this._organizationService.currentOrganization$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((organization) => {
      this.organization = organization
      this.twoFactorForm.get('require_2fa').setValue(this.organization.require_2fa)
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  submit(): void {
    if (this.twoFactorForm.valid) {
      this.organization.require_2fa = this.twoFactorForm.get('require_2fa').value
      this._organizationService.updateSettings(this.organization).subscribe()
    }
  }
}
