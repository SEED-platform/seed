import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DOCUMENT, inject } from '@angular/core'
import { FormsModule, ReactiveFormsModule } from '@angular/forms'
import { Subject, takeUntil } from 'rxjs'
import type { CurrentUser } from '@seed/api'
import { UserService } from '@seed/api'
import { ClipboardComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-profile-developer',
  templateUrl: './developer.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ClipboardComponent, FormsModule, MaterialImports, ReactiveFormsModule, SharedImports],
})
export class ProfileDeveloperComponent implements OnInit, OnDestroy {
  private _changeDetectorRef = inject(ChangeDetectorRef)
  private _document = inject(DOCUMENT)
  private _snackBar = inject(SnackBarService)
  private _userService = inject(UserService)

  user: CurrentUser

  private readonly _unsubscribeAll$ = new Subject<void>()

  ngOnInit(): void {
    // Subscribe to user changes
    this._userService.currentUser$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((currentUser) => {
      this.user = currentUser

      // Mark for check
      this._changeDetectorRef.markForCheck()
    })
  }

  generateKey(): void {
    // send request to generate a new key; refresh user
    this._userService.generateApiKey().subscribe({
      error: (error) => {
        console.error('Error generating API key:', error)
        this._snackBar.alert('Failed to generate new API key')
      },
      complete: () => {
        this._snackBar.success('New API Key Generated!')
      },
    })
  }

  getHost(): string {
    const { hostname, protocol } = this._document.location
    const port = Number(this._document.location.port)
    const showPort = (protocol === 'http:' && port !== 80) || (protocol === 'https:' && port !== 443)

    return `${protocol}//${hostname}${showPort ? `:${port}` : ''}`
  }

  getCurl(): string {
    return `curl -s -X GET \\
  '${this.getHost()}/api/version/' \\
  -H 'Accept: application/json' \\
  -u ${this.user.username}:${this.user.api_key}`
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
