import type { Rule, UnitSymbols } from '@seed/api'

export class DataQualityUtils {
  private static _unitLookup = {
    'ft**2': 'ft²',
    'm**2': 'm²',
    'kBtu/ft**2/year': 'kBtu/ft²/yr',
    'gal/ft**2/year': 'gal/ft²/yr',
    'GJ/m**2/year': 'GJ/m²/yr',
    'MJ/m**2/year': 'MJ/m²/yr',
    'kWh/m**2/year': 'kWh/m²/yr',
    'kBtu/m**2/year': 'kBtu/m²/yr',
  }

  static getDisplayName(columnDisplayName: string, rule: Rule): string {
    return `${columnDisplayName} ${this.getCriteria(rule)}`
  }

  static getCriteria(rule: Rule): string {
    switch (rule.condition) {
      case 'not_null':
        return 'if null'
      case 'required':
        return 'if missing'
      case 'include':
        return `if it contains "${rule.text_match}"`
      case 'exclude':
        return `if it does not contain "${rule.text_match}"`
      case 'range':
        return this.getRangeText(rule)
      default:
        return rule.condition
    }
  }

  /*
   * builds a readable string for the range criteria
   * ex: "if greater than [ 100 ] ft²"
   * ex: "if % change across cycles is less than [ 100 ] ft²"
   */
  static getRangeText(rule: Rule): string {
    const { cross_cycle, min, max, data_type, severity, units } = rule
    const unitText = this._unitLookup[units as UnitSymbols] || ''
    const cycleText = cross_cycle ? 'if % change across cycles is' : 'if'
    const severityText = {
      range: severity === 2 ? 'inside' : 'outside',
      min: severity === 2 ? 'greater' : 'less',
      max: severity === 2 ? 'less' : 'greater',
    }

    if (min !== null && max !== null) {
      const minText = data_type === 2 ? this.formatDate(min) : min.toLocaleString()
      const maxText = data_type === 2 ? this.formatDate(max) : max.toLocaleString()
      return `${cycleText} ${severityText.range} [ ${minText} ] and [ ${maxText} ] ${unitText}`
    }

    if (min !== null) return `${cycleText} ${severityText.min} than [ ${min.toLocaleString()} ] ${unitText}`
    if (max !== null) return `${cycleText} ${severityText.max} than [ ${max.toLocaleString()} ] ${unitText}`

    return ''
  }

  static formatDate(dateYMD: number): string {
    const dateString = dateYMD.toString()
    const year = dateString.slice(0, 4)
    const month = dateString.slice(4, 6)
    const day = dateString.slice(6, 8)
    return `${month}/${day}/${year}`
  }
}
