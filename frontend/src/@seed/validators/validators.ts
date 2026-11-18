import type { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms'

export class SEEDValidators {
  /**
   * Check for empty (optional fields) values
   *
   * @param value
   */
  static isEmptyInputValue(value: unknown): boolean {
    if (typeof value === 'string') {
      return value.length === 0
    }
    return value == null
  }

  /**
   * Must match validator
   *
   * @param controlPath A dot-delimited string values that define the path to the control.
   * @param matchingControlPath A dot-delimited string values that define the path to the matching control.
   */
  static mustMatch(controlPath: string, matchingControlPath: string): ValidatorFn {
    return (formGroup: AbstractControl): ValidationErrors | null => {
      // Get the control and matching control
      const control = formGroup.get(controlPath)
      const matchingControl = formGroup.get(matchingControlPath)

      // Return if control or matching control doesn't exist
      if (!control || !matchingControl) {
        return null
      }

      // Delete the mustMatch error to reset the error on the matching control
      if (matchingControl.hasError('mustMatch')) {
        delete matchingControl.errors.mustMatch
        matchingControl.updateValueAndValidity()
      }

      // Don't validate empty values on the matching control
      // Don't validate if values are matching
      if (this.isEmptyInputValue(matchingControl.value) || control.value === matchingControl.value) {
        return null
      }

      // Prepare the validation errors
      const errors = { mustMatch: true }

      // Set the validation error on the matching control
      matchingControl.setErrors(errors)

      // Return the errors
      return errors
    }
  }

  static uniqueValue(existingValues: string[]): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      if (!control.value) return null
      const value = (control.value as string).trim().toLowerCase()
      const valueExists = existingValues.some((v) => v.toLowerCase() === value)

      return valueExists ? { valueExists: true } : null
    }
  }

  static afterDate(startKey: string): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      if (!control.value) return null
      const start = control.parent?.get(startKey)
      if (!start?.value) return null
      const _endDate = new Date(control.value as string)
      const _startDate = new Date(start.value as string)
      return _endDate < _startDate ? { dateBefore: true } : null
    }
  }
}
