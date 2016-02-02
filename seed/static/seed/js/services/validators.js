/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/*
 * Validation Libraries
 */
/*
 * Mapping Validator
 *
 * @originals - list of str, i.e. a row of CSV data.
 * @type - the data type that they're meant to be coerced into.
 *
 * @returns - a list of strings, all the values which didn't pass the validator.
 */
angular.module('mappingValidatorService', []).factory(
    'mappingValidatorService', function() {

        var validatorService = {};
        validatorService.validate = function(originals, type) {
            var invalid_date = "Invalid Date";

            var date_converter = function(item) {
                return new Date(item);
            };

            var date_validator = function(orig, converted) {
                return (
                    angular.isDate(converted) &&
                    converted.toString() !==
                    invalid_date
                );
            };

            var float_converter = function(item) {
                if (typeof(item) === 'string'){
                    item = item.replace(/[,$$]/g, '');
                }
                return Number(item);
            };

            var float_validator = function(orig, converted) {
                return (
                    angular.isNumber(converted) &&
                    !isNaN(converted) &&
                    orig !== ''
                );
            };

            var pass_converter = function(item) {
                return item;
            };

            var pass_validator = function() {
                return true;
            };

            var results = [];
            var converter = pass_converter;
            var validator = pass_validator;
            switch (angular.lowercase(type)) {
                case 'float':
                   validator = float_validator;
                   converter = float_converter;
                   break;
                case 'date':
                    validator = date_validator;
                    converter = date_converter;
                    break;
             }

            angular.forEach(originals, function(original) {
                var valid = validator(original, converter(original));
                if (!valid) {
                    results.push(original);
                }
            });

            // Returns a list of objects, each containing 'original' and 'valid'
            return results;
        };

        return validatorService;
});
