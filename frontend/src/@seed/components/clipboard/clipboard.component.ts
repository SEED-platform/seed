import { Clipboard } from '@angular/cdk/clipboard'
import { ChangeDetectionStrategy, Component, inject, input } from '@angular/core'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from '../../../app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-clipboard',
  templateUrl: './clipboard.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports],
})
export class ClipboardComponent {
  private _clipboard = inject(Clipboard)
  private _snackBar = inject(SnackBarService)

  text = input<string>()

  // Called when the user clicks the icon button.
  copyText(): void {
    this._clipboard.copy(this.text())
    this._snackBar.success('Copied!')
  }
}
