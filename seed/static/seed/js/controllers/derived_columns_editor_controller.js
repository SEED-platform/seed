/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.derived_columns_editor', [])
  .controller('derived_columns_editor_controller', [
    '$scope',
    '$log',
    '$state',
    '$stateParams',
    'derived_columns_service',
    'Notification',
    'modified_service',
    'simple_modal_service',
    'spinner_utility',
    'auth_payload',
    'organization_payload',
    'derived_column_payload',
    'derived_columns_payload',
    'property_columns_payload',
    'taxlot_columns_payload',
    function (
      $scope,
      $log,
      $state,
      $stateParams,
      derived_columns_service,
      Notification,
      modified_service,
      simple_modal_service,
      spinner_utility,
      auth_payload,
      organization_payload,
      derived_column_payload,
      derived_columns_payload,
      property_columns_payload,
      taxlot_columns_payload
    ) {
      $scope.state = $state.current;
      // lazy - always ask user to confirm page change (unless they save / create the derived column)
      modified_service.setModified();

      // creates a new parameter object with a unique name
      const make_param = function () {
        // search for a parameter name that's not taken
        let char = 'a'.charCodeAt(0);
        let parameter_name = `param_${String.fromCharCode(char)}`;
        const existing_names = ($scope.parameters || []).map(param => param.parameter_name);

        while (existing_names.includes(parameter_name) && char < 'z'.charCodeAt(0)) {
          char += 1;
          parameter_name = `param_${String.fromCharCode(char)}`;
        }

        return {
          parameter_name,
          errors: {}
        };
      };

      // creates an initial derived column object
      // used when user is creating a new derived column rather than editing an existing one
      const make_derived_column = function () {
        const param = make_param();
        return {
          name: null,
          expression: `$${param.parameter_name} / 100`,
          inventory_type: $stateParams.inventory_type === 'properties' ? 'Property' : 'Tax Lot',
          parameters: [param]
        };
      };

      $scope.inventory_type_options = [
        'Property',
        'Tax Lot'
      ];

      $scope.auth = auth_payload.auth;
      $scope.org = organization_payload.organization;

      $scope.derived_column = derived_column_payload.derived_column || make_derived_column();
      $scope.parameters = $scope.derived_column.parameters;

      $scope.derived_columns = derived_columns_payload.derived_columns

      $scope.property_columns = property_columns_payload.filter(col => !col.related);
      $scope.taxlot_columns = taxlot_columns_payload.filter(col => !col.related);

      // turn each parameter's source_column (an ID to a Column) into an object
      // which includes the display name and add an empty array to for storing validation errors later
      $scope.parameters = $scope.parameters.map(param => {
        // if this parameter is 'new' (i.e., from make_param) it won't have a source column
        if (!param.source_column) {
          return {
            ...param,
            errors: {}
          };
        }

        const source_column = $scope.derived_column.inventory_type === 'Property' ?
          $scope.property_columns.find(col => col.id === param.source_column) :
          $scope.taxlot_columns.find(col => col.id === param.source_column);

        return {
          ...param,
          errors: {},
          source_column: {
            id: param.source_column,
            displayName: source_column ? source_column.displayName : '',
          }
        };
      });

      // updates parameter errors according to name validity
      const validate_parameter_name = function (parameter_index) {
        const this_param = $scope.parameters[parameter_index];
        // name is invalid if it doesn't follow Python variable naming conventions
        // or if it has the same name as another parameter
        this_param.errors.invalid_parameter_name = !/^[_a-zA-Z][_a-zA-Z0-9]*$/.test(this_param.parameter_name);
        this_param.errors.duplicate_parameter_name = $scope.parameters.some((param, idx) => {
          return param.parameter_name === this_param.parameter_name &&
            idx !== parameter_index;
        });

      };

      // updates parameter errors according to source column validity and check for duplicate
      const validate_parameter_source_column = function (parameter_index) {
        $scope.recursive_definition = false
        const this_param = $scope.parameters[parameter_index];
        this_param.errors.invalid_source_column = !this_param.source_column;

        if (!this_param.errors.invalid_source_column) {
          let other_source_column_ids = $scope.parameters.map(p => p.source_column ? p.source_column.id : -1);
          other_source_column_ids.splice(parameter_index, 1);

          this_param.errors.duplicate_source_column = other_source_column_ids.includes(this_param.source_column.id);
        } else {
          this_param.errors.duplicate_source_column = false;
        }

        this_param.errors.circular_source_column = check_for_circular_definition(this_param.source_column)
      };


      // Recursion exists when the source column (the definition) contains a reference to itself
      // a = b
      // b = a ----> b = b
      const check_for_circular_definition = function (source_column) {
        if (!source_column.derived_column) {
          return false
        } else if (source_column.derived_column == $scope.derived_column.id) {
          return true
        } else {
          let source_derived_column = $scope.derived_columns.find(dc => dc.id == source_column.derived_column)
          let nested_derived_columns = check_parameters_for_nested_derived_columns(source_derived_column.parameters)

          const current_column = property_columns_payload.find(col => col.derived_column == $scope.derived_column.id);
          // if the current column has been found in the definition of any of the source_column's nested derived columns, recursion has occurred.
          return nested_derived_columns.includes(current_column.id)
        }
      }
      const check_parameters_for_nested_derived_columns = function (params, nested_derived_column_ids = []) {
        params.forEach(param => {
          if (!param.source_column) {
            return
          }
          const source_col = property_columns_payload.find(col => col.id == param.source_column);
          // is source col a derived col?
          if (source_col.derived_column) {

            if (nested_derived_column_ids.includes(source_col.id)) {
              return nested_derived_column_ids
            }

            nested_derived_column_ids.push(source_col.id);

            const child_derived_col = $scope.derived_columns.find(dc => dc.id == source_col.derived_column)
            // use recursion to find all nested (related) derived columns
            check_parameters_for_nested_derived_columns(child_derived_col.parameters, nested_derived_column_ids)
          }
        });
        return nested_derived_column_ids
      }

      const validate_parameter_in_expression = function (parameter_index) {
        const this_param = $scope.parameters[parameter_index];
        if (this_param.errors.invalid_parameter_name) {
          this_param.errors.expression_missing_parameter = false;
        } else {
          const regex = new RegExp(`\\$${this_param.parameter_name}([^_a-zA-Z0-9]|$)`);
          this_param.errors.expression_missing_parameter = !regex.test($scope.derived_column.expression);
        }
      };

      $scope.update_parameter_errors = function () {
        $scope.parameters.forEach((_, idx) => {
          validate_parameter_name(idx);
          validate_parameter_source_column(idx);
          validate_parameter_in_expression(idx);
        });
      };

      $scope.update_expression_errors = function () {
        if (!$scope.derived_column.expression.trim()) {
          $scope.expression_error_message = 'Expression cannot be empty';
          return;
        }

        // check that there are no undeclared parameters in the expression
        const expression_parameter_names = [
          ...$scope.derived_column.expression.matchAll(/\$([_a-zA-Z][_a-zA-Z0-9]*)/g)
        ].map(match => match[1]);

        const declared_parameter_names = $scope.parameters.map(param => param.parameter_name);
        const undeclared_parameters = expression_parameter_names.filter(param_name => {
          return !declared_parameter_names.includes(param_name);
        });

        if (undeclared_parameters.length > 0) {
          $scope.expression_error_message = 'Expression includes references to undeclared parameters: '
            + `${undeclared_parameters.map(p => '"' + p + '"').join(', ')}. `
            + 'Please remove them before continuing';
        } else {
          $scope.expression_error_message = null;
        }
      };

      $scope.update_column_name_error = function () {
        $scope.duplicate_column_name = false;
        let applicableColumns = $scope.derived_column.inventory_type === 'Property' ? $scope.property_columns : $scope.taxlot_columns;
        if ($scope.derived_column.id) {
          // Exclude consideration of the derived column itself when verifying the name
          applicableColumns = applicableColumns.filter(col => col.derived_column !== $scope.derived_column.id)
        }

        if (applicableColumns.some(col => col.column_name === $scope.derived_column.name)) {
          $scope.duplicate_column_name = true;
        }

        $scope.invalid_column_name = !$scope.derived_column.name;
      };

      $scope.updated_parameter_or_expression = function () {
        $scope.update_parameter_errors();
        $scope.update_expression_errors();
      };

      $scope.updated_inventory_type = function () {
        const modalOptions = {
          type: 'default',
          okButtonText: 'Yes',
          cancelButtonText: 'Cancel',
          headerText: 'Are you sure?',
          bodyText: 'If you change the Type your current configuration will be reset. Would you like to continue?'
        };
        simple_modal_service.showModal(modalOptions).then(() => {
          //user confirmed, clear the params then generate a new one
          $scope.derived_column.name = '';
          $scope.parameters = [];
          $scope.parameters = [make_param()];
        }, () => {
          //user doesn't want to, switch back to the original inventory type
          $scope.derived_column.inventory_type = $scope.inventory_type_options.find(o => o !== $scope.derived_column.inventory_type);
        });
      };

      $scope.add_parameter = function () {
        $scope.parameters.push(make_param());
        $scope.updated_parameter_or_expression();
      };

      $scope.delete_parameter = function (parameter_index) {
        $scope.parameters.splice(parameter_index, 1);
        $scope.updated_parameter_or_expression();
      };

      $scope.any_errors = function () {
        const any_param_errors = $scope.parameters.some(param => {
          return Object.values(param.errors).some(v => v);
        });
        return (
          any_param_errors ||
          !!$scope.expression_error_message ||
          !!$scope.duplicate_column_name
        );
      };

      const update_all_errors = function () {
        $scope.updated_parameter_or_expression();
        $scope.update_column_name_error();
      };

      $scope.create_or_update_derived_column = function () {
        $scope.errors_from_server = null;

        update_all_errors();
        if ($scope.any_errors()) {
          return;
        }

        spinner_utility.show();

        const derived_column_data = {
          name: $scope.derived_column.name,
          expression: $scope.derived_column.expression,
          inventory_type: $scope.derived_column.inventory_type,
          parameters: $scope.parameters.map(param => {
            return {
              parameter_name: param.parameter_name,
              source_column: param.source_column.id,
            };
          })
        };

        const creating = !$scope.derived_column.id;
        let api_call = null;
        if (creating) {
          api_call = () => {
            return derived_columns_service.create_derived_column(
              $scope.org.id,
              derived_column_data
            );
          };
        } else {
          api_call = () => {
            return derived_columns_service.update_derived_column(
              $scope.org.id,
              $scope.derived_column.id,
              derived_column_data
            );
          };
        }

        api_call()
          .then(res => {
            spinner_utility.hide();
            modified_service.resetModified();
            Notification.success(`${creating ? 'Created' : 'Updated'} "${res.derived_column.name}"`);
            $state.go('organization_derived_columns', {organization_id: $scope.org.id, inventory_type: derived_column_data.inventory_type === 'Property' ? 'properties' : 'taxlots' });
          }).catch(err => {
            spinner_utility.hide();
            $log.error(err);
            if (err.data && err.data.errors) {
              $scope.errors_from_server = err.data.errors;
            } else {
              throw Error(`Something unexpectedly went wrong: ${err}`);
            }
          });
      };
    }
  ]);
