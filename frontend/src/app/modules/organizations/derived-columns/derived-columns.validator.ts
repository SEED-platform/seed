import { Injectable } from '@angular/core'
import type { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms'

@Injectable({ providedIn: 'root' })
export class DerivedColumnsValidator {
  inExpression(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      const parentControl = control.parent?.parent?.parent
      if (!parentControl) {
        return null
      }
      const parameterName = control.value as string
      const expression = parentControl.get('expression')?.value as string
      const regex = new RegExp(`\\$${parameterName}([^_a-zA-Z0-9]|$)`)
      return regex.test(expression) ? null : { missing: true }
    }
  }
}
