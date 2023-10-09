/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * htmlToPlainText
 * Strips html tags from text
 */
angular.module('htmlToPlainText', []).filter(
  'htmlToPlainText',
  // eslint-disable-next-line func-names, prefer-arrow/prefer-arrow-functions, prefer-arrow-callback
  function () {
    return (html) => {
      const temp = document.createElement('div');
      temp.innerHTML = html;
      return temp.textContent; // Or return temp.innerText if you need to return only visible text. It's slower.
    };
  }
);
