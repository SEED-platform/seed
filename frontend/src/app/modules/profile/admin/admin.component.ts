import { DatePipe } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, type FormGroupDirective, ReactiveFormsModule, Validators } from '@angular/forms'
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

@Component({
  selector: 'seed-admin',
  templateUrl: './admin.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [DatePipe, MaterialImports, ReactiveFormsModule, SharedImports],
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
  allUsers: UserBrief[] = []
  orgUsers: OrganizationUser[] = []

  // Organization table
  orgDataSource = new MatTableDataSource<AdminOrganization>([])
  orgColumns = ['id', 'name', 'created', 'number_of_users', 'property_count', 'taxlot_count', 'actions']

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
    organizationId: new FormControl<number>(null, Validators.required),
    role: new FormControl<UserRole>('member', Validators.required),
    accessLevel: new FormControl<string>(null, Validators.required),
    accessLevelInstanceId: new FormControl<number>(null, Validators.required),
  })

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
      this.orgDataSource.data = orgs
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
    if (this.createUserForm.valid) {
      const { firstName, lastName, email, organizationId, role, accessLevelInstanceId } = this.createUserForm.value
      this._userService
        .createUser(organizationId, {
          first_name: firstName,
          last_name: lastName,
          email,
          org_name: '',
          role,
          access_level_instance_id: accessLevelInstanceId,
        })
        .subscribe({
          complete: () => {
            this._snackBar.success(this._transloco.translate('User "{{email}}" created', { email }))
            formDirective.resetForm({ role: 'member' })
            this.createUserAccessLevelNames = []
            this.createUserAccessLevelInstances = []
            this.loadUsers()
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

  trackByOrgId(_index: number, org: AdminOrganization): number {
    return org.id
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
