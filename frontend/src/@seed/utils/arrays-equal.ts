export const arraysEqual = <T>(arr1: T[], arr2: T[]): boolean => {
  return arr1.length === arr2.length && arr1.every((item, index) => item === arr2[index])
}
