import { ChangeDetectionStrategy, Component } from '@angular/core'

@Component({
  selector: 'seed-edit-header',
  changeDetection: ChangeDetectionStrategy.Eager,
  template: `
    <div class="flex items-center gap-2">
      <span>{{ name }}</span>
      <span class="material-icons text-secondary my-auto scale-75">edit</span>
    </div>
  `,
})
export class EditHeaderComponent {
  name: string
  agInit(params: { name: string }): void {
    this.name = params.name
  }
}
