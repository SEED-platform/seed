/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
 * Directive sd-scroll-sync used for keeping the horizontal scrollbar in sync across multiple scrolling areas
 */
angular.module('sdScrollSync', []).directive('sdScrollSync', function () {
  var scrollLeft = 0;

  function combine (elements) {
    elements.on('scroll', function (e) {
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

  return {
    restrict: 'A',
    replace: false,
    compile: function (element, attrs) {
      combine(element.find('.' + attrs.sdScrollSync));
    }
  };
});
