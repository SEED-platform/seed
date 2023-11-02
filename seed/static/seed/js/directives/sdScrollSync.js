/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * Directive sd-scroll-sync used for keeping the horizontal scrollbar in sync across multiple scrolling areas
 */
angular.module('sdScrollSync', []).directive('sdScrollSync', () => {
  let scrollLeft = 0;

  return {
    restrict: 'A',
    replace: false,
    compile: (element, attrs) => {
      const elements = element.find(`.${attrs.sdScrollSync}`);

      elements.on('scroll', (e) => {
        if (e.isTrigger) {
          e.target.scrollLeft = scrollLeft;
        } else {
          scrollLeft = e.target.scrollLeft;
          elements.each(function () {
            if (!this.isEqualNode(e.target)) {
              $(this).trigger('scroll');
            }
          });
        }
      });
    }
  };
});
