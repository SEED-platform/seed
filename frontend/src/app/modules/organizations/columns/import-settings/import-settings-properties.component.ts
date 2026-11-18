import { ChangeDetectionStrategy, Component, type OnInit, ViewEncapsulation } from '@angular/core'
import { ReactiveFormsModule } from '@angular/forms'
import { map, takeUntil } from 'rxjs'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { ImportSettingsComponent } from './import-settings.component'

@Component({
  selector: 'seed-organizations-column-import-settings-properties',
  templateUrl: './import-settings.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [SharedImports, MaterialImports, ReactiveFormsModule],
})
export class ImportSettingsPropertiesComponent extends ImportSettingsComponent implements OnInit {
  type = 'PropertyState'

  ngOnInit(): void {
    this._columnService.propertyColumns$
      .pipe(takeUntil(this._unsubscribeAll$))
      .pipe(
        map((columns) => {
          this.prepareColumns(columns)
        }),
      )
      .subscribe()
  }
}
