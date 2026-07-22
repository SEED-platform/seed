/**
 * SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 *
 * htmlToPlainText
 * Strips html tags from text
 */
angular.module('htmlToPlainText', []).filter(
  'htmlToPlainText',
  () => (html) => {
    const temp = document.createElement('div');
    temp.innerHTML = html;
    return temp.textContent; // Or return temp.innerText if you need to return only visible text. It's slower.
  }
);
