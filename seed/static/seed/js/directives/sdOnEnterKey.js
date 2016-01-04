/*
 * :copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * 	
 * Calls function defined in HTML input element when enter key is pressed for that element.
 */
 angular.module('sdOnEnterKey', []).directive('sdOnEnterKey', function() {
 	return {
 		restrict: 'A',
 		link: function($scope, $element, $attrs) {

 			$element.bind("keypress", function(event) {
 				if (event.keyCode == 13 ){
 					$scope.$apply(function() {
 						$scope.$eval($attrs.sdOnEnterKey, {$event: event});
 					});
 				}
 			});
 		}
 	};
 });