import { formatDate } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms'
import { Subject, takeUntil } from 'rxjs'
import type { AuditTemplateConfig, Organization } from '@seed/api'
import { AuditTemplateService, OrganizationService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-organizations-settings-audit-template',
  templateUrl: './audit-template.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, PageComponent, ReactiveFormsModule, SharedImports],
})
export class AuditTemplateComponent implements OnDestroy, OnInit {
  private _organizationService = inject(OrganizationService)
  private _auditTemplateService = inject(AuditTemplateService)
  private _snackBar = inject(SnackBarService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  organization: Organization
  auditTemplateConfig: AuditTemplateConfig = {
    update_at_day: 0,
    update_at_hour: 0,
    update_at_minute: 0,
    id: null,
    organization: null,
  }
  auditTemplateReportTypes: string[]
  auditTemplateForm = new FormGroup({
    at_organization_token: new FormControl(''),
    audit_template_user: new FormControl('', Validators.email),
    audit_template_password: new FormControl(''),
    audit_template_city_id: new FormControl(),
    status_complies: new FormControl(false),
    status_pending: new FormControl(false),
    status_received: new FormControl(false),
    status_rejected: new FormControl(false),
    audit_template_conditional_import: new FormControl(false),
    audit_template_sync_enabled: new FormControl(false),
    audit_template_report_type: new FormControl(''),
    audit_template_config_day: new FormControl(0),
    audit_template_config_hour: new FormControl(1),
    audit_template_config_minute: new FormControl(1),
  })
  status_fields = [
    { key: 'Complies', field: 'status_complies' },
    { key: 'Pending', field: 'status_pending' },
    { key: 'Received', field: 'status_received' },
    { key: 'Rejected', field: 'status_rejected' },
  ]
  passwordHidden = true
  days = [
    { index: 0, name: 'Sunday' },
    { index: 1, name: 'Monday' },
    { index: 2, name: 'Tuesday' },
    { index: 3, name: 'Wednesday' },
    { index: 4, name: 'Thursday' },
    { index: 5, name: 'Friday' },
    { index: 6, name: 'Saturday' },
  ]
  minutes = Array.from(Array(60).keys())
  hours = Array.from(Array(24).keys())

  ngOnInit(): void {
    this._organizationService.currentOrganization$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((organization) => {
      this.organization = organization
      this.auditTemplateForm.patchValue(this.organization)
      for (const field of this.status_fields) {
        this.auditTemplateForm.get(field.field).setValue(this.organization.audit_template_status_types.includes(field.key))
      }
      if (!this.organization.audit_template_sync_enabled) {
        this.auditTemplateForm.get('audit_template_config_day').disable()
        this.auditTemplateForm.get('audit_template_config_hour').disable()
        this.auditTemplateForm.get('audit_template_config_minute').disable()
      }
      if (this.auditTemplateConfig) {
        this.auditTemplateConfig.organization = organization.id
      }
    })
    this._auditTemplateService.reportTypes$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((types) => {
      this.auditTemplateReportTypes = types
    })
    this._auditTemplateService.auditTemplateConfig$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((config) => {
      if (config) {
        this.auditTemplateConfig = config
      }
      this.auditTemplateForm.get('audit_template_config_day').setValue(this.auditTemplateConfig.update_at_day)
      this.auditTemplateForm.get('audit_template_config_hour').setValue(this.auditTemplateConfig.update_at_hour)
      this.auditTemplateForm.get('audit_template_config_minute').setValue(this.auditTemplateConfig.update_at_minute)
    })
  }

  updateScheduleInputs(): void {
    if (this.auditTemplateForm.get('audit_template_sync_enabled').value) {
      this.auditTemplateForm.get('audit_template_config_day').enable()
      this.auditTemplateForm.get('audit_template_config_hour').enable()
      this.auditTemplateForm.get('audit_template_config_minute').enable()
    } else {
      this.auditTemplateForm.get('audit_template_config_day').disable()
      this.auditTemplateForm.get('audit_template_config_hour').disable()
      this.auditTemplateForm.get('audit_template_config_minute').disable()
    }
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  togglePassword(): void {
    this.passwordHidden = !this.passwordHidden
  }

  importSubmissions(): void {
    // TODO - Build out import wizard
    console.log('Not implemented')
    this._snackBar.warning('Not implemented')
  }

  submit(): void {
    if (this.auditTemplateForm.valid) {
      this.organization = { ...this.organization, ...this.auditTemplateForm.value }

      this.organization.audit_template_status_types = this.status_fields
        .filter((f) => this.auditTemplateForm.get(f.field).value === true)
        .map((f) => f.key)
        .join(',')
      this._organizationService.updateSettings(this.organization).subscribe()

      if (this.organization.audit_template_sync_enabled) {
        this.auditTemplateConfig.update_at_day = this.auditTemplateForm.get('audit_template_config_day').value
        this.auditTemplateConfig.update_at_hour = this.auditTemplateForm.get('audit_template_config_hour').value
        this.auditTemplateConfig.update_at_minute = this.auditTemplateForm.get('audit_template_config_minute').value
        this.auditTemplateConfig.last_update_date = formatDate(new Date(), 'yyyy:MM:dd', 'en-us')
        if (!this.auditTemplateConfig.id) {
          this._auditTemplateService.create(this.auditTemplateConfig).subscribe((atc) => {
            this.auditTemplateConfig = atc
          })
        } else {
          this._auditTemplateService.update(this.auditTemplateConfig).subscribe((atc) => (this.auditTemplateConfig = atc))
        }
      }
    }
  }
}
