/*
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.pairing', []).controller('pairing_controller', [
  '$scope',
  '$log',
  'import_file_payload',
  '$window',
  '$uibModal',
  'inventory_service',
  'user_service',
  'pairing_service',
  'propertyInventory',
  'taxlotInventory',
  'cycles',
  '$http',
  '$state',
  '$stateParams',
  'spinner_utility',
  'dragulaService',
  function ($scope,
            $log,
            import_file_payload,
            $window,
            $uibModal,
            inventory_service,
            user_service,
            pairing_service,
            propertyInventory,
            taxlotInventory,
            cycles,
            $http,
            $state,
            $stateParams,
            spinner_utility,
            dragulaService) {
    spinner_utility.show();

    $scope.import_file = import_file_payload.import_file;
    $scope.inventory_type = $stateParams.inventory_type;
    $scope.selectedCount = 0;
    $scope.selectedParentCount = 0;

    $scope.showPaired = 'All';
    $scope.showPairedOptions = ['All', 'Show Paired', 'Show Unpaired'];

    $scope.propertyData = propertyInventory.results;
    $scope.taxlotData = taxlotInventory.results;
    $scope.allPropertyColumns = propertyInventory.columns;
    $scope.propertyColumns = _.reject(propertyInventory.columns, {name: 'jurisdiction_tax_lot_id'});
    $scope.taxlotColumns = taxlotInventory.columns;

    var allPropertyColumns = ['address_line_1', 'pm_property_id', 'custom_id_1'];
    var allTaxlotColumns = ['address_line_1', 'jurisdiction_tax_lot_id', 'not_a_real_key_placeholder_pairing'];

    // Data Maps to fill with 'createMap'
    $scope.propToTaxlot = {};
    $scope.propertyMap = {};
    $scope.taxlotMap = {};
    $scope.taxlotToProp = {};

    var lastCycleId = inventory_service.get_last_cycle();
    $scope.cycle = {
      selected_cycle: lastCycleId ? _.find(cycles.cycles, {id: lastCycleId}) : _.first(cycles.cycles),
      cycles: cycles.cycles
    };

    var refreshObjects = function () {
      var visiblePropertyColumns = _.map($scope.allPropertyColumns, 'name');
      var visibleTaxlotColumns = _.map($scope.taxlotColumns, 'name');
      return inventory_service.get_properties(1, undefined, $scope.cycle.selected_cycle, visiblePropertyColumns).then(function (properties) {
        $scope.propertyData = properties.results;
        return inventory_service.get_taxlots(1, undefined, $scope.cycle.selected_cycle, visibleTaxlotColumns).then(function (taxlots) {
          $scope.taxlotData = taxlots.results;
          createMap();
          $scope.updateLeftRight();
          spinner_utility.hide();
        });
      });
    };

    $scope.cycleChanged = function () {
      spinner_utility.show();
      inventory_service.save_last_cycle($scope.cycle.selected_cycle.id);
      refreshObjects();
    };

    $scope.inventoryTypeChanged = function () {
      $state.go('pairing', {
        importfile_id: $stateParams.importfile_id,
        inventory_type: $scope.inventory_type
      });
    };

    $scope.whichColumns = function (side) {
      if (side === 'left') {
        return $scope.inventory_type == 'properties' ? allPropertyColumns : allTaxlotColumns;
      } else {
        return $scope.inventory_type != 'properties' ? allPropertyColumns : allTaxlotColumns;
      }
    };

    $scope.whichChildren = function (row) {
      if ($scope.inventory_type == 'properties') {
        return $scope.taxlotToProp[row.taxlot_view_id];
      } else {
        // console.log('which row: ', row, $scope.propToTaxlot)
        return $scope.propToTaxlot[row.property_view_id];
      }
    };

    $scope.whichChildData = function (propId, col) {
      if ($scope.inventory_type == 'properties') {
        return $scope.propertyMap[propId][col];
      } else {
        // console.log('child: ', propId, $scope.taxlotMap)
        return $scope.taxlotMap[propId][col];
      }
    };

    $scope.unpairChild = function ($event) {
      $event.stopPropagation();
      var promise;
      var taxlotId;
      var propertyId;

      // console.log('target: ', $event.target)

      // call with PUT /api/v2/taxlots/1/unpair/?property_id=1&organization_id=1
      if ($scope.inventory_type == 'properties') {
        taxlotId = +$event.target.getAttribute('rightParentId');
        propertyId = +$event.target.getAttribute('viewId');
        promise = pairing_service.unpair_taxlot_from_property(propertyId, taxlotId);
      } else {
        taxlotId = +$event.target.getAttribute('viewId');
        propertyId = +$event.target.getAttribute('rightParentId');
        promise = pairing_service.unpair_property_from_taxlot(taxlotId, propertyId);
      }

      promise.then(function (data) {
        //if success remove from maps
        // console.log('data: ', data);
        if (data.status === 'success') {
          // console.log('tl: ', taxlotId);
          // console.log('prop: ', propertyId);
          _.pull($scope.taxlotToProp[taxlotId], propertyId);
          _.pull($scope.propToTaxlot[propertyId], taxlotId);
          if ($scope.taxlotToProp[taxlotId].length == 0) {
            // console.log('pulling: ', taxlotId)
            delete $scope.taxlotToProp[taxlotId];
          }
          if ($scope.propToTaxlot[propertyId].length == 0) {
            // console.log('pulling: ', propertyId)
            delete $scope.propToTaxlot[propertyId];
          }
        } else {
          $log.error('unable to unpair: ', propertyId, taxlotId);
        }
        // console.log('tTop after: ', $scope.taxlotToProp);
        // console.log('pTot after: ', $scope.propToTaxlot);
      });
    };

    var addTtoP = function (taxlotId, propertyId) {
      if (!$scope.taxlotToProp[+taxlotId]) {
        $scope.taxlotToProp[+taxlotId] = [];
      }
      if (!_.includes($scope.taxlotToProp[+taxlotId], +propertyId)) {
        $scope.taxlotToProp[+taxlotId].push(+propertyId);
      }
    };
    var addPtoT = function (taxlotId, propertyId) {
      if (!$scope.propToTaxlot[+propertyId]) {
        $scope.propToTaxlot[+propertyId] = [];
      }
      if (!_.includes($scope.propToTaxlot[+propertyId], +taxlotId)) {
        $scope.propToTaxlot[+propertyId].push(+taxlotId);
      }
    };
    var createMap = function () {
      _.forEach(_.keys($scope.propertyMap), function (key) {
        delete $scope.propertyMap[key];
      });
      _.forEach(_.keys($scope.taxlotMap), function (key) {
        delete $scope.taxlotMap[key];
      });
      _.forEach(_.keys($scope.propToTaxlot), function (key) {
        delete $scope.propToTaxlot[key];
      });
      _.forEach(_.keys($scope.taxlotToProp), function (key) {
        delete $scope.taxlotToProp[key];
      });
      $scope.propertyData.forEach(function (property) {
        // console.log('prop: ', property);
        // Create map of property IDs to objects
        $scope.propertyMap[property.property_view_id] = property;

        property.related.forEach(function (taxlot) {
          // Create array of all properties with id of their taxlots
          addTtoP(taxlot.taxlot_view_id, property.property_view_id);

          // Create array of all taxlots with id of their property
          addPtoT(taxlot.taxlot_view_id, property.property_view_id);
        });
      });

      // Create map of taxlot IDs to objects
      $scope.taxlotData.forEach(function (taxlot) {
        // console.log('tl: ', taxlot.taxlot_view_id);
        $scope.taxlotMap[taxlot.taxlot_view_id] = taxlot;
      });
    };


    $scope.leftPaired = function (row) {
      if ($scope.inventory_type != 'properties') {
        return $scope.taxlotToProp[row.taxlot_view_id] ? $scope.taxlotToProp[row.taxlot_view_id].length : false;
      } else {
        return $scope.propToTaxlot[row.property_view_id] ? $scope.propToTaxlot[row.property_view_id].length : false;
      }
    };

    $scope.leftNumUnpaired = function () {
      var count = 0;
      if ($scope.inventory_type == 'properties') {
        $scope.leftData.forEach(function (data) {
          count += $scope.propToTaxlot[data.property_view_id] && $scope.propToTaxlot[data.property_view_id].length > 0 ? 0 : 1;
        });
      } else {
        $scope.leftData.forEach(function (data) {
          count += $scope.taxlotToProp[data.taxlot_view_id] && $scope.taxlotToProp[data.taxlot_view_id].length > 0 ? 0 : 1;
        });
      }
      return count;
    };

    $scope.rightNumUnpaired = function () {
      var count = 0;
      if ($scope.inventory_type != 'properties') {
        $scope.rightData.forEach(function (data) {
          count += $scope.propToTaxlot[data.property_view_id] && $scope.propToTaxlot[data.property_view_id].length > 0 ? 0 : 1;
        });
      } else {
        $scope.rightData.forEach(function (data) {
          count += $scope.taxlotToProp[data.taxlot_view_id] && $scope.taxlotToProp[data.taxlot_view_id].length > 0 ? 0 : 1;
        });
      }
      return count;
    };

    $scope.getLeftData = function () {
      var newLeftData = [];
      var leftMap = $scope.inventory_type == 'properties' ? $scope.propToTaxlot : $scope.taxlotToProp;
      var leftId = $scope.inventory_type == 'properties' ? 'property_view_id' : 'taxlot_view_id';
      if ($scope.showPaired === 'All') {
        newLeftData = $scope.leftData;
      } else if ($scope.showPaired === 'Show Paired') {
        $scope.leftData.forEach(function (data) {
          // console.log('left: ', leftMap[data[leftId]])
          if (leftMap[data[leftId]] && leftMap[data[leftId]].length > 0) {
            newLeftData.push(data);
          }
        });
      } else {
        $scope.leftData.forEach(function (data) {
          if (leftMap[data[leftId]] == undefined || leftMap[data[leftId]].length == 0) {
            newLeftData.push(data);
          }
        });
      }
      // console.log('getLeftData', newLeftData)
      $scope.newLeftData = newLeftData;
    };

    $scope.getRightParentId = function (row) {
      if ($scope.inventory_type == 'properties') {
        // console.log('here: ', row.taxlot_view_id)
        return row.taxlot_view_id;
      } else {
        return row.property_view_id;
      }
    };

    $scope.getLeftParentId = function (row) {
      if ($scope.inventory_type !== 'properties') {
        return row.taxlot_view_id;
      } else {
        // console.log('here: ', row.property_view_id)
        return row.property_view_id;
      }
    };

    $scope.leftSearch = function (value) {
      //left and right filters, works with table flip
      for (var i = 0; i < $scope.leftColumns.length; i++) {
        if ($scope.leftColumns[i].searchText && value[$scope.leftColumns[i].name]) {
          var searchTextLower = $scope.leftColumns[i].searchText.toLowerCase();
          var leftColLower = value[$scope.leftColumns[i].name].toLowerCase();
          var isMatch = leftColLower.indexOf(searchTextLower) > -1;
          if (!isMatch) {
            return false;
          }
        } else if ($scope.leftColumns[i].searchText && !value[$scope.leftColumns[i].name]) {
          return false;
        }
      }
      return true;
    };

    $scope.rightSearch = function (value) {
      for (var i = 0; i < $scope.rightColumns.length; i++) {
        // console.log("RC V: " + value[$scope.rightColumns[i].name]);
        if ($scope.rightColumns[i].searchText && value[$scope.rightColumns[i].name]) {
          var searchTextLower = $scope.rightColumns[i].searchText.toLowerCase();
          var rightColLower = value[$scope.rightColumns[i].name].toLowerCase();
          var isMatch = rightColLower.indexOf(searchTextLower) > -1;
          if (!isMatch) {
            return false;
          }
        } else if ($scope.rightColumns[i].searchText && !value[$scope.rightColumns[i].name]) {
          return false;
        }
      }
      return true;
    };


    $scope.leftSortColumn = 'name';
    $scope.leftReverseSort = false;

    $scope.leftSortData = function (column) {
      // console.log("left: " + column);
      $scope.leftReverseSort = ($scope.leftSortColumn === column) ? !$scope.leftReverseSort : false;
      $scope.leftSortColumn = column;
    };

    $scope.leftGetSortClass = function (column) {
      // console.log("left: " + column)
      if ($scope.leftSortColumn === column) {
        return $scope.leftReverseSort ? 'arrow-down' : 'arrow-up';
      }
      return 'arrow-down';
    };

    $scope.rightSortColumn = 'name';
    $scope.rightReverseSort = false;

    $scope.rightSortData = function (column) {
      // console.log('right: ' + column);
      $scope.rightReverseSort = ($scope.rightSortColumn === column) ? !$scope.rightReverseSort : false;
      $scope.rightSortColumn = column;
    };

    $scope.rightGetSortClass = function (column) {
      // console.log('right: ' + column)
      if ($scope.rightSortColumn === column) {
        return $scope.rightReverseSort ? 'arrow-down' : 'arrow-up';
      }
      return 'arrow-down';
    };


    $scope.updateLeftRight = function () {
      if ($scope.inventory_type === 'properties') {
        $scope.rightData = $scope.taxlotData;
        $scope.leftData = $scope.propertyData;

        $scope.leftColumns = $scope.propertyColumns;
        $scope.rightColumns = $scope.taxlotColumns;
      } else {
        $scope.leftData = $scope.taxlotData;
        $scope.rightData = $scope.propertyData;

        $scope.leftColumns = $scope.taxlotColumns;
        $scope.rightColumns = $scope.propertyColumns;
      }
      $scope.getLeftData();
      // console.log('prop map: ', $scope.propToTaxlot);
      // console.log('tl map: ', $scope.taxlotToProp);
    };

    $scope.doubleClick = function (side, event) {
      // console.log('side: ', side, angular.element(event.currentTarget))
      if (side === 'left') {
        $scope.newElement = angular.element(event.currentTarget);
        $scope.$emit('drag-pairing-row.drag', angular.element(event.currentTarget));
      } else if (side === 'right') {
        $scope.$emit('drag-pairing-row.drop', $scope.newElement, {
          container: angular.element(event.currentTarget),
          fromClick: true
        });
      }

    };

    //Dragula stuff:
    dragulaService.options($scope, 'drag-pairing-row', {
      copy: true,
      copySortSource: false,
      moves: function (el, container) {
        // restrict dragging to designated handles
        return (container.className.indexOf('cant-move') === -1);
      },
      accepts: function (el, target) {
        //don't allow dropping in left column
        return (target.className.indexOf('pairing-data-left') === -1);
      }
    });

    $scope.$on('drag-pairing-row.drag', function (e, el) {
      // console.log('picked up e: ', e);
      // console.log('picked up el: ', el);
      // alert('you picked it up!');
      $scope.pickedUpEle = +el.children()[0].getAttribute('leftParentId');
    });

    $scope.$on('drag-pairing-row.drop', function (e, el, tempContainer) {
      var container;
      var fromClick;
      if (tempContainer.fromClick) {
        container = tempContainer.container;
        fromClick = tempContainer.fromClick;
      } else {
        container = tempContainer;
        fromClick = false;
      }
      // alert('you dropped it!');
      if (!el || !container) {
        return; //dropped in left side
      }
      if (!fromClick) {
        el.removeClass('grab-pairing-left');
        el.removeClass('pairing-data-row');
        // el.children.removeClass('pairing-data-row-col');
        // el.children.addClass('pairing-data-row-col-indent');
        el.addClass('pairing-data-row-indent');
        el.attr('ng-repeat', 'id in whichChildren(row) track by $index');
        el.parent().attr('style', '');
      }
      // console.log('el: ', el)
      // console.log('container: ', container)
      // console.log('ids: ', container[0].getAttribute('rightParentId'))
      // call with PUT /api/v2/taxlots/1/pair/?property_id=1&organization_id=1
      var promise;
      var taxlotId;
      var propertyId;
      if ($scope.inventory_type === 'properties') {
        taxlotId = +container[0].getAttribute('rightParentId');
        propertyId = $scope.pickedUpEle;
        promise = pairing_service.pair_taxlot_to_property($scope.pickedUpEle, +container[0].getAttribute('rightParentId'));
      } else {
        taxlotId = $scope.pickedUpEle;
        propertyId = +container[0].getAttribute('rightParentId');
        promise = pairing_service.pair_property_to_taxlot($scope.pickedUpEle, +container[0].getAttribute('rightParentId'));
      }

      promise.then(function (data) {
        if (data.status === 'success') {
          addTtoP(taxlotId, propertyId);
          addPtoT(taxlotId, propertyId);
          $scope.getLeftData();
          // $scope.$apply();
          // console.log('tTop: ', $scope.taxlotToProp);
          // console.log('pTot: ', $scope.propToTaxlot);
        } else {
          $log.error('unable to unpair: ', propertyId, taxlotId);
        }
      });

      if (!fromClick)
        el.remove();
    });

    // get data and Set left right data initially
    createMap();
    $scope.updateLeftRight();
    spinner_utility.hide();
  }]);
