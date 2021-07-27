/*
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.controller.derived_columns_editor', [])
  .controller('derived_columns_editor_controller', [
    '$scope',
    '$log',
    '$state',
    'derived_columns_service',
    'Notification',
    'modified_service',
    'simple_modal_service',
    'spinner_utility',
    'auth_payload',
    'organization_payload',
    'derived_column_payload',
    'property_columns_payload',
    'taxlot_columns_payload',
    function (
      $scope,
      $log,
      $state,
      derived_columns_service,
      Notification,
      modified_service,
      simple_modal_service,
      spinner_utility,
      auth_payload,
      organization_payload,
      derived_column_payload,
      property_columns_payload,
      taxlot_columns_payload,
    ) {
      // lazy - always ask user to confirm page change (unless they save / create the derived column)
      modified_service.setModified()

      // creates a new parameter object with a unique name
      const make_param = function() {
        // search for a parameter name that's not taken
        let char = 'a'.charCodeAt(0);
        let parameter_name = `param_${String.fromCharCode(char)}`;
        const existing_names = ($scope.parameters || []).map(param => param.parameter_name)

        while (existing_names.includes(parameter_name) && char < 'z'.charCodeAt(0)) {
          char += 1
          parameter_name = `param_${String.fromCharCode(char)}`
        }

        return {
          parameter_name,
          errors: {}
        }
      }

      // creates an initial derived column object
      // used when user is creating a new derived column rather than editing an existing one
      const make_derived_column = function() {
        const param = make_param()
        return {
          name: null,
          expression: `\$${param.parameter_name} / 100`,
          inventory_type: 'Property',
          parameters: [param]
        };
      }

      $scope.inventory_type_options = [
        'Property',
        'Tax Lot',
      ]

      $scope.auth = auth_payload.auth
      $scope.org = organization_payload.organization

      $scope.derived_column = derived_column_payload.derived_column || make_derived_column()
      $scope.parameters = $scope.derived_column.parameters

      $scope.property_columns = property_columns_payload.filter(col => !col.related)
      $scope.taxlot_columns = taxlot_columns_payload.filter(col => !col.related)

      // turn each parameter's source_column (an ID to a Column) into an object
      // which includes the display name and add an empty array to for storing validation errors later
      $scope.parameters = $scope.parameters.map(param => {
        // if this parameter is 'new' (ie from make_param) it won't have a source column
        if (!param.source_column) {
          return {
            ...param,
            errors: {}
          }
        }

        const source_column = $scope.derived_column.inventory_type == 'Property' ?
          $scope.property_columns.find(col => col.id == param.source_column) :
          $scope.taxlot_columns.find(col => col.id == param.source_column);

        return {
          ...param,
          errors: {},
          source_column: {
            id: param.source_column,
            displayName: source_column ? source_column.displayName : ''
          }
        }
      })

      // updates parameter errors according to name validity
      validate_parameter_name = function(parameter_index) {
        const this_param = $scope.parameters[parameter_index]
        // name is invalid if it doesn't follow Python variable naming conventions
        // or if it has the same name as another parameter
        this_param.errors.invalid_parameter_name = !/^[_a-zA-Z][_a-zA-Z0-9]*$/.test(this_param.parameter_name)
        this_param.errors.duplicate_parameter_name = $scope.parameters.some((param, idx) => {
          return param.parameter_name == this_param.parameter_name &&
            idx != parameter_index
        })
      }

      // updates parameter errors according to source column validity and check for duplicate
      validate_parameter_source_column = function(parameter_index) {
        const this_param = $scope.parameters[parameter_index]
        this_param.errors.invalid_source_column = !this_param.source_column

        if (!this_param.errors.invalid_source_column) {
          let other_source_column_ids = $scope.parameters.map(p => p.source_column ? p.source_column.id : -1)
          other_source_column_ids.splice(parameter_index, 1)

          this_param.errors.duplicate_source_column = other_source_column_ids.includes(this_param.source_column.id)
        } else {
          this_param.errors.duplicate_source_column = false
        }
      }

      validate_parameter_in_expression = function(parameter_index) {
        const this_param = $scope.parameters[parameter_index]
        if (this_param.errors.invalid_parameter_name) {
          this_param.errors.expression_missing_parameter = false;
        } else {
          const regex = new RegExp(`\\\$${this_param.parameter_name}([^_a-zA-Z0-9]|$)`)
          this_param.errors.expression_missing_parameter = !regex.test($scope.derived_column.expression)
        }
      }

      $scope.update_parameter_errors = function() {
        $scope.parameters.forEach((_, idx) => {
          validate_parameter_name(idx)
          validate_parameter_source_column(idx)
          validate_parameter_in_expression(idx)
        })
      }

      $scope.update_expression_errors = function() {
        if (!$scope.derived_column.expression.trim()) {
          $scope.expression_error_message = 'Expression cannot be empty'
          return
        }

        // check that there are no undeclared parameters in the expression
        const expression_parameter_names = [
          ...$scope.derived_column.expression.matchAll(/\$([_a-zA-Z][_a-zA-Z0-9]*)/g)
        ].map(match => match[1])

        const declared_parameter_names = $scope.parameters.map(param => param.parameter_name)
        const undeclared_parameters = expression_parameter_names.filter(param_name => {
          return !declared_parameter_names.includes(param_name)
        })

        if (undeclared_parameters.length > 0) {
          $scope.expression_error_message = `Expression includes references to undeclared parameters: `
            + `${undeclared_parameters.map(p => '"' + p + '"').join(', ')}. `
            + `Please remove them before continuing`
        } else {
          $scope.expression_error_message = null
        }
      }

      $scope.update_column_name_error = function() {
        if (!$scope.derived_column.name) {
          $scope.invalid_column_name = true
        } else {
          $scope.invalid_column_name = false
        }
      }

      $scope.updated_parameter_or_expression = function() {
        $scope.update_parameter_errors()
        $scope.update_expression_errors()
      }

      $scope.updated_inventory_type = function() {
        const modalOptions = {
          type: 'default',
          okButtonText: 'Yes',
          cancelButtonText: 'Cancel',
          headerText: 'Are you sure?',
          bodyText: 'If you change the Type your current parameters will be reset. Would you like to continue?'
        }
        simple_modal_service.showModal(modalOptions).then(() => {
          //user confirmed, clear the params then generate a new one
          $scope.parameters = []
          $scope.parameters = [make_param()]
        }, () => {
          //user doesn't want to, switch back to the original inventory type
          $scope.derived_column.inventory_type = $scope.inventory_type_options.find(o => o != $scope.derived_column.inventory_type)
        });
      }

      $scope.add_parameter = function() {
        $scope.parameters.push(make_param())
        $scope.updated_parameter_or_expression()
      }

      $scope.delete_parameter = function(parameter_index) {
        $scope.parameters.splice(parameter_index, 1)
        $scope.updated_parameter_or_expression()
      }

      $scope.any_errors = function() {
        const any_param_errors = $scope.parameters.some(param => {
          return Object.values(param.errors).some(v => v)
        })
        return (
          any_param_errors ||
          !!$scope.expression_error_message
        )
      }

      update_all_errors = function() {
        $scope.updated_parameter_or_expression()
        $scope.update_column_name_error()
      }

      $scope.create_or_update_derived_column = function() {
        $scope.errors_from_server = null

        update_all_errors()
        if ($scope.any_errors()) {
          return
        }

        spinner_utility.show()

        const derived_column_data = {
          name: $scope.derived_column.name,
          expression: $scope.derived_column.expression,
          inventory_type: $scope.derived_column.inventory_type,
          parameters: $scope.parameters.map(param => {
            return {
              parameter_name: param.parameter_name,
              source_column: param.source_column.id
            }
          }),
        }

        const creating = !$scope.derived_column.id
        let api_call = null
        if (creating) {
          api_call = () => {
            return derived_columns_service.create_derived_column(
              $scope.org.id,
              derived_column_data,
            )
          }
        } else {
          api_call = () => {
            return derived_columns_service.update_derived_column(
              $scope.org.id,
              $scope.derived_column.id,
              derived_column_data,
            )
          }
        }

        api_call()
          .then(res => {
            spinner_utility.hide()
            modified_service.resetModified()
            Notification.success(`${creating ? 'Created' : 'Updated'} "${res.derived_column.name}"`)
            $state.go('organization_derived_columns', {organization_id: $scope.org.id, inventory_type: 'properties'})
          }).catch(err => {
            spinner_utility.hide()
            $log.error(err)
            if (err.data && err.data.errors) {
              $scope.errors_from_server = err.data.errors
            } else {
              throw Error(`Something unexpectedly went wrong: ${err}`)
            }
          })
      }
    }
  ]);
