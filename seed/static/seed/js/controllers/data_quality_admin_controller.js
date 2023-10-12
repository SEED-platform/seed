/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.data_quality_admin', []).controller('data_quality_admin_controller', [
  '$scope',
  '$q',
  '$state',
  '$stateParams',
  'Notification',
  'columns',
  'used_columns',
  'derived_columns_payload',
  'organization_payload',
  'data_quality_rules_payload',
  'auth_payload',
  'labels_payload',
  'data_quality_service',
  'modified_service',
  'organization_service',
  'label_service',
  'spinner_utility',
  '$uibModal',
  'urls',
  'naturalSort',
  '$translate',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $q,
    $state,
    $stateParams,
    Notification,
    columns,
    used_columns,
    derived_columns_payload,
    organization_payload,
    data_quality_rules_payload,
    auth_payload,
    labels_payload,
    data_quality_service,
    modified_service,
    organization_service,
    label_service,
    spinner_utility,
    $uibModal,
    urls,
    naturalSort,
    $translate
  ) {
    $scope.inventory_type = $stateParams.inventory_type;
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;
    $scope.ruleGroups = {};

    $scope.state = $state.current;
    $scope.rule_count_property = 0;
    $scope.rule_count_taxlot = 0;

    $scope.conditions = [
      { id: 'required', label: 'Required' },
      { id: 'not_null', label: 'Not Null' },
      { id: 'range', label: 'Range' },
      { id: 'include', label: 'Must Contain' },
      { id: 'exclude', label: 'Must Not Contain' }
    ];

    $scope.original_rules = angular.copy(data_quality_rules_payload);

    $scope.data_type_keys = {
      number: 0,
      string: 1,
      date: 2,
      year: 3,
      area: 4,
      eui: 5
    };

    $scope.data_types = [
      [
        { id: null, label: '' },
        { id: $scope.data_type_keys.string, label: $translate.instant('Text') }
      ],
      [
        { id: null, label: '' },
        { id: $scope.data_type_keys.number, label: $translate.instant('Number') },
        { id: $scope.data_type_keys.date, label: $translate.instant('Date') },
        { id: $scope.data_type_keys.year, label: $translate.instant('Year') },
        { id: $scope.data_type_keys.area, label: $translate.instant('Area') },
        { id: $scope.data_type_keys.eui, label: $translate.instant('EUI') }
      ],
      [
        { id: null, label: '' },
        { id: $scope.data_type_keys.number, label: $translate.instant('Number') },
        { id: $scope.data_type_keys.string, label: $translate.instant('Text') },
        { id: $scope.data_type_keys.date, label: $translate.instant('Date') },
        { id: $scope.data_type_keys.year, label: $translate.instant('Year') },
        { id: $scope.data_type_keys.area, label: $translate.instant('Area') },
        { id: $scope.data_type_keys.eui, label: $translate.instant('EUI') }
      ]
    ];

    $scope.severity_type_keys = {
      error: 0,
      warning: 1,
      valid: 2
    };

    $scope.severity_types = [
      { id: 0, label: $translate.instant('Error') },
      { id: 1, label: $translate.instant('Warning') },
      { id: 2, label: $translate.instant('Valid') }
    ];

    $scope.units = [
      { id: '', label: '' },
      { id: 'ft**2', label: 'square feet' },
      { id: 'm**2', label: 'square metres' },
      { id: 'kBtu/ft**2/year', label: 'kBtu/sq. ft./year' },
      { id: 'GJ/m**2/year', label: 'GJ/m²/year' },
      { id: 'MJ/m**2/year', label: 'MJ/m²/year' },
      { id: 'kWh/m**2/year', label: 'kWh/m²/year' },
      { id: 'kBtu/m**2/year', label: 'kBtu/m²/year' }
    ];

    $scope.columns = _.map(angular.copy(columns.filter((col) => !col.derived_column)), (col) => {
      if (!_.find(used_columns, ['id', col.id])) {
        col.group = 'Not Mapped';
      } else {
        col.group = 'Mapped Fields';
      }
      return col;
    });
    $scope.columns.push(
      ...derived_columns_payload.derived_columns.map((derived_column) => ({
        ...derived_column,
        data_type: $scope.data_type_keys.number,
        column_name: derived_column.name,
        displayName: derived_column.name,
        group: 'Derived',
        is_derived: true
      }))
    );

    $scope.all_labels = labels_payload;

    const loadRules = (rules_payload) => {
      const ruleGroups = {
        properties: {},
        taxlots: {}
      };
      let inventory_type;
      _.forEach(rules_payload, (rule) => {
        if (rule.table_name === 'PropertyState') {
          inventory_type = 'properties';
        } else if (rule.table_name === 'TaxLotState') {
          inventory_type = 'taxlots';
        } else {
          inventory_type = rule.table_name;
        }

        if (!_.has(ruleGroups[inventory_type], rule.field)) ruleGroups[inventory_type][rule.field] = [];
        const row = rule;
        if (row.data_type === $scope.data_type_keys.date) {
          if (row.min) row.min = moment(row.min, 'YYYYMMDD').toDate();
          if (row.max) row.max = moment(row.max, 'YYYYMMDD').toDate();
        }
        if (rule.status_label) {
          const match = _.find($scope.all_labels, (label) => label.id === rule.status_label);
          if (match) {
            row.label = match;
          }
        }
        ruleGroups[inventory_type][rule.field].push(row);
      });

      $scope.ruleGroups = ruleGroups;
      $scope.rule_count_property = 0;
      $scope.rule_count_taxlot = 0;
      _.map($scope.ruleGroups.properties, (rule) => {
        $scope.rule_count_property += rule.length;
      });
      _.map($scope.ruleGroups.taxlots, (rule) => {
        $scope.rule_count_taxlot += rule.length;
      });
    };
    loadRules(data_quality_rules_payload);

    $scope.isModified = () => modified_service.isModified();

    $scope.rules_changed = (rule) => {
      if (rule) rule.rule_type = 1;

      $scope.rules_reset = false;
      $scope.rules_updated = false;
      modified_service.setModified();
    };

    // Reset all rules
    $scope.reset_all_rules = () => modified_service.showResetDialog().then(() => {
      $scope.rules_reset = false;
      $scope.rules_updated = false;
      spinner_utility.show();
      return data_quality_service
        .reset_all_data_quality_rules($scope.org.org_id)
        .then(
          (rules) => {
            $scope.original_rules = angular.copy(rules);
            loadRules(rules);
            $scope.rules_reset = true;
            modified_service.resetModified();
          },
          (data) => {
            $scope.$emit('app_error', data);
          }
        )
        .finally(() => {
          spinner_utility.hide();
        });
    });

    // In order to save rules, the configured rules need to be reformatted.
    const get_configured_rules = () => {
      const rules = [];
      const misconfigured_rules = [];
      $scope.duplicate_rule_keys = [];
      _.forEach($scope.ruleGroups, (ruleGroups, inventory_type) => {
        _.forEach(ruleGroups, (ruleGroup) => {
          const duplicate_rules = _.groupBy(
            ruleGroup,
            (rule) => `${rule.condition}-${rule.field}-${rule.data_type}-${rule.min}-${rule.max}-${rule.text_match}-${rule.units}-${rule.severity}-${
              !_.isUndefined(rule.label) ? rule.label : rule.status_label
            }`
          );
          _.forEach(Object.keys(duplicate_rules), (key) => {
            if (duplicate_rules[key].length > 1) {
              _.forEach(duplicate_rules[key], (rule) => {
                $scope.duplicate_rule_keys.splice(0, 0, rule.$$hashKey);
              });
            }
          });
          _.forEach(ruleGroup, (rule) => {
            // Skip rules that haven't been assigned to a field yet
            if (rule.field === null) return;

            const column = _.find($scope.columns, { column_name: rule.field }) || {};
            const r = {
              enabled: rule.enabled,
              condition: rule.condition,
              field: rule.field,
              id: rule.id,
              data_type: rule.data_type,
              rule_type: rule.rule_type,
              required: rule.required,
              not_null: rule.not_null,
              min: rule.min,
              max: rule.max,
              table_name: inventory_type === 'properties' ? 'PropertyState' : 'TaxLotState',
              text_match: rule.text_match,
              severity: rule.severity,
              units: rule.units,
              status_label: null,
              for_derived_column: !!column.is_derived
            };
            if (rule.condition === 'not_null' || rule.condition === 'required') {
              r.min = null;
              r.max = null;
              r.text_match = null;
            }
            r.condition = rule.condition;

            if (rule.data_type === $scope.data_type_keys.date) {
              if (rule.min) r.min = Number(moment(rule.min).format('YYYYMMDD'));
              if (rule.max) r.max = Number(moment(rule.max).format('YYYYMMDD'));
            }
            if (rule.label) {
              r.status_label = rule.label.id;
            }
            if (rule.new) {
              rule.new = null;
              const match = _.find(labels_payload, (label) => label.name === rule.label);

              if (match) {
                r.label = match.id;
              }
            }
            if (!(r.min === '' || r.min === null) && !(r.max === '' || r.max === null)) {
              if (r.max < r.min) {
                const { min } = r;
                r.min = r.max;
                r.max = min;
              }
            }

            const include_or_exclude_without_text = (r.condition === 'include' || r.condition === 'exclude') && (r.text_match === null || r.text_match === '');
            const valid_severity_without_label = r.severity === $scope.severity_type_keys.valid && !r.status_label;
            if (include_or_exclude_without_text || valid_severity_without_label) {
              misconfigured_rules.push({
                rule,
                include_or_exclude_without_text,
                valid_severity_without_label
              });
            } else {
              rules.push(r);
            }
          });
        });
      });

      return [rules, misconfigured_rules];
    };

    // Capture misconfigured rule fields for UI indicators
    const init_misconfigured_fields_ref = () => {
      $scope.misconfigured_fields_ref = {
        condition: [],
        text_match: [],
        severity: [],
        label: []
      };
    };
    init_misconfigured_fields_ref();

    const show_configuration_errors = (misconfigured_rules) => {
      let include_or_exclude_without_text_count = 0;
      let valid_severity_without_label_count = 0;

      _.forEach(misconfigured_rules, (entry) => {
        if (entry.include_or_exclude_without_text) {
          include_or_exclude_without_text_count += 1;
          $scope.misconfigured_fields_ref.condition.push(entry.rule.$$hashKey);
          $scope.misconfigured_fields_ref.text_match.push(entry.rule.$$hashKey);
        }

        if (entry.valid_severity_without_label) {
          valid_severity_without_label_count += 1;

          $scope.misconfigured_fields_ref.severity.push(entry.rule.$$hashKey);
          $scope.misconfigured_fields_ref.label.push(entry.rule.$$hashKey);
        }
      });

      if (include_or_exclude_without_text_count) {
        Notification.error({
          message: `Must Contain and Must Not Contain rules cannot have empty text. Count: ${include_or_exclude_without_text_count}`,
          delay: 60000
        });
      }

      if (valid_severity_without_label_count) {
        Notification.error({
          message: `Rules with valid severity must have a label. Count: ${valid_severity_without_label_count}`,
          delay: 60000
        });
      }
    };

    $scope.save_settings = () => {
      // Clear notifications and misconfigured indicators in case there were any from previous save attempts.
      Notification.clearAll();
      init_misconfigured_fields_ref();
      $scope.is_duplicate = false;

      const [rules, misconfigured_rules] = get_configured_rules();
      const promises = [];

      if (misconfigured_rules.length) {
        show_configuration_errors(misconfigured_rules);
      }

      // Find duplicate rules and trigger warnings
      $scope.is_duplicate = $scope.duplicate_rule_keys.length > 1;
      if ($scope.is_duplicate) return Notification.error({ message: 'Duplicate rules detected.', delay: 10000 });

      // Find rules to delete
      _.forEach($scope.original_rules, (or) => {
        if (!_.find(rules, ['id', or.id]) && !_.find(misconfigured_rules, (m_rule) => m_rule.rule.id === or.id)) {
          promises.push(data_quality_service.delete_data_quality_rule($scope.org.id, or.id));
        }
      });

      // Find rules to update or create
      _.forEach(rules, (rule) => {
        const previous_copy = _.find($scope.original_rules, ['id', rule.id]);

        if (!previous_copy) {
          promises.push(data_quality_service.create_data_quality_rule($scope.org.id, rule));
        } else if (!_.isMatch(previous_copy, rule)) {
          promises.push(data_quality_service.update_data_quality_rule($scope.org.id, rule.id, rule));
        }
      });

      if (!promises.length) {
        return Notification.error({ message: 'No changes made.', delay: 10000 });
      }

      spinner_utility.show();
      $q.all(promises)
        .then(() => {
          data_quality_service.data_quality_rules($scope.org.id).then((updated_rules) => {
            $scope.original_rules = angular.copy(updated_rules);
            loadRules(updated_rules);
          });
          modified_service.resetModified();
        })
        .then((data) => {
          $scope.rules_updated = true;
          $scope.$emit('app_success', data);
        })
        .catch((data) => {
          // If we aren't preventing misconfigured_rules from sending requests
          // this needs to be updated to await all requests and display error messages afterwards.
          $scope.$emit('app_error', data);
        })
        .finally(() => {
          $scope.rules_updated = true;
          spinner_utility.hide();
        });
    };

    // check that contradictory conditions aren't being used in any Rule Group
    $scope.invalid_conditions = [];

    $scope.validate_conditions = (group, group_name) => {
      const conditions = _.map(group, 'condition');
      if (conditions.includes('range') && (conditions.includes('include') || conditions.includes('exclude'))) {
        $scope.invalid_conditions = _.union($scope.invalid_conditions, [group_name]);
      } else if ($scope.invalid_conditions.includes(group_name)) {
        _.pull($scope.invalid_conditions, group_name);
      }
    };

    // check that data_types are aligned in any Rule Group
    $scope.invalid_data_types = [];

    $scope.validate_data_types = (group, group_name) => {
      const data_types = _.uniq(_.map(group, 'data_type'));
      const conditions = _.map(group, 'condition');

      const range_has_text = conditions.includes('range') && data_types.includes($scope.data_type_keys.string);
      const numeric_types = _.map($scope.data_types[1], 'id');
      const include_has_numeric = conditions.includes('include') && _.intersection(data_types, numeric_types).length > 0;
      const exclude_has_numeric = conditions.includes('exclude') && _.intersection(data_types, numeric_types).length > 0;
      const invalid_condition_data_type_combinations = range_has_text || include_has_numeric || exclude_has_numeric;

      if (data_types.length > 1 || invalid_condition_data_type_combinations) {
        $scope.invalid_data_types = _.uniq(_.concat($scope.invalid_data_types, group_name));
      } else if ($scope.invalid_data_types.includes(group_name)) {
        _.pull($scope.invalid_data_types, group_name);
      }
    };

    // perform checks on load
    _.forEach($scope.ruleGroups[$scope.inventory_type], (group, group_name) => {
      $scope.validate_data_types(group, group_name);
      $scope.validate_conditions(group, group_name);
    });

    $scope.change_condition = (rule) => {
      $scope.rules_updated = false;
      $scope.rules_reset = false;
      if (rule.condition === 'include' || (rule.condition === 'exclude' && rule.data_type !== $scope.data_type_keys.string)) rule.data_type = $scope.data_type_keys.string;
      if (_.isMatch(rule, { condition: 'range', data_type: $scope.data_type_keys.string })) rule.data_type = null;
      if (
        _.isMatch(rule, { condition: 'not_null', data_type: $scope.data_type_keys.string }) ||
        _.isMatch(rule, {
          condition: 'required',
          data_type: $scope.data_type_keys.string
        })
      ) rule.text_match = null;
      if (rule.condition !== 'range') {
        rule.units = '';
        rule.min = null;
        rule.max = null;
      }

      const group_name = rule.field;
      const group = $scope.ruleGroups[$scope.inventory_type][group_name];
      $scope.validate_conditions(group, group_name);
      $scope.validate_data_types(group, group_name);
    };

    $scope.check_null = false;
    $scope.filter_null = (rule) => {
      $scope.check_null = rule.condition === 'not_null' || rule.condition === 'required';
      return $scope.check_null;
    };

    // capture rule field dropdown change.
    $scope.change_field = (rule, oldField, index) => {
      if (oldField === '') oldField = null;
      const original = rule.data_type;
      const newDataTypeString = _.find($scope.columns, { column_name: rule.field }).data_type;
      let newDataType = $scope.data_type_keys[newDataTypeString];

      if (_.isNil(newDataType)) newDataType = $scope.data_type_keys.number;
      // clear columns that are type specific.
      if (newDataType !== original) {
        rule.text_match = null;
        rule.units = '';

        if (![null, $scope.data_type_keys.number].includes(original) || ![null, $scope.data_type_keys.number].includes(newDataType)) {
          // Reset min/max if the data type is something other than null <-> number
          rule.min = null;
          rule.max = null;
        }
      }

      rule.data_type = newDataType;

      // move rule to appropriate spot in ruleGroups.
      if (!_.has($scope.ruleGroups[$scope.inventory_type], rule.field)) {
        $scope.ruleGroups[$scope.inventory_type][rule.field] = [];
      } else {
        // Rules already exist for the new field name, so match the data_type, required, and not_null columns
        const existingRule = _.first($scope.ruleGroups[$scope.inventory_type][rule.field]);
        rule.data_type = existingRule.data_type;
        rule.required = existingRule.required;
        rule.not_null = existingRule.not_null;
      }
      $scope.ruleGroups[$scope.inventory_type][rule.field].push(rule);
      // remove old rule.
      if ($scope.ruleGroups[$scope.inventory_type][oldField].length === 1) delete $scope.ruleGroups[$scope.inventory_type][oldField];
      else $scope.ruleGroups[$scope.inventory_type][oldField].splice(index, 1);
      rule.autofocus = true;

      const group_name = rule.field;
      const group = $scope.ruleGroups[$scope.inventory_type][group_name];
      $scope.validate_data_types(group, group_name);
      $scope.validate_conditions(group, group_name);

      $scope.validate_data_types($scope.ruleGroups[$scope.inventory_type][oldField], oldField);
      $scope.validate_conditions($scope.ruleGroups[$scope.inventory_type][oldField], oldField);
    };
    // Keep field types consistent for identical fields
    $scope.change_data_type = (rule, oldValue) => {
      const { data_type } = rule;
      const rule_group = $scope.ruleGroups[$scope.inventory_type][rule.field];

      _.forEach(rule_group, (currentRule) => {
        currentRule.text_match = null;

        if (!_.includes(['', $scope.data_type_keys.number], oldValue) || !_.includes([null, $scope.data_type_keys.number], data_type)) {
          // Reset min/max if the data type is something other than null <-> number
          currentRule.min = null;
          currentRule.max = null;
        }
        currentRule.data_type = data_type;
      });

      $scope.validate_data_types(rule_group, rule.field);
    };

    $scope.remove_label = (rule) => {
      rule.label = null;
    };

    // create a new rule.
    $scope.create_new_rule = () => {
      const field = null;
      if (!_.has($scope.ruleGroups[$scope.inventory_type], field)) {
        $scope.ruleGroups[$scope.inventory_type][field] = [];
      }
      $scope.ruleGroups[$scope.inventory_type][field].push({
        enabled: true,
        condition: '',
        field,
        displayName: field,
        data_type: $scope.data_type_keys.number,
        rule_type: 1,
        required: false,
        not_null: false,
        max: null,
        min: null,
        text_match: null,
        severity: $scope.severity_type_keys.error,
        units: '',
        // label: 'Invalid ' + label,
        label: null,
        new: true,
        autofocus: true
      });
      $scope.rules_changed();
      if ($scope.inventory_type === 'properties') $scope.rule_count_property += 1;
      else $scope.rule_count_taxlot += 1;
    };

    // create label and assign to that rule
    $scope.create_label = (rule) => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/data_quality_labels_modal.html`,
        controller: 'data_quality_labels_modal_controller',
        resolve: {
          org_id: () => $scope.org.org_id
        }
      });
      modalInstance.result
        .then((returnedLabel) => {
          rule.label = returnedLabel;
        })
        .finally(() => {
          // refresh labels
          label_service.get_labels_for_org($scope.org.org_id).then((labels) => {
            $scope.all_labels = labels;
          });
        });
    };

    // set rule as deleted.
    $scope.delete_rule = (rule, index) => {
      if ($scope.ruleGroups[$scope.inventory_type][rule.field].length === 1) {
        delete $scope.ruleGroups[$scope.inventory_type][rule.field];
      } else $scope.ruleGroups[$scope.inventory_type][rule.field].splice(index, 1);
      $scope.rules_changed();
      if ($scope.inventory_type === 'properties') $scope.rule_count_property -= 1;
      else $scope.rule_count_taxlot -= 1;
    };

    const displayNames = {};
    _.forEach($scope.columns, (column) => {
      // TRANSLATION_FIXME
      displayNames[column.column_name] = column.displayName;
    });

    $scope.sortedRuleGroups = () => {
      const sortedKeys = _.keys($scope.ruleGroups[$scope.inventory_type]).sort((a, b) => naturalSort(displayNames[a], displayNames[b]));
      const nullKey = _.remove(sortedKeys, (key) => key === 'null');

      // Put created unassigned rows first
      return nullKey.concat(sortedKeys);
    };

    $scope.selectAll = () => {
      $scope.rules_changed();

      const allEnabled = $scope.allEnabled();
      _.forEach($scope.ruleGroups[$scope.inventory_type], (ruleGroup) => {
        _.forEach(ruleGroup, (rule) => {
          rule.enabled = !allEnabled;
        });
      });
    };

    $scope.allEnabled = () => {
      let total = 0;
      const enabled = _.reduce(
        $scope.ruleGroups[$scope.inventory_type],
        (result, ruleGroup) => {
          total += ruleGroup.length;
          return result + _.filter(ruleGroup, 'enabled').length;
        },
        0
      );
      return total === enabled;
    };
  }
]);
