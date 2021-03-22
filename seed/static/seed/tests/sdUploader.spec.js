/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// taken from the angularjs testing page
// http://docs.angularjs.org/guide/dev_guide.unit-testing

// create dummy angularJS app to attach filter(s)
var mySDUploaderDirectiveApp = angular.module('mySDUploaderDirectiveApp', ['sdUploader']);

describe('The sdUploader directive', function () {
  var g_message, g_file, g_progress;
  var $compile;
  var $rootScope;
  var $scope;
  var sdUploaderFineUploader = window.sdUploaderFineUploader;
  var uploader_html = '<div sd-uploader sourcetype="assessor" importrecord="5" buttontext="Upload your building list .csv file" eventfunc="uploaderfunc(message, filename, progress)" ng-hide="uploader.in_progress"></div>';
  beforeEach(function () {
    module('mySDUploaderDirectiveApp');
    inject(function (_$compile_, _$rootScope_) {
      // The injector unwraps the underscores (_) from around the parameter names when matching
      $compile = _$compile_;
      $rootScope = _$rootScope_;
      $scope = $rootScope.$new();
      // Set up parent with cycle information
      $rootScope.selectedCycle = {id: 1};
      $scope.eventfunc = function (fine_object) {
        // console.log({fin: fine_object});
        g_message = fine_object.message;
        g_file = fine_object.file;
        g_progress = fine_object.progress;
      };
      window.BE = window.BE || {};
    });
  });

  it('Creates the fineuploader element', function () {
    // arrange
    var element = $compile(uploader_html)($scope);

    // act
    $scope.$digest();

    // assert
    expect(element.html()).toContain('qq-button-id');
  });

  it('Only allows one file to be uploaded at a time', function () {
    // arrange
    var element = $compile(uploader_html)($scope);
    var func = sdUploaderFineUploader($scope, element, '', 'test_file.csv');

    // act
    $scope.$digest();

    // assert
    expect(func._options.multiple).toBe(false);
  });

  it('Uses the callback function to share its state: upload started', function () {
    // arrange
    var element = $compile(uploader_html)($scope);
    var func = sdUploaderFineUploader($scope, element, '', 'test_file.csv');
    var filename = 'test_file.csv';

    // act
    $scope.$digest();
    func._options.callbacks.onSubmitted(1, filename);


    // assert
    expect(g_message).toBe('upload_submitted');
    expect(g_file.filename).toBe(filename);
  });

  it('Uses the callback function to share its state: in progress', function () {
    // arrange
    var element = $compile(uploader_html)($scope);
    var func = sdUploaderFineUploader($scope, element, '', 'test_file.csv');
    var filename = 'test_file.csv';
    var loaded = 10;
    var total = 100;

    // act
    $scope.$digest();
    func._options.callbacks.onProgress(1, filename, loaded, total);


    // assert
    expect(g_message).toBe('upload_in_progress');
    expect(g_file.filename).toBe(filename);
    expect(g_progress.loaded).toBe(loaded);
    expect(g_progress.total).toBe(total);
  });

  it('Uses the callback function to share its state: complete', function () {
    // arrange
    var element = $compile(uploader_html)($scope);
    var func = sdUploaderFineUploader($scope, element, '', 'test_file.csv');
    var filename = 'test_file.csv';


    // act
    $scope.$digest();
    func._options.callbacks.onComplete(1, filename, {success: true});


    // assert
    expect(g_message).toBe('upload_complete');
    expect(g_file.filename).toBe(filename);
  });

});
