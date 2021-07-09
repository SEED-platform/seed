/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
 * htmlToPlainText
 * Strips html tags from text
 */
angular.module('htmlToPlainText', []).filter('htmlToPlainText', function () {

    return function(html) {
	    var temp = document.createElement('div');
	    temp.innerHTML = html;
	    return temp.textContent; // Or return temp.innerText if you need to return only visible text. It's slower.
    };

});
