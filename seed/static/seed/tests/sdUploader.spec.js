/*
 * :copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// taken from the angularjs testing page
// http://docs.angularjs.org/guide/dev_guide.unit-testing

// create dummy angularJS app to attach filter(s)
var mySDUploaderDirectiveApp = angular.module('mySDUploaderDirectiveApp', ['sdUploader']);

describe("The sdUploader directive", function() {
    var g_message, g_file, g_progress;
    var $compile;
    var $rootScope;
    var uploader_html = '<div sd-uploader sourcetype="assessor" importrecord="5" buttontext="Upload your building list .csv file" eventfunc="uploaderfunc(message, filename, progress)" ng-hide="uploader.in_progress"></div>';
    beforeEach(module('mySDUploaderDirectiveApp'));
    // Store references to $rootScope and $compile
    // so they are available to all tests in this describe block
    beforeEach(inject(function(_$compile_, _$rootScope_){
      // The injector unwraps the underscores (_) from around the parameter names when matching
      $compile = _$compile_;
      $rootScope = _$rootScope_;
      $rootScope.eventfunc = function (fine_object) {
        console.log({fin: fine_object});
        g_message = fine_object.message;
        g_file = fine_object.file;
        g_progress = fine_object.progress;
      };
      window.BE = window.BE || {};
      window.BE.FILE_UPLOAD_DESTINATION = 'S3';
    }));

    it('Creates the fineuploader element', function() {
        // arrange
        var element = $compile(uploader_html)($rootScope);
        
        // act
        $rootScope.$digest();

        // assert
        expect(element.html()).toContain("qq-uploader");
        expect(element.html()).toContain("qq-upload-button");
    });

    it('Contains the buttontext specified', function() {
        // arrange
        var element = $compile(uploader_html)($rootScope);

        // act
        $rootScope.$digest();

        // assert
        expect(element.html()).toContain("Upload your building list .csv file");
    });

    it('Only allows one file to be uploaded at a time', function() {
        // arrange
        var element = $compile(uploader_html)($rootScope);
        var func = sdUploaderFineUploader($rootScope, element, "", "test_file.csv");

        // act
        $rootScope.$digest();

        // assert
        expect(func._options.multiple).toBe(false);
    });

    it('Uses the callback function for invalid file types', function() {
        // arrange
        var element = $compile(uploader_html)($rootScope);
        var func = sdUploaderFineUploader($rootScope, element, "", "test_file.jpeg");

        // act
        $rootScope.$digest();
        func._options.showMessage("there was an invalid extension. Valid extension(s): .csv");


        // assert
        expect(g_message).toBe("invalid_extension");
    });

    it('Uses the callback function to share its state: upload started',
        function() {
        // arrange
        var element = $compile(uploader_html)($rootScope);
        var func = sdUploaderFineUploader($rootScope, element, "", "test_file.csv");
        var filename = 'test_file.csv';
        
        // act
        $rootScope.$digest();
        func._options.callbacks.onSubmitted(1, filename);


        // assert
        expect(g_message).toBe("upload_submitted");
        expect(g_file.filename).toBe(filename);
    });

    it('Uses the callback function to share its state: in progress',
        function() {
        // arrange
        var element = $compile(uploader_html)($rootScope);
        var func = sdUploaderFineUploader($rootScope, element, "", "test_file.csv");
        var filename = 'test_file.csv';
        var loaded = 10;
        var total = 100;
        
        // act
        $rootScope.$digest();
        func._options.callbacks.onProgress(1, filename, loaded, total);


        // assert
        expect(g_message).toBe("upload_in_progress");
        expect(g_file.filename).toBe(filename);
        expect(g_progress.loaded).toBe(loaded);
        expect(g_progress.total).toBe(total);
    });

    it('Uses the callback function to share its state: complete',
        function() {
        // arrange
        var element = $compile(uploader_html)($rootScope);
        var func = sdUploaderFineUploader($rootScope, element, "", "test_file.csv");
        var filename = 'test_file.csv';

        
        // act
        $rootScope.$digest();
        func._options.callbacks.onComplete(1, filename, {success: true});


        // assert        
        expect(g_message).toBe("upload_complete");
        expect(g_file.filename).toBe(filename);
    });

});
