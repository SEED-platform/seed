/**
 * Returns true if all characters in `input` appear in `target` in the same order (not necessarily consecutively).
 * Used for fuzzy matching like 'ac' matching 'abc' but not 'cab'.
 */
export const isOrderedSubset = (input: string, target: string): boolean => {
  let i = 0
  for (const char of target.toLowerCase()) {
    if (char === input[i]?.toLowerCase()) i++
    if (i === input.length) return true
  }
  return i === input.length
}
