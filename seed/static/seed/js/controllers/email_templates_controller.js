/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.email_templates', []).controller('email_templates_controller', [
  '$scope',
  '$filter',
  'auth_payload',
  'organization_payload',
  'postoffice_service',
  'templates_payload',
  'current_template',
  '$uibModal',
  'urls',
  'modified_service',
  'flippers',
  '$translate',
  'i18nService',
  'Notification',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $filter,
    auth_payload,
    organization_payload,
    postoffice_service,
    templates_payload,
    current_template,
    $uibModal,
    urls,
    modified_service,
    flippers,
    $translate,
    i18nService,
    Notification
  ) {
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;
    $scope.canceled = false;

    $scope.available_templates = templates_payload;
    $scope.selected_template = current_template;

    // temp data is what's actually on the page, before writing it to the actual template obj
    if ($scope.selected_template) {
      $scope.temp = {
        subject: $scope.selected_template.subject,
        html_content: $scope.selected_template.html_content
      };
    } else {
      $scope.selected_template = null;
      $scope.temp = {
        subject: '',
        html_content: ''
      };
    }

    $scope.saveTemplate = () => {
      if (!$scope.selected_template) {
        // if no template exists, asks user to create one first
        const modalInstance = $uibModal.open({
          templateUrl: `${urls.static_url}seed/partials/email_templates_modal.html`,
          controller: 'email_templates_modal_controller',
          resolve: {
            action: () => 'new',
            data: () => $scope.selected_template,
            org_id: $scope.org.id
          }
        });
        modalInstance.result.then((newTemplate) => {
          Notification.primary(`Created ${newTemplate.name}`);

          newTemplate.subject = $scope.temp.subject;
          newTemplate.html_content = $scope.temp.html_content;
          newTemplate.content = $filter('htmlToPlainText')(newTemplate.html_content);

          $scope.available_templates.push(newTemplate);
          $scope.selected_template = $scope.available_templates[0]; // no need to search

          const { id } = newTemplate;
          postoffice_service.update_template(id, newTemplate, $scope.org.id);

          modified_service.resetModified();
          Notification.primary('Template saved');
        });
      } else {
        const { id } = $scope.selected_template;
        const newTemplate = _.omit($scope.selected_template, 'id');
        newTemplate.subject = $scope.temp.subject;
        $scope.selected_template.subject = newTemplate.subject;
        newTemplate.html_content = $scope.temp.html_content;
        $scope.selected_template.html_content = newTemplate.html_content;
        newTemplate.content = $filter('htmlToPlainText')(newTemplate.html_content);
        postoffice_service.update_template(id, newTemplate, $scope.org.id);

        modified_service.resetModified();
        Notification.primary('Template saved');
      }
    };

    $scope.renameTemplate = () => {
      const oldTemplate = angular.copy($scope.selected_template);
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/email_templates_modal.html`,
        controller: 'email_templates_modal_controller',
        resolve: {
          action: () => 'rename',
          data: () => $scope.selected_template,
          org_id: $scope.org.id
        }
      });
      modalInstance.result.then((newName) => {
        $scope.selected_template.name = newName;
        const originalIndex = _.findIndex($scope.available_templates, { name: $scope.selected_template.name });
        const newIndex = _.sortedIndexBy($scope.available_templates, $scope.selected_template, 'name');

        // reinsert template in dropdown according to new name
        $scope.available_templates.splice(originalIndex, 1);
        $scope.available_templates.splice(newIndex, 0, $scope.selected_template);

        Notification.primary(`Renamed ${oldTemplate.name} to ${newName}`);
      });
    };

    $scope.removeTemplate = () => {
      const oldTemplate = angular.copy($scope.selected_template);
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/email_templates_modal.html`,
        controller: 'email_templates_modal_controller',
        resolve: {
          action: () => 'remove',
          data: () => $scope.selected_template,
          org_id: $scope.org.id
        }
      });
      modalInstance.result.then(() => {
        _.remove($scope.available_templates, oldTemplate);
        modified_service.resetModified();
        $scope.selected_template = _.first($scope.available_templates);
        if (!$scope.selected_template) {
          $scope.temp.html_content = '';
          $scope.temp.subject = '';
        }
        Notification.primary(`Removed ${oldTemplate.name}`);
      });
    };

    $scope.newTemplate = () => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/email_templates_modal.html`,
        controller: 'email_templates_modal_controller',
        resolve: {
          action: () => 'new',
          data: () => $scope.selected_template,
          org_id: $scope.org.id
        }
      });
      modalInstance.result.then((newTemplate) => {
        const index = _.sortedIndexBy($scope.available_templates, newTemplate, 'name');
        $scope.available_templates.splice(index, 0, newTemplate);
        modified_service.resetModified();
        $scope.selected_template = $scope.available_templates[index];
        Notification.primary(`Created ${newTemplate.name}`);
        return newTemplate;
      });
    };

    $scope.$watch('selected_template', (newTemplate, oldTemplate) => {
      if (!newTemplate || !oldTemplate || newTemplate.id === oldTemplate.id) {
        return;
      }
      if (!modified_service.isModified() && !$scope.canceled) {
        $scope.temp.html_content = newTemplate.html_content;
        $scope.temp.subject = newTemplate.subject;
        postoffice_service.save_last_template(newTemplate.id, $scope.org.id);
      } else if ($scope.canceled) {
        $scope.canceled = false;
        modified_service.setModified();
      } else {
        modified_service.resetModified();
        $uibModal
          .open({
            template:
              '<div class="modal-header"><h3 class="modal-title" translate>You have unsaved changes</h3></div><div class="modal-body" translate>You will lose your unsaved changes if you switch templates without saving. Would you like to continue?</div><div class="modal-footer"><button type="button" class="btn btn-warning"' +
              ' ng-click="$close()" translate>Cancel</button><button type="button" class="btn btn-primary" ng-click="$dismiss()" autofocus translate>Switch Profiles</button></div>'
          })
          .result.then(() => {
            // Cancel
            modified_service.resetModified();
            $scope.canceled = true;
            $scope.selected_template = oldTemplate;
          })
          .catch(() => {
            // Switch
            $scope.temp.html_content = newTemplate.html_content;
            $scope.temp.subject = newTemplate.subject;
            postoffice_service.save_last_template(newTemplate.id, $scope.org.id);
            modified_service.resetModified();
          });
        modified_service.setModified();
      }
    });

    $scope.set_modified = () => {
      modified_service.setModified();
    };

    // updating modified
    $scope.isModified = () => modified_service.isModified();
  }
]);
