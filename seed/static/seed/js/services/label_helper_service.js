/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// convert color to bootstrap 3.0 label and button class names
angular.module('BE.seed.services.label_helper', []).factory('label_helper_service',
  function() {
    return {
        lookup_label: function (color) {
            var lookup_colors = {
                'red': 'danger',
                'gray': 'default',
                'orange': 'warning',
                'green': 'success',
                'blue': 'primary',
                'light blue': 'info'
            };
            try {
                return lookup_colors[color];
            } catch (err) {
                console.log(err);
                return lookup_colors.white;
            }
        }
    };
});
