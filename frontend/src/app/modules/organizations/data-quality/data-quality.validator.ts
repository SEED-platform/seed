import { Injectable } from '@angular/core'
import { type ValidationErrors, type ValidatorFn } from '@angular/forms'
import type { DataQualityFormGroup, Rule } from '@seed/api'
import { DATATYPE_LOOKUP } from './constants'

@Injectable({ providedIn: 'root' })
export class DataQualityValidator {
  hasRange(): ValidatorFn {
    return (formGroup: DataQualityFormGroup): ValidationErrors | null => {
      const { min, max, condition, data_type } = formGroup.value

      if (condition !== 'range') return null
      if (min === null && max === null) return { rangeRequired: 'Min or max required' }
      // cant have a mismatch if one is null
      if (min === null || max === null) return null

      // date check
      if (data_type === 2) {
        const minDate = new Date(min)
        const maxDate = new Date(max)
        return minDate >= maxDate ? { rangeMismatch: 'Min must be before max' } : null
      }

      if (min >= max) return { rangeMismatch: 'Min must be before max' }

      return null
    }
  }

  hasTextMatch(): ValidatorFn {
    return (formGroup: DataQualityFormGroup): ValidationErrors | null => {
      const { condition, text_match } = formGroup.value

      if (['exclude', 'include'].includes(condition) && !text_match) {
        return { textMatchRequired: 'Text match required' }
      }

      return null
    }
  }

  dataTypeMatch(currentRules: Rule[]): ValidatorFn {
    return (formGroup: DataQualityFormGroup): ValidationErrors | null => {
      const { id, field, data_type } = formGroup.value
      const fieldRules = currentRules.filter((rule) => rule.field === field && rule.id !== id)
      if (!fieldRules.length) return null

      const existingDataType = DATATYPE_LOOKUP[fieldRules[0].data_type]
      if (!existingDataType) return null
      if (data_type !== fieldRules[0].data_type) {
        return { dataTypeMismatch: `Rules of the same field cannot have different data types. Try [ ${existingDataType} ]` }
      }

      return null
    }
  }

  hasValidLabel(): ValidatorFn {
    return (formGroup: DataQualityFormGroup): ValidationErrors | null => {
      const { severity, status_label } = formGroup.value

      if (severity === 2 && !status_label) return { invalidLabel: 'Valid severity must have a label' }

      return null
    }
  }
}
