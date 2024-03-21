/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
// taken from the angularjs testing page
// http://docs.angularjs.org/guide/dev_guide.unit-testing

// create dummy angularJS app to attach filter(s)
const mySDUploaderDirectiveApp = angular.module('mySDUploaderDirectiveApp', ['sdUploader']);

describe('The sdUploader directive', () => {
  let g_message; let g_file; let
    g_progress;
  let $compile;
  let $rootScope;
  let $scope;
  const sdUploaderFineUploader = window.sdUploaderFineUploader;
  const uploader_html =
    '<div sd-uploader sourcetype="assessor" importrecord="5" buttontext="Upload your building list .csv file" eventfunc="uploaderfunc(message, filename, progress)" ng-hide="uploader.in_progress"></div>';
  beforeEach(() => {
    module('mySDUploaderDirectiveApp');
    inject((_$compile_, _$rootScope_) => {
      // The injector unwraps the underscores (_) from around the parameter names when matching
      $compile = _$compile_;
      $rootScope = _$rootScope_;
      $scope = $rootScope.$new();
      // Set up parent with cycle information
      $rootScope.selectedCycle = { id: 1 };
      $scope.eventfunc = function (fine_object) {
        // console.log({fin: fine_object});
        g_message = fine_object.message;
        g_file = fine_object.file;
        g_progress = fine_object.progress;
      };
      window.BE = window.BE || {};
    });
  });

  it('Creates the fineuploader element', () => {
    // arrange
    const element = $compile(uploader_html)($scope);

    // act
    $scope.$digest();

    // assert
    expect(element.html()).toContain('qq-button-id');
  });

  it('Only allows one file to be uploaded at a time', () => {
    // arrange
    const element = $compile(uploader_html)($scope);
    const func = sdUploaderFineUploader($scope, element, '', 'test_file.csv');

    // act
    $scope.$digest();

    // assert
    expect(func._options.multiple).toBe(false);
  });

  it('Uses the callback function to share its state: upload started', () => {
    // arrange
    const element = $compile(uploader_html)($scope);
    const func = sdUploaderFineUploader($scope, element, '', 'test_file.csv');
    const filename = 'test_file.csv';

    // act
    $scope.$digest();
    func._options.callbacks.onSubmitted(1, filename);

    // assert
    expect(g_message).toBe('upload_submitted');
    expect(g_file.filename).toBe(filename);
  });

  it('Uses the callback function to share its state: in progress', () => {
    // arrange
    const element = $compile(uploader_html)($scope);
    const func = sdUploaderFineUploader($scope, element, '', 'test_file.csv');
    const filename = 'test_file.csv';
    const loaded = 10;
    const total = 100;

    // act
    $scope.$digest();
    func._options.callbacks.onProgress(1, filename, loaded, total);

    // assert
    expect(g_message).toBe('upload_in_progress');
    expect(g_file.filename).toBe(filename);
    expect(g_progress.loaded).toBe(loaded);
    expect(g_progress.total).toBe(total);
  });

  it('Uses the callback function to share its state: complete', () => {
    // arrange
    const element = $compile(uploader_html)($scope);
    const func = sdUploaderFineUploader($scope, element, '', 'test_file.csv');
    const filename = 'test_file.csv';

    // act
    $scope.$digest();
    func._options.callbacks.onComplete(1, filename, { success: true });

    // assert
    expect(g_message).toBe('upload_complete');
    expect(g_file.filename).toBe(filename);
  });
});
