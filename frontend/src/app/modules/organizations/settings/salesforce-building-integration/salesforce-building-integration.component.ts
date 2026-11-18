import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms'
import { MatDialog } from '@angular/material/dialog'
import { MatTableDataSource } from '@angular/material/table'
import { Subject, takeUntil, tap } from 'rxjs'
import type { BbSalesforceConfig, Column, Label, Organization, SalesforceConfig, SalesforceMapping } from '@seed/api'
import { BbSalesforceService, ColumnService, LabelService, OrganizationService, SalesforceService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { naturalSort } from '@seed/utils'
import { DeleteModalComponent, FormModalComponent } from './modal'

@Component({
  selector: 'seed-organizations-settings-salesforce-building-integration',
  templateUrl: './salesforce-building-integration.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, PageComponent, ReactiveFormsModule, SharedImports],
})
export class SalesforceBuildingIntegrationComponent implements OnDestroy, OnInit {
  private _organizationService = inject(OrganizationService)
  private _salesforceService = inject(SalesforceService)
  private _bbSalesforceService = inject(BbSalesforceService)
  private _labelService = inject(LabelService)
  private _columnService = inject(ColumnService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  private _dialog = inject(MatDialog)
  passwordHidden = true
  tokenHidden = true
  bbClientSecretHidden = true
  testConnectionStatus: 'idle' | 'success' | 'error' = 'idle'
  testConnectionMessage = ''
  isLoggedIntoBbSalesforce = false
  labels: Label[]
  columns: Column[]
  organization: Organization
  salesforceConfig: SalesforceConfig
  bbSalesforceConfig: BbSalesforceConfig
  salesforceMappings: SalesforceMapping[]
  salesforceMappingsDataSource = new MatTableDataSource<SalesforceMapping>([])
  salesforceMappingColumns = ['salesforce_fieldname', 'column', 'actions']
  salesforceForm = new FormGroup({
    salesforce_enabled: new FormControl(false),
    salesforceConfig: new FormGroup({
      delete_label_after_sync: new FormControl(false),
      id: new FormControl(null),
      organization_id: new FormControl(null),
      indication_label: new FormControl(null),
      violation_label: new FormControl(null),
      compliance_label: new FormControl(null),
      account_rec_type: new FormControl(''),
      contact_rec_type: new FormControl(''),
      unique_benchmark_id_fieldname: new FormControl(''),
      seed_benchmark_id_column: new FormControl(null),
      url: new FormControl(''),
      username: new FormControl(''),
      password: new FormControl(''),
      security_token: new FormControl(''),
      domain: new FormControl(''),
      cycle_fieldname: new FormControl(''),
      status_fieldname: new FormControl(''),
      labels_fieldname: new FormControl(''),
      contact_email_column: new FormControl(null),
      contact_name_column: new FormControl(null),
      account_name_column: new FormControl(null),
      default_contact_account_name: new FormControl(''),
      logging_email: new FormControl('', Validators.email),
      benchmark_contact_fieldname: new FormControl(''),
      data_admin_email_column: new FormControl(null),
      data_admin_name_column: new FormControl(null),
      data_admin_account_name_column: new FormControl(null),
      default_data_admin_account_name: new FormControl(''),
      data_admin_contact_fieldname: new FormControl(null),
      update_at_hour: new FormControl(0, [Validators.min(0), Validators.max(23)]),
      update_at_minute: new FormControl(0, [Validators.min(0), Validators.max(59)]),
    }),
  })
  bbSalesforceForm = new FormGroup({
    bb_salesforce_enabled: new FormControl(false),
    bbSalesforceConfig: new FormGroup({
      salesforce_url: new FormControl(''),
      client_id: new FormControl(''),
      client_secret: new FormControl(''),
    }),
  })

  ngOnInit(): void {
    this._organizationService.currentOrganization$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((organization) => {
      this.organization = organization
      this.salesforceForm.get('salesforce_enabled').setValue(this.organization.salesforce_enabled)
      this._setFormEnabledState(this.organization.salesforce_enabled)
      this.bbSalesforceForm.get('bb_salesforce_enabled').setValue(this.organization.bb_salesforce_enabled)
      this._setBbFormEnabledState(this.organization.bb_salesforce_enabled)
      if (this.organization.bb_salesforce_enabled) {
        this._checkBbLoginStatus()
      }
    })
    this._salesforceService.config$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((config) => {
      this.salesforceConfig = config
      for (const field of Object.keys(config)) {
        const key = `salesforceConfig.${field}`
        if (this.salesforceForm.get(key)) {
          this.salesforceForm.get(key).patchValue(config[field])
        }
      }
    })
    this._bbSalesforceService.config$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((config) => {
      this.bbSalesforceConfig = config
      for (const field of Object.keys(config ?? {})) {
        const key = `bbSalesforceConfig.${field}`
        if (this.bbSalesforceForm.get(key)) {
          this.bbSalesforceForm.get(key).patchValue(config[field])
        }
      }
    })
    this._salesforceService.mappings$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((mappings) => {
      this.salesforceMappings = mappings
      this.salesforceMappingsDataSource.data = mappings
    })
    this._labelService.labels$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((labels) => {
      this.labels = labels
    })
    this._columnService.propertyColumns$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((columns) => {
      this.columns = columns.sort((a, b) => naturalSort(a.display_name, b.display_name))
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  trackByFn(_index: number, { id }: SalesforceMapping) {
    return id
  }

  refreshMappings(): void {
    this._salesforceService.getMappings(this.organization.id).subscribe()
  }

  addMapping = () => {
    const newMapping: Omit<SalesforceMapping, 'id' | 'column' | 'salesforce_fieldname'> = {
      organization_id: this.organization.id,
    }
    const dialogRef = this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: { salesforceMapping: newMapping, organization_id: this.organization.id },
    })

    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap(() => {
          this.refreshMappings()
        }),
      )
      .subscribe()
  }

  deleteMapping(sfm: SalesforceMapping) {
    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { salesforceMapping: sfm, columnName: this.columns.find((c) => c.id === sfm.column).display_name },
    })

    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap(() => {
          this.refreshMappings()
        }),
      )
      .subscribe()
  }

  editMapping(sfm: SalesforceMapping) {
    const dialogRef = this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: { salesforceMapping: sfm, organization_id: this.organization.id },
    })

    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap(() => {
          this.refreshMappings()
        }),
      )
      .subscribe()
  }

  columnName(column_id: number): string {
    if (!this.columns) {
      return ''
    }
    return this.columns.find((c) => column_id === c.id).display_name
  }

  togglePassword(): void {
    this.passwordHidden = !this.passwordHidden
  }

  toggleToken(): void {
    this.tokenHidden = !this.tokenHidden
  }

  resetUpdateDate(): void {
    this.salesforceConfig.last_update_date = null
    this._salesforceService.update(this.organization.id, this.salesforceConfig, 'Reset Successful').subscribe((config) => {
      this.salesforceConfig = config
    })
  }

  testConnection(): void {
    this.testConnectionStatus = 'idle'
    this.updateConfig()
    this._salesforceService.test_connection(this.organization.id, this.salesforceConfig).subscribe({
      next: () => {
        this.testConnectionStatus = 'success'
        this.testConnectionMessage = ''
      },
      error: (error: { message?: string }) => {
        this.testConnectionStatus = 'error'
        this.testConnectionMessage = error?.message || 'Connection failed'
      },
    })
  }

  toggleForm(): void {
    const enabled = this.salesforceForm.get('salesforce_enabled').value
    this.organization.salesforce_enabled = enabled
    this._organizationService.updateSettings(this.organization).subscribe()
    this._setFormEnabledState(enabled)
  }

  updateConfig(): void {
    for (const field of Object.keys(this.salesforceForm.controls.salesforceConfig.controls)) {
      this.salesforceConfig[field] = this.salesforceForm.get(`salesforceConfig.${field}`).value
    }
  }

  submit(): void {
    if (this.salesforceForm.valid) {
      this.organization.salesforce_enabled = this.salesforceForm.get('salesforce_enabled').value
      this.updateConfig()
      this._organizationService.updateSettings(this.organization).subscribe()
      if (this.salesforceConfig.id) {
        this._salesforceService.update(this.organization.id, this.salesforceConfig).subscribe((config) => {
          this.salesforceConfig = config
        })
      } else {
        this._salesforceService.create(this.organization.id, this.salesforceConfig).subscribe((config) => {
          this.salesforceConfig = config
        })
      }
    }
  }

  toggleBbForm(): void {
    const enabled = this.bbSalesforceForm.get('bb_salesforce_enabled').value
    this.organization.bb_salesforce_enabled = enabled
    this._organizationService.updateSettings(this.organization).subscribe()
    this._setBbFormEnabledState(enabled)
    if (enabled) {
      this._checkBbLoginStatus()
    }
  }

  toggleBbClientSecret(): void {
    this.bbClientSecretHidden = !this.bbClientSecretHidden
  }

  bbLogin(): void {
    this._bbSalesforceService.getLoginUrl(this.organization.id).subscribe((data) => {
      if (data.status === 'error') {
        this.testConnectionMessage = data.response || 'Cannot login to Salesforce'
      } else if (data.url) {
        window.location.href = data.url
      }
    })
  }

  bbLogout(): void {
    this._bbSalesforceService.logout(this.organization.id).subscribe((data) => {
      if (data.status === 'success') {
        this.isLoggedIntoBbSalesforce = false
      }
    })
  }

  submitBb(): void {
    this.organization.bb_salesforce_enabled = this.bbSalesforceForm.get('bb_salesforce_enabled').value
    this._organizationService.updateSettings(this.organization).subscribe()
    const configValues = this.bbSalesforceForm.controls.bbSalesforceConfig.value
    // update_config endpoint handles upsert (create or update) using the org from query param
    this._bbSalesforceService.update(this.organization.id, configValues).subscribe((config) => {
      this.bbSalesforceConfig = config
    })
  }

  private _checkBbLoginStatus(): void {
    this._bbSalesforceService.verifyToken(this.organization.id).subscribe({
      next: (response) => {
        this.isLoggedIntoBbSalesforce = response.valid
      },
      error: () => {
        this.isLoggedIntoBbSalesforce = false
      },
    })
  }

  private _setFormEnabledState(enabled: boolean): void {
    const fg = this.salesforceForm.get('salesforceConfig') as FormGroup
    for (const field of Object.keys(fg.controls)) {
      if (enabled) {
        this.salesforceForm.get(`salesforceConfig.${field}`).enable()
      } else {
        this.salesforceForm.get(`salesforceConfig.${field}`).disable()
      }
    }
  }

  private _setBbFormEnabledState(enabled: boolean): void {
    const fg = this.bbSalesforceForm.get('bbSalesforceConfig') as FormGroup
    for (const field of Object.keys(fg.controls)) {
      if (enabled) {
        this.bbSalesforceForm.get(`bbSalesforceConfig.${field}`).enable()
      } else {
        this.bbSalesforceForm.get(`bbSalesforceConfig.${field}`).disable()
      }
    }
  }
}
