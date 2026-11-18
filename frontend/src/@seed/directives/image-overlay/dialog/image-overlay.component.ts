import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA } from '@angular/material/dialog'
import { MaterialImports } from '@seed/materials'
import type { ImageOverlayData } from '../image-overlay.types'

@Component({
  selector: 'seed-image-overlay',
  templateUrl: './image-overlay.component.html',
  imports: [MaterialImports],
  changeDetection: ChangeDetectionStrategy.Eager,
  styles: ':host { @apply flex }',
})
export class OverlayImageComponent {
  data = inject(MAT_DIALOG_DATA) as ImageOverlayData
}
