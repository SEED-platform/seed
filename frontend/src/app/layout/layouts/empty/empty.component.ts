import { CdkScrollable } from '@angular/cdk/scrolling'
import { ChangeDetectionStrategy, Component, ViewEncapsulation } from '@angular/core'
import { RouterOutlet } from '@angular/router'
import { SEEDLoadingBarComponent } from '@seed/components'

@Component({
  selector: 'layout-empty',
  templateUrl: './empty.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CdkScrollable, RouterOutlet, SEEDLoadingBarComponent],
})
export class EmptyLayoutComponent {}
