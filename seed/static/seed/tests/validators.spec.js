/**
 * :copyright: (c) 2014 Building Energy Inc
 */
// create dummy angularJS app to attach filter(s)
var validationTestApp = angular.module(
    'validationTestApp', ['mappingValidatorService']
);

describe("The MappingValidatorService", function() {
    var mvs;

    beforeEach(function () {
        module("validationTestApp");
        inject(function (mappingValidatorService) {
            mvs = mappingValidatorService;

        });

    });

    it('validates good string, float and date data', function() {
        // normal cases
        // Here ``type`` is undefined. Should still work.
        var str_data = ['Fun', 'fun2', 'fun3', 'fun4'];
        var float_data = ['12.34', '144.5', '234'];
        var date_data = ['2014/02/02', '03/13/2013', '03-14-2004'];

        expect(mvs.validate(str_data)).toEqual([]);
        expect(mvs.validate(float_data, 'float')).toEqual([]);
        expect(mvs.validate(date_data, 'date')).toEqual([]);
    });

    it('recognizes semivalid data', function() {
        // Cases where the data is /almost/ right.
        var float_data = ['12.34', '144.5', 'NaN'];
        var date_data = ['2014/02/02', 'huh?', '03-14-2004'];
        expect(mvs.validate(float_data, 'float')).toEqual(['NaN']);
        expect(mvs.validate(date_data, 'date')).toEqual(['huh?']);
    });

    it('recognizes invalid data', function() {
        // Cases where the data is *all* wrong.
        var float_data = ['', 'not a float', 'NaN'];
        var date_data = ['', 'huh?', 'what?'];
        // Cases where the data are correct.
        var good_float_data = ['12.34', '144.5', '234'];
        var good_date_data = ['2014/02/02', '03/13/2013', '03-14-2004'];

        // Data is wrong
        expect(mvs.validate(float_data, 'float')).toEqual(float_data);
        expect(mvs.validate(date_data, 'date')).toEqual(date_data);

        // Type is wrong
        // N.B. we use semivalid here, because Date is pretty forgiving w/ nums.
        expect(mvs.validate(good_float_data, 'date')).toEqual(['12.34']);
        expect(mvs.validate(good_date_data, 'float')).toEqual(good_date_data);


    });

});

