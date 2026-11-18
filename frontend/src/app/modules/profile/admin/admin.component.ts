import { DatePipe, DecimalPipe, NgTemplateOutlet } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import {
  type AbstractControl,
  FormControl,
  FormGroup,
  type FormGroupDirective,
  ReactiveFormsModule,
  type ValidationErrors,
  Validators,
} from '@angular/forms'
import { MatDialog } from '@angular/material/dialog'
import { MatTableDataSource } from '@angular/material/table'
import { TranslocoService } from '@jsverse/transloco'
import { Subject, switchMap, takeUntil } from 'rxjs'
import type { AccessLevelsByDepth, AdminOrganization, CurrentUser, OrganizationUser, UserBrief, UserRole } from '@seed/api'
import { OrganizationService, ProgressService, UserService } from '@seed/api'
import { DeleteModalComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { AdminOrganizationRow, OrgTableRow } from './admin.utils'
import { buildOrgTableRows, isCycleTableRow, orgNameExists, toAdminOrganizationRow } from './admin.utils'

type CreateUserOrgMode = 'existing' | 'new'

@Component({
  selector: 'seed-admin',
  templateUrl: './admin.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [DatePipe, DecimalPipe, MaterialImports, NgTemplateOutlet, ReactiveFormsModule, SharedImports],
})
export class AdminComponent implements OnInit, OnDestroy {
  private _organizationService = inject(OrganizationService)
  private _userService = inject(UserService)
  private _progressService = inject(ProgressService)
  private _snackBar = inject(SnackBarService)
  private _dialog = inject(MatDialog)
  private _transloco = inject(TranslocoService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  currentUser: CurrentUser
  organizations: AdminOrganization[] = []
  organizationsLoaded = false
  allUsers: UserBrief[] = []
  orgUsers: OrganizationUser[] = []

  // Organization table
  orgDataSource = new MatTableDataSource<OrgTableRow>([])
  orgColumns = ['expand', 'parent_id', 'id', 'name', 'created', 'number_of_users', 'cycle_count', 'property_counts', 'taxlot_counts', 'actions']
  // Expanded cycle rows: a spacer spanning the columns before Cycles, then values under Cycles / Properties / Tax Lots
  cycleColumns = ['cycle_lead', 'cycle_name', 'cycle_properties', 'cycle_taxlots', 'cycle_trail']
  cycleLeadColspan = this.orgColumns.indexOf('cycle_count')
  private _orgRows: AdminOrganizationRow[] = []

  // Orgs whose per-cycle counts are expanded
  expandedOrgIds = new Set<number>()

  // Progress tracking for inventory deletion
  deletingInventory = new Map<number, number>()

  // Search controls for large selects
  orgSearch = new FormControl('')
  userSearch = new FormControl('')
  aliSearch = new FormControl('')

  // Create Organization form
  createOrgForm = new FormGroup({
    organizationName: new FormControl('', Validators.required),
    userId: new FormControl<number>(null, Validators.required),
  })

  // Create User form
  createUserForm = new FormGroup({
    firstName: new FormControl('', Validators.required),
    lastName: new FormControl('', Validators.required),
    email: new FormControl('', [Validators.required, Validators.email]),
    // Legacy parity: superusers can create the user in a brand-new org, which the user then owns
    orgMode: new FormControl<CreateUserOrgMode>('existing', { nonNullable: true }),
    newOrgName: new FormControl(
      { value: '', disabled: true },
      [
        (control: AbstractControl<string>) => (control.value?.trim() ? null : { required: true }),
        (control: AbstractControl<string>) => this._uniqueOrgName(control),
      ],
    ),
    organizationId: new FormControl<number>(null, Validators.required),
    role: new FormControl<UserRole>('member', Validators.required),
    accessLevel: new FormControl<string>(null, Validators.required),
    accessLevelInstanceId: new FormControl<number>(null, Validators.required),
  })

  // Create User controls that only apply when adding the user to an existing org
  private readonly _existingOrgControls = ['organizationId', 'role', 'accessLevel', 'accessLevelInstanceId'] as const

  // Access level state for create user form
  createUserAccessLevelNames: string[] = []
  createUserAccessLevelInstancesByDepth: AccessLevelsByDepth = {}
  createUserAccessLevelInstances: { id: number; name: string }[] = []

  // Add User to Org form
  addUserOrgForm = new FormGroup({
    organizationId: new FormControl<number>(null, Validators.required),
    userId: new FormControl<number>(null, Validators.required),
  })

  // Remove User from Org
  selectedRemoveOrgId: number | null = null
  removeOrgUsers: OrganizationUser[] = []

  roles: { value: UserRole; label: string }[] = [
    { value: 'owner', label: 'Owner' },
    { value: 'member', label: 'Member' },
    { value: 'viewer', label: 'Viewer' },
  ]

  // `when` predicates for the org table's two row templates
  isOrgRow = (_index: number, row: OrgTableRow) => !isCycleTableRow(row)
  isCycleRow = (_index: number, row: OrgTableRow) => isCycleTableRow(row)

  get sortedOrganizations() {
    const s = (this.orgSearch.value ?? '').toLowerCase()
    const orgs = [...this.organizations].sort((a, b) => a.name.localeCompare(b.name))
    return s ? orgs.filter((o) => o.name.toLowerCase().includes(s)) : orgs
  }

  get filteredUsers() {
    const s = (this.userSearch.value ?? '').toLowerCase()
    return s ? this.allUsers.filter((u) => u.email.toLowerCase().includes(s)) : this.allUsers
  }

  get filteredAccessLevelInstances() {
    const s = (this.aliSearch.value ?? '').toLowerCase()
    return s ? this.createUserAccessLevelInstances.filter((a) => a.name.toLowerCase().includes(s)) : this.createUserAccessLevelInstances
  }

  resetSearch(ctrl: FormControl): void {
    ctrl.setValue('')
  }

  ngOnInit(): void {
    this._userService.currentUser$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((user) => {
      this.currentUser = user
    })

    this.loadOrganizations()
    this.loadUsers()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  loadOrganizations(): void {
    this._organizationService.getAllOrganizations().subscribe((orgs) => {
      this.organizations = orgs
      this.organizationsLoaded = true
      this.createUserForm.controls.newOrgName.updateValueAndValidity()
      this._orgRows = orgs.map(toAdminOrganizationRow)
      this._refreshOrgTable()
    })
  }

  loadUsers(): void {
    this._userService.getAllUsers().subscribe((users) => {
      this.allUsers = users
    })
  }

  // --- Organization Management ---

  removeInventory(org: AdminOrganization): void {
    this.deletingInventory.set(org.id, 0)
    this._organizationService
      .deleteOrganizationInventory(org.id)
      .pipe(
        switchMap((response) => {
          return this._progressService.checkProgressLoop$(response.progress_key)
        }),
      )
      .subscribe({
        next: (progress) => {
          this.deletingInventory.set(org.id, progress.progress)
        },
        error: () => {
          this.deletingInventory.delete(org.id)
          this._snackBar.alert(this._transloco.translate('Failed to remove inventory for {{orgName}}', { orgName: org.name }))
        },
        complete: () => {
          this.deletingInventory.delete(org.id)
          this._snackBar.success(this._transloco.translate('Inventory removed for {{orgName}}', { orgName: org.name }))
          this.loadOrganizations()
        },
      })
  }

  deleteOrganization(org: AdminOrganization): void {
    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '400px',
      data: { instance: org.name, model: 'Organization' },
    })

    dialogRef.afterClosed().subscribe((confirmed) => {
      if (confirmed) {
        this._organizationService.deleteOrganization(org.id).subscribe({
          complete: () => {
            this._snackBar.success(this._transloco.translate('Organization "{{orgName}}" deleted', { orgName: org.name }))
            this.loadOrganizations()
            this._organizationService.getBrief().subscribe()
          },
        })
      }
    })
  }

  // --- Create Organization ---

  onCreateOrg(formDirective: FormGroupDirective): void {
    if (this.createOrgForm.valid) {
      const { organizationName, userId } = this.createOrgForm.value
      this._organizationService.createOrganization(userId, organizationName).subscribe({
        complete: () => {
          this._snackBar.success(this._transloco.translate('Organization "{{orgName}}" created', { orgName: organizationName }))
          formDirective.resetForm()
          this.loadOrganizations()
          // Refresh the org dropdown in the top-right nav
          this._organizationService.getBrief().subscribe()
        },
      })
    }
  }

  // --- Create User ---

  onCreateUserOrgModeChange(): void {
    const isNew = this.createUserForm.controls.orgMode.value === 'new'
    const { newOrgName } = this.createUserForm.controls
    if (isNew) {
      newOrgName.enable()
    } else {
      newOrgName.disable()
    }
    for (const name of this._existingOrgControls) {
      const control = this.createUserForm.get(name)
      if (isNew) {
        control.disable()
      } else {
        control.enable()
      }
    }
  }

  onCreateUserOrgChange(): void {
    const orgId = this.createUserForm.get('organizationId').value
    if (!orgId) return
    this._organizationService.getAccessLevelTree(orgId).subscribe(({ accessLevelNames, accessLevelTree }) => {
      this.createUserAccessLevelNames = accessLevelNames
      this.createUserAccessLevelInstancesByDepth = this._calculateAccessLevelsByDepth(accessLevelTree)
      // Default to last access level name and first instance
      const defaultLevel = accessLevelNames.at(-1)
      this.createUserForm.get('accessLevel').setValue(defaultLevel)
      this.onCreateUserAccessLevelChange()
    })
  }

  onCreateUserAccessLevelChange(): void {
    const accessLevel = this.createUserForm.get('accessLevel').value
    const depth = this.createUserAccessLevelNames.findIndex((name) => name === accessLevel)
    this.createUserAccessLevelInstances = this.createUserAccessLevelInstancesByDepth[depth] ?? []
    if (this.createUserAccessLevelInstances.length) {
      this.createUserForm.get('accessLevelInstanceId').setValue(this.createUserAccessLevelInstances[0].id)
    }
  }

  onCreateUser(formDirective: FormGroupDirective): void {
    const isNewOrg = this.createUserForm.controls.orgMode.value === 'new'
    if (this.createUserForm.valid && (!isNewOrg || this.organizationsLoaded)) {
      const { firstName, lastName, email, newOrgName, organizationId, role, accessLevelInstanceId } = this.createUserForm.value
      this._userService
        .createUser(isNewOrg ? null : organizationId, {
          first_name: firstName,
          last_name: lastName,
          email,
          org_name: isNewOrg ? newOrgName.trim() : '',
          // The backend makes the user the owner of a newly created org
          role: isNewOrg ? 'owner' : role,
          access_level_instance_id: isNewOrg ? null : accessLevelInstanceId,
        })
        .subscribe({
          next: (response) => {
            const message = response.org_created
              ? this._transloco.translate('User "{{email}}" created as owner of new organization "{{orgName}}"', { email, orgName: response.org })
              : this._transloco.translate('User "{{email}}" created', { email })
            this._snackBar.success(message)
            formDirective.resetForm({ role: 'member', orgMode: 'existing' })
            this.onCreateUserOrgModeChange()
            this.createUserAccessLevelNames = []
            this.createUserAccessLevelInstances = []
            this.loadUsers()
            if (response.org_created) {
              this.loadOrganizations()
              // Refresh the org dropdown in the top-right nav
              this._organizationService.getBrief().subscribe()
            }
          },
        })
    }
  }

  // --- Add User to Org ---

  onAddUserToOrg(formDirective: FormGroupDirective): void {
    if (this.addUserOrgForm.valid) {
      const { organizationId, userId } = this.addUserOrgForm.value
      this._organizationService.addUserToOrganization(organizationId, userId).subscribe({
        complete: () => {
          const user = this.allUsers.find((u) => u.user_id === userId)
          this._snackBar.success(this._transloco.translate('User "{{email}}" added to organization', { email: user?.email }))
          formDirective.resetForm()
          this.loadOrganizations()
        },
      })
    }
  }

  // --- Remove User from Org ---

  onRemoveOrgChange(): void {
    if (this.selectedRemoveOrgId) {
      this._organizationService.getOrganizationUsers(this.selectedRemoveOrgId).subscribe((users) => {
        this.removeOrgUsers = users
      })
    } else {
      this.removeOrgUsers = []
    }
  }

  removeUserFromOrg(user: OrganizationUser): void {
    const orgId = this.selectedRemoveOrgId
    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '400px',
      data: { instance: user.email, model: 'User' },
    })

    dialogRef.afterClosed().subscribe((confirmed) => {
      if (confirmed) {
        this._organizationService.deleteOrganizationUser(user.user_id, orgId).subscribe({
          complete: () => {
            this._snackBar.success(this._transloco.translate('User "{{email}}" removed from organization', { email: user.email }))
            this.onRemoveOrgChange()
            this.loadOrganizations()
          },
        })
      }
    })
  }

  trackByOrgRow(_index: number, row: OrgTableRow): string {
    return isCycleTableRow(row) ? `${row.cycleOf.id}:${row.cycle.cycle}` : `${row.id}`
  }

  toggleOrgExpanded(org: AdminOrganization): void {
    if (!this.expandedOrgIds.delete(org.id)) {
      this.expandedOrgIds.add(org.id)
    }
    this._refreshOrgTable()
  }

  private _refreshOrgTable(): void {
    this.orgDataSource.data = buildOrgTableRows(this._orgRows, this.expandedOrgIds)
  }

  private _uniqueOrgName(control: AbstractControl<string>): ValidationErrors | null {
    return control.value && orgNameExists(this.organizations, control.value) ? { orgExists: true } : null
  }

  private _calculateAccessLevelsByDepth(
    tree: { id: number; name: string; children?: { id: number; name: string; children?: unknown[] }[] }[],
    depth = 0,
    result: AccessLevelsByDepth = {},
  ): AccessLevelsByDepth {
    if (!tree) return result
    result[depth] ??= []
    for (const { children, id, name } of tree) {
      result[depth].push({ id, name })
      if (children?.length) {
        this._calculateAccessLevelsByDepth(children as typeof tree, depth + 1, result)
      }
    }
    return result
  }
}
