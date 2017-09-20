// see seed/ogbs/flipper.py ... usage and philosophy pretty much the same
// bit minimum-useable right now .. just want this to squawk after it goes stale so as not to
// forget about it.
angular.module('BE.seed.service.flippers', []).factory('flippers', [
  function () {

    var registry = {};
    var flippers = new Object();

    flippers.make_flipper = function (owner, expires, label, kind, initial_value) {
      var flipper = {};
      flipper.label = label;
      flipper[kind] = initial_value;
      flipper.expires = expires;
      flipper.owner = owner;

      registry[label] = flipper;
    };

    var is_stale = function (flipper, now) {
      if (!flipper.expires) return false;
      var expires = Date.parse(flipper.expires);
      return (now > expires);
    };

    var log_stale_flipper = function (flipper) {
      // TODO throw someplace more useful; raven? sentry?
      console.warn('Flipper \'' + flipper.label +
        '\' is stale; tell ' + flipper.owner + ' to tidy up.');
    };

    flippers.is_active = function (s) {
      var flipper = registry[s] || { 'boolean': false };
      if (is_stale(flipper, new Date())) log_stale_flipper(flipper);
      return flipper.boolean;
    };

    return flippers;
  }
]);
