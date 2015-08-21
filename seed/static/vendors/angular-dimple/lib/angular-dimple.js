angular.module('angular-dimple', [
  'angular-dimple.graph',
  'angular-dimple.legend',
  'angular-dimple.x',
  'angular-dimple.y',
  'angular-dimple.r',
  'angular-dimple.line',
  'angular-dimple.bar',
  'angular-dimple.stacked-bar',
  'angular-dimple.area',
  'angular-dimple.stacked-area',
  'angular-dimple.scatter-plot',
  'angular-dimple.ring'
])

.constant('MODULE_VERSION', '0.0.1')

.value('defaults', {
  foo: 'bar'
});