/**
 * :copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// create dummy angularJS app to attach filter(s)
var validationTestApp = angular.module('validationTestApp', ['mappingValidatorService']);

describe('The MappingValidatorService', function () {
  var mappingValidatorService;

  beforeEach(function () {
    module('validationTestApp');
    inject(function (_mappingValidatorService_) {
      mappingValidatorService = _mappingValidatorService_;
    });

  });

  it('validates good string, float and date data', function () {
    // normal cases
    // Here ``type`` is undefined. Should still work.
    var str_data = ['Fun', 'fun2', 'fun3', 'fun4'];
    var float_data = ['12.34', '144.5', '234'];
    var date_data = ['2014/02/02', '03/13/2013', '03-14-2004'];

    expect(mappingValidatorService.validate(str_data)).toEqual([]);
    expect(mappingValidatorService.validate(float_data, 'float')).toEqual([]);
    expect(mappingValidatorService.validate(date_data, 'date')).toEqual([]);
  });

  it('recognizes semivalid data', function () {
    // Cases where the data is /almost/ right.
    var float_data = ['12.34', '144.5', 'NaN'];
    var date_data = ['2014/02/02', 'huh?', '03-14-2004'];
    expect(mappingValidatorService.validate(float_data, 'float')).toEqual(['NaN']);
    expect(mappingValidatorService.validate(date_data, 'date')).toEqual(['huh?']);
  });

  it('recognizes invalid data', function () {
    // Cases where the data is *all* wrong.
    var float_data = ['', 'not a float', 'NaN'];
    var date_data = ['', 'huh?', 'what?'];
    // Cases where the data are correct.
    var good_float_data = ['12.34', '144.5', '234'];
    var good_date_data = ['2014/02/02', '03/13/2013', '03-14-2004'];

    // Data is wrong
    expect(mappingValidatorService.validate(float_data, 'float')).toEqual(float_data);
    expect(mappingValidatorService.validate(date_data, 'date')).toEqual(date_data);

    // Type is wrong
    // N.B. we use semivalid here, because Date is pretty forgiving w/ nums.
    expect(mappingValidatorService.validate(good_float_data, 'date')).toEqual(['12.34']);
    expect(mappingValidatorService.validate(good_date_data, 'float')).toEqual(good_date_data);


  });

});

