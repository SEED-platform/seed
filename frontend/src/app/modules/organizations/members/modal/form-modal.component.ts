import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { Observable } from 'rxjs'
import { forkJoin, Subject, takeUntil, tap } from 'rxjs'
import type { AccessLevelInstancesByDepth, AccessLevelsByDepth, CreateUserRequest, OrganizationUser, UserRole } from '@seed/api'
import { OrganizationService, UserService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-organizations-members-form-modal',
  templateUrl: './form-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ReactiveFormsModule],
})
export class FormModalComponent implements OnDestroy, OnInit {
  private _dialogRef = inject(MatDialogRef<FormModalComponent>)
  private _organizationService = inject(OrganizationService)
  private _userService = inject(UserService)
  private _snackBar = inject(SnackBarService)
  data = inject(MAT_DIALOG_DATA) as { member: OrganizationUser | null; orgId: number }

  private readonly _unsubscribeAll$ = new Subject<void>()
  accessLevelNames: AccessLevelInstancesByDepth['accessLevelNames']
  accessLevelInstancesByDepth: AccessLevelsByDepth = {}
  accessLevelInstances: AccessLevelsByDepth[keyof AccessLevelsByDepth] = []
  roles = ['owner', 'member', 'viewer']
  form = new FormGroup({
    first_name: new FormControl('', Validators.required),
    last_name: new FormControl('', Validators.required),
    email: new FormControl('', [Validators.required, Validators.email]),
    access_level: new FormControl<string | null>(null, Validators.required),
    access_level_instance_id: new FormControl<number | null>(null, Validators.required),
    role: new FormControl<UserRole | null>('member', Validators.required),
  })
  create = true

  ngOnInit(): void {
    this.patchForm()
    this.getALITree()
    this.watchForm()
  }

  getALITree() {
    this._organizationService.accessLevelTree$.pipe(takeUntil(this._unsubscribeAll$)).subscribe(({ accessLevelNames }) => {
      this.accessLevelNames = accessLevelNames
      // suggest access level if null
      if (!this.form.get('access_level')?.value) {
        this.form.get('access_level')?.setValue(accessLevelNames.at(-1))
      }
    })

    this._organizationService.accessLevelInstancesByDepth$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((accessLevelsByDepth) => {
      this.accessLevelInstancesByDepth = accessLevelsByDepth
      this.getPossibleAccessLevelInstances(this.form.get('access_level')?.value)
      // suggest access level instance if null
      if (!this.form.get('access_level_instance_id')?.value) {
        this.form.get('access_level_instance_id')?.setValue(this.accessLevelInstances[0]?.id)
      }
    })
  }

  patchForm() {
    this.form.patchValue(this.data.member)
    // disable name and email if editing existing member
    if (this.data.member) {
      this.create = false
      this.form.get('first_name')?.disable()
      this.form.get('last_name')?.disable()
      this.form.get('email')?.disable()
    }
  }

  watchForm() {
    // watch for changes to access level and repopulate access level instances
    this.form
      .get('access_level')
      ?.valueChanges.pipe(
        takeUntil(this._unsubscribeAll$),
        tap((accessLevel) => {
          this.getPossibleAccessLevelInstances(accessLevel)
          // default to first access level instance
          this.form.get('access_level_instance_id')?.setValue(this.accessLevelInstances[0]?.id)
        }),
      )
      .subscribe()
  }

  getPossibleAccessLevelInstances(accessLevelName: string): void {
    const depth = this.accessLevelNames.findIndex((name) => name === accessLevelName)
    this.accessLevelInstances = this.accessLevelInstancesByDepth[depth]
  }

  onSubmit(): void {
    if (this.create) {
      this.createMember()
    } else {
      this.editMember()
    }
  }

  createMember() {
    const { first_name, last_name, email, access_level_instance_id, role } = this.form.value
    const userDetails: CreateUserRequest = {
      first_name,
      last_name,
      email,
      access_level_instance_id,
      role,
      org_name: null,
    }
    this._userService.createUser(this.data.orgId, userDetails).subscribe(() => {
      this._snackBar.success('User created')
      this._dialogRef.close()
    })
  }

  editMember() {
    const { member, orgId } = this.data
    const { role, access_level, access_level_instance_id } = this.form.value
    const requests: Observable<{ status: string }>[] = []

    // update role
    if (member.role !== role) {
      requests.push(this._userService.updateUserRole(member.user_id, orgId, role))
    }
    // update access levels
    if (member.access_level !== access_level || member.access_level_instance_id !== access_level_instance_id) {
      requests.push(this._userService.updateUserAccessLevelInstance(member.user_id, orgId, access_level_instance_id))
    }
    // wait for both to finish
    if (requests.length) {
      forkJoin(requests)
        .pipe(
          takeUntil(this._unsubscribeAll$),
          tap(() => {
            this._snackBar.success('User updated')
            this._dialogRef.close()
          }),
        )
        .subscribe()
    }
  }

  dismiss() {
    this._dialogRef.close('dismiss')
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
