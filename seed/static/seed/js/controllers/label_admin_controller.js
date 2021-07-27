/*
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.controller.label_admin', [])
  .controller('label_admin_controller', [
    '$scope',
    '$log',
    'urls',
    'organization_payload',
    'labels_payload',
    'auth_payload',
    'label_service',
    'simple_modal_service',
    'Notification',
    '$translate',
    '$sce',
    function (
      $scope,
      $log,
      urls,
      organization_payload,
      labels_payload,
      auth_payload,
      label_service,
      simple_modal_service,
      notification,
      $translate,
      $sce
    ) {
      $scope.org = organization_payload.organization;
      $scope.auth = auth_payload.auth;

      $scope.available_colors = _.map(label_service.get_available_colors(), function (color) {
        // label is already used for danger, success, etc.
        return _.extend(color, {uiLabel: $translate.instant(color.color)});
      });
      $scope.labels = labels_payload;

      function initialize_new_label () {
        $scope.new_label = {color: 'gray', label: 'default', name: '', show_in_list: false};
      }

      $scope.showColor = function (label) {
        var selected = [];
        if(label.color) {
          selected = $filter('filter')($scope.available_colors, {value: label.color});
        }
        return selected.length ? selected[0].text : 'Not set';
      };




      /*  Take user input from New Label form and submit
        to service to create a new label. */
      $scope.submitNewLabelForm = function (form) {
        if (form.$invalid) {
          return;
        }
        label_service.create_label_for_org($scope.org.id, $scope.new_label).then(function () {
          get_labels();
          var msg = translateMessage('CREATED_LABEL_NAMED', {
            label_name: getTruncatedName($scope.new_label.name)
          });
          notification.primary(msg);
          initialize_new_label();
          form.$setPristine();
        }, function (message) {
          $log.error('Error creating new label.', message);
        });
      };


      /* Checks for existing label name for inline edit form.
        Form assumes function will return a string if there's an existing label */
      $scope.checkEditLabelBeforeSave = function (data, currentLabelName) {
        if (data === currentLabelName) {
          return;
        }
        if (data === undefined || data === '') {
          return 'Enter at least one character';
        }
        if(isLabelNameUsed(data)) {
          return 'That label name already exists';
        }
      };

      function isLabelNameUsed (newLabelName) {
        var len = $scope.labels.length;
        for (var index = 0;index < len;index++) {
          var label = $scope.labels[index];
          if (label.name === newLabelName) {
            return true;
          }
        }
        return false;
      }

      /* Submit edit when 'enter' is pressed */
      $scope.onEditLabelNameKeypress = function (e, form) {
        if (e.which === 13) {
          form.$submit();
        }
      };

      function translateMessage (msg, params) {
      // TODO XSS, discuss with Nick and Alex
        return $sce.getTrustedHtml($translate.instant(msg, params));
      }

      $scope.saveLabel = function (label, id, index) {
        //Don't update $scope.label until a 'success' from server
        angular.extend(label, {id: id});
        label_service.update_label_for_org($scope.org.id, label).then(function (data) {
          var msg = translateMessage('Label updated');
          notification.primary(msg);
          $scope.labels.splice(index, 1, data);
          $scope.label = data;
        }, function (message) {
          $log.error('Error saving label.', message);
        });
      };


      $scope.deleteLabel = function (label, index) {
        var modalOptions = {
          type: 'default',
          okButtonText: $translate.instant('OK'),
          cancelButtonText: $translate.instant('Cancel'),
          headerText: $translate.instant('Confirm delete'),
          bodyText: $translate.instant('DELETE_LABEL_AND_REMOVE', { label_name: label.name })
        };
        simple_modal_service.showModal(modalOptions).then(function () {
          //user confirmed delete, so go ahead and do it.
          label_service.delete_label_for_org($scope.org.id, label).then(function () {
            //server deleted label, so remove it locally
            $scope.labels.splice(index, 1);
            var msg = translateMessage('DELETED_LABEL_NAMED', {
              label_name: getTruncatedName(label.name)
            });
            notification.primary(msg);
          }, function (message) {
            $log.error('Error deleting label.', message);
          });
        }, function () {
          //user doesn't want to delete after all.
        });

      };



      function get_labels () {
        // gets all labels for an org user
        label_service.get_labels_for_org($scope.org.id).then(function (data) {
          // resolve promise
          $scope.labels = data;
        });
      }

      function getTruncatedName (name) {
        if (name && name.length > 20) {
          name = name.substr(0, 20) + '...';
        }
        return name;
      }

      initialize_new_label();

    }]);
