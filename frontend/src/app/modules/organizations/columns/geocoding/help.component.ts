import { ChangeDetectionStrategy, Component, ViewEncapsulation } from '@angular/core'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-organizations-column-geocoding-help',
  templateUrl: './help.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [SharedImports, MaterialImports],
})
export class ColumnGeocodingHelpComponent {}
