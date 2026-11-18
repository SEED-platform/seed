import { CommonModule } from '@angular/common'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import { MAT_DIALOG_DATA } from '@angular/material/dialog'
import { MaterialImports } from '@seed/materials'
import type { ConfirmationConfig } from '..'

@Component({
  selector: 'seed-confirmation-dialog',
  templateUrl: './dialog.component.html',
  styleUrl: './dialog.component.scss',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, MaterialImports],
})
export class ConfirmationDialogComponent {
  data = inject(MAT_DIALOG_DATA) as ConfirmationConfig
}
