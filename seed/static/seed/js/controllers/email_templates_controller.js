// /**
//  * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
//  * :author
//  */
// angular.module('BE.seed.controller.group', [])
//     .controller('group_controller', [
//     '$scope',
//     '$window',
//     //'$uibModalInstance',
//     '$stateParams',
//     '$uibModal',
//     'Notification',
//     //'organization_payload',
//     //'auth_payload',
//     // 'group_service',
//     // 'modified_service',
//     'inventory_service',
//     //'organization_service',
//     'user_service',
//     'urls',
//     //'all_columns',
//     // 'groups',
//     // 'current_group',
//     //'shared_fields_payload',
//     'flippers',
//     '$translate',
//     'i18nService', // from ui-grid
//     function (
//         $scope,
//         $window,
//         //$uibModalInstance,
//         $stateParams,
//         $uibModal,
//         Notification,
//         //organization_payload,
//         //auth_payload,
//         // group_service,
//         // modified_service,
//         inventory_service,
//         //organization_service,
//         user_service,
//         urls,
//         //all_columns,
//         // groups,
//         // current_group,
//         //shared_fields_payload,
//         flippers,
//         $translate,
//         i18nService
//     ) {
//         $scope.inventory_type = $stateParams.inventory_type;
//         $scope.groups = groups;
//         $scope.currentGroup = current_group;
//         /*
//         /*Switch groups.
//         var ignoreNextChange = true;
//         $scope.$watch('currentGroup', function (newProfile, oldProfile) {
//           if (ignoreNextChange) {
//             ignoreNextChange = false;
//             return;
//           }
//           if (!modified_service.isModified()) {
//             switchProfile(newProfile);
//           } else {
//             $uibModal.open({
//               template: '<div class="modal-header"><h3 class="modal-title" translate>You have unsaved changes</h3></div><div class="modal-body" translate>You will lose your unsaved changes if you switch groups without saving. Would you like to continue?</div><div class="modal-footer"><button type="button" class="btn btn-warning" ng-click="$dismiss()" translate>Cancel</button><button type="button" class="btn btn-primary" ng-click="$close()" autofocus translate>Switch groups</button></div>'
//             }).result.then(function () {
//               modified_service.resetModified();
//               switchProfile(newProfile);
//             }).catch(function () {
//               ignoreNextChange = true;
//               $scope.currentGroup = oldProfile;
//             });
//           }
//         });
//         /*Called by previous funct
//         function switchProfile (newProfile) {
//           ignoreNextChange = true;
//           if (newProfile) {
//             $scope.currentGroup = _.find($scope.groups, {id: newProfile.id});
//             group_service.save_last_profile(newProfile.id, $scope.inventory_type); //saves what youve been working on
//           } else {
//             $scope.currentGroup = undefined;
//           }
//           setColumnsForcurrentGroup();
//           initializeRowSelections();
//         }
//         // set up i18n
//         //
//         // let angular-translate be in charge ... need
//             // to feed the language-only part of its $translate setting into
//             // ui-grid's i18nService
//             var stripRegion = function (languageTag) {
//               return _.first(languageTag.split('_'));
//             };
//             i18nService.setCurrentLang(stripRegion($translate.proposedLanguage() || $translate.use()));
//             //$scope.showSharedBuildings = shared_fields_payload.show_shared_buildings;
//             //BUTTONS---------------------------------------------------------------------------------------------------------
//             /*IMPORTANT: Saving current profile
//             $scope.save_group = function () {
//               var id = $scope.currentGroup.id;
//               var group = _.omit($scope.currentGroup, 'id');
//               //profile.columns = currentColumns();
//               //IMPORTANT calling group_service to update, then does the following once thats done
//               group_service.update_group(id, group).then(function (updatedGroup) {
//                 var index = _.findIndex($scope.groups, {id: updatedGroup.id});
//                 $scope.groups[index] = updatedGroup;
//                 modified_service.resetModified(); //resets modified
//                 Notification.primary('Saved ' + $scope.currentGroup.name); //updated webpage
//               });
//             };
//             var ignoreNextChange = true;
//             $scope.$watch('currentGroup', function (newGroup) {
//               if (ignoreNextChange) {
//                 ignoreNextChange = false;
//                 return;
//               }
//               group_service.save_last_profile(newGroup.id, $scope.inventory_type);
//               spinner_utility.show();
//               $window.location.reload();
//             });*/

//             /*IMPORTANT: Rename current profile*/
//             $scope.rename_group = function () {
//                 var oldGroup = angular.copy($scope.currentGroup); //preserves old profile?

//                 var modalInstance = $uibModal.open({
//                     templateUrl: urls.static_url + 'seed/partials/group_modal.html',
//                     controller: 'group_modal_controller',
//                     resolve: {
//                         action: _.constant('rename'),
//                         data: _.constant($scope.currentGroup),
//                         //settings_location: _.constant('List View Settings'),
//                         org_id: function () {
//                             return user_service.get_organization().id;
//                         },
//                         inventory_type: function () {
//                             return $scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
//                         }
//                     }
//                 });

//                 modalInstance.result.then(function (newName) {
//                     $scope.currentGroup.name = newName;
//                     _.find($scope.groups, { id: $scope.currentGroup.id }).name = newName;
//                     Notification.primary('Renamed ' + oldGroup.name + ' to ' + newName);
//                 });
//             };


//             /*IMPORTANT: Remove profile*/
//             $scope.remove_group = function () {
//                 var oldGroup = angular.copy($scope.currentGroup);

//                 var modalInstance = $uibModal.open({
//                     templateUrl: urls.static_url + 'seed/partials/group_modal.html',
//                     controller: 'group_modal_controller',
//                     resolve: {
//                         action: _.constant('remove'),
//                         data: _.constant($scope.currentGroup),
//                         org_id: function () {
//                             return user_service.get_organization().id;
//                         },
//                         inventory_type: function () {
//                             return $scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
//                         }
//                     }
//                 });

//                 modalInstance.result.then(function () {
//                     _.remove($scope.groups, oldGroup);
//                     modified_service.resetModified();
//                     $scope.currentGroup = _.first($scope.groups);
//                     Notification.primary('Removed ' + oldGroup.name);
//                 });
//             };

//             /*IMPORTANT: new profile*/
//             $scope.new_group = function () {
//                 var modalInstance = $uibModal.open({ //creates an overlay window to enter a name into
//                     templateUrl: urls.static_url + 'seed/partials/group_modal.html',
//                     controller: 'group_modal_controller', //problem is in the modal controller!
//                     resolve: {
//                         action: _.constant('new'),
//                         data: _.constant(""), //logic data
//                         org_id: function () {
//                             return user_service.get_organization().id;
//                         },
//                         inventory_type: function () {
//                             return $scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot';
//                         }
//                     }
//             });
//             modalInstance.result.then(function (newGroup) {
//                 $scope.groups.push(newGroup);
//                 modified_service.resetModified();
//                 $scope.currentGroup = _.last($scope.groups);
//                 inventory_service.save_last_group(newGroup.id, $scope.inventory_type);
//                 Notification.primary('Created ' + newGroup.name);
//             });
//         };
//         //BUTTONS-------------------------------------------------------------------------------------------------------^^

//         $scope.profile_change = function () {
//             inventory_service.save_last_group($scope.currentGroup.id, $scope.inventory_type);
//         };
//         //updating modified
//         $scope.isModified = function () {
//             return modified_service.isModified();
//         };


//     }]);

angular.module('BE.seed.controller.email_templates', [])
  .controller('email_templates_controller', [
    '$scope', //from before
    'organization_payload',
    'postoffice_service',
//     '$uibModalInstance', //?
//     'action', //new_group
//     'group_service', //from before
//     'inventory_service', //from before
//     //'settings_location',
//     'inventory_type', //new_group
//     'data', //new_group
//     'org_id', //new_group
    function (
      $scope,
      organization_payload,
      postoffice_service,
//       $uibModalInstance,
//       action,
//       group_service,
//       inventory_service,
//       //settings_location,
//       inventory_type,
//       data,
//       org_id
    ) {
        $scope.org = organization_payload.organization;
        $scope.available_templates = [];
        postoffice_service.get_templates().then(function(templates){
          $scope.available_templates = templates;
        });
//         $scope.action = action;
//         $scope.data = data;
//         $scope.org_id = org_id;
//         //$scope.settings_location = settings_location;
//         $scope.inventory_type = inventory_type;

//         $scope.rename_group = function () {
//           if (!$scope.disabled()) {
//             var id = $scope.data.id;
//             var group = _.omit($scope.data, 'id');
//             group.name = $scope.newName;
//             group_service.update_group(id, group).then(function (result) {
//               $uibModalInstance.close(result.name);
//             }).catch(function () {
//               $uibModalInstance.dismiss();
//             });
//           }
//         };

//         $scope.remove_group = function () {
//           group_service.remove_group($scope.data.id).then(function () {
//             $uibModalInstance.close();
//           }).catch(function () {
//             $uibModalInstance.dismiss();
//           });
//         };

//         //referenced from column_mapping_preset_modal_controller
//         $scope.new_group = function () { //called when modal button clicked
//           if (!$scope.disabled()) {
//             group_service.new_group({
//               name: $scope.newName,
//               inventory_type: $scope.inventory_type,
//               organization: $scope.org_id
//             }).then(function (result) {
//               $uibModalInstance.close(result.data);
//             });
//           }
//         };

//         $scope.disabled = function () {
//           if ($scope.action === 'rename') {
//             return _.isEmpty($scope.newName) || $scope.newName === $scope.data.name;
//           } else if ($scope.action === 'new') {
//             return _.isEmpty($scope.newName);
//           }
//         };

//         $scope.cancel = function () {
//           $uibModalInstance.dismiss();
//         };
  }]);