/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * see seed/ogbs/flipper.py ... usage and philosophy pretty much the same
 * bit minimum-usable right now .. just want this to squawk after it goes stale so as not to
 * forget about it.
 */
angular.module('BE.seed.service.flippers', []).factory('flippers', [
  '$log',
  ($log) => {
    const registry = {};
    const flippers = {};

    flippers.make_flipper = (owner, expires, label, kind, initial_value) => {
      const flipper = {};
      flipper.label = label;
      flipper[kind] = initial_value;
      flipper.expires = expires;
      flipper.owner = owner;

      registry[label] = flipper;
    };

    const is_stale = (flipper, now) => {
      if (!flipper.expires) return false;
      const expires = Date.parse(flipper.expires);
      return now > expires;
    };

    const log_stale_flipper = (flipper) => {
      // TODO throw someplace more useful; sentry?
      $log.warn(`Flipper '${flipper.label}' is stale; tell ${flipper.owner} to tidy up.`);
    };

    flippers.is_active = (s) => {
      const flipper = registry[s] || { boolean: false };
      if (is_stale(flipper, new Date())) log_stale_flipper(flipper);
      return flipper.boolean;
    };

    return flippers;
  }
]);
