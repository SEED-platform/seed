/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.pairing', []).controller('pairing_controller', [
  '$scope',
  '$window',
  '$uibModal',
  'inventory_service',
  'user_service',
  'propertyInventory',
  'taxlotInventory',
  'cycles',
  '$http',
  'spinner_utility',
  'dragulaService',
  function ($scope,
            $window,
            $uibModal,
            inventory_service,
            user_service,
            propertyInventory,
            taxlotInventory,
            cycles,
            $http,
            spinner_utility,
            dragulaService) {
    spinner_utility.show();
    $scope.selectedCount = 0;
    $scope.selectedParentCount = 0;

    $scope.inventoryType = 'Property';
    $scope.inventoryOptions = ['Property', 'Tax Lot'];

    $scope.showPaired = 'All';
    $scope.showPairedOptions = ['All', 'Show Paired', 'Show Unpaired'];

    $scope.propertyData = propertyInventory.results;
    $scope.taxlotData = taxlotInventory.results;
    $scope.allPropertyColumns = propertyInventory.columns;
    $scope.propertyColumns = _.filter(propertyInventory.columns, function (o) {
      return o.name !== 'jurisdiction_tax_lot_id'
    });
    $scope.taxlotColumns = taxlotInventory.columns;

    var organization_id = user_service.get_organization().id;
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
      inventory_service.get_properties(1, undefined, $scope.cycle.selected_cycle, visiblePropertyColumns).then(function (properties) {
        $scope.propertyData = properties.results;
        $scope.updateLeftRight();
      });
      inventory_service.get_taxlots(1, undefined, $scope.cycle.selected_cycle, visibleTaxlotColumns).then(function (taxlots) {
        $scope.taxlotData = taxlots.results;
        $scope.updateLeftRight();
      });
    };

    $scope.updateCycle = function (cycle) {
      spinner_utility.show();
      inventory_service.save_last_cycle(cycle.id);
      $scope.cycle.selected_cycle = cycle;
      refreshObjects();
    };

    $scope.updateInventoryType = function () {
      spinner_utility.show();
      // console.log('inv: ', $scope.inventoryType)
      $scope.updateLeftRight();
      // console.log('pTot: ', $scope.propToTaxlot)
      // console.log('leftData: ', $scope.leftData)
    };

    $scope.whichColumns = function (side) {
      if (side === 'left') {
        return $scope.inventoryType === 'Property' ? allPropertyColumns : allTaxlotColumns;
      } else {
        return $scope.inventoryType !== 'Property' ? allPropertyColumns : allTaxlotColumns;
      }
    };

    $scope.whichChildren = function (row) {
      // console.log('row: ', row);
      if ($scope.inventoryType === 'Property') {
        return $scope.taxlotToProp[row.id]
      } else {
        return $scope.propToTaxlot[row.id]
      }
    };

    $scope.otherInventory = function () {
      if ($scope.inventoryType === 'Property') {
        return "Tax Lot"
      } else {
        return "Property"
      }
    };

    $scope.whichChildData = function (propId, col) {
      if ($scope.inventoryType === 'Property') {
        return $scope.propertyMap[propId][col]
      } else {
        return $scope.taxlotMap[propId][col]
      }
    };

    $scope.unpairChild = function ($event) {
      var ids = getIdsFromDOM(angular.element($event.target.parentNode));

      // call with PUT /api/v2/taxlots/1/unpair/?property_id=1&organization_id=1
      if ($scope.inventoryType === 'Property') {
        var url = '/api/v2/taxlots/' + ids.taxlotId + '/unpair/?property_id=' + ids.propertyId + '&organization_id=' + organization_id;
      } else {
        var url = '/api/v2/properties/' + ids.propertyId + '/unpair/?taxlot_id=' + ids.taxlotId + '&organization_id=' + organization_id;
      }

      $http.put(url, {}).then(function (response) {
        //if success remove from maps
        _.pull($scope.taxlotToProp[ids.taxlotId], ids.propertyId);
        _.pull($scope.propToTaxlot[ids.propertyId], ids.taxlotId);
        // console.log('tTop: ', $scope.taxlotToProp)
        // console.log('pTot: ', $scope.propToTaxlot)
      }).catch(function (response) {
        console.error(response);
      });
    };

    var addTtoP = function (taxlotId, propertyId) {
      if (!$scope.taxlotToProp[+taxlotId]) {
        $scope.taxlotToProp[+taxlotId] = [];
      }
      if (!_.includes($scope.taxlotToProp[+taxlotId], +propertyId)) {
        $scope.taxlotToProp[+taxlotId].push(+propertyId)
      }
    };
    var addPtoT = function (taxlotId, propertyId) {
      if (!$scope.propToTaxlot[+propertyId]) {
        $scope.propToTaxlot[+propertyId] = [];
      }
      if (!_.includes($scope.propToTaxlot[+propertyId], +taxlotId)) {
        $scope.propToTaxlot[+propertyId].push(+taxlotId)
      }
    };
    var createMap = function () {
      $scope.propertyData.forEach(function (property) {
        // Create map of property IDs to objects
        $scope.propertyMap[property.id] = property;

        property.related.forEach(function (taxlot) {
          // Create array of all properties with id of their taxlots
          addTtoP(taxlot.id, property.id);

          // Create array of all taxlots with id of their property
          addPtoT(taxlot.id, property.id);
        })
      });

      // Create map of taxlot IDs to objects
      $scope.taxlotData.forEach(function (taxlot) {
        $scope.taxlotMap[taxlot.id] = taxlot;
      })
    };
    createMap();


    $scope.leftPaired = function (row) {
      if ($scope.inventoryType !== 'Property') {
        return $scope.taxlotToProp[row.id] ? $scope.taxlotToProp[row.id].length : false;
      } else {
        return $scope.propToTaxlot[row.id] ? $scope.propToTaxlot[row.id].length : false;
      }
    };

    $scope.leftNumUnpaired = function () {
      var count = 0;
      if ($scope.inventoryType === 'Property') {
        $scope.leftData.forEach(function (data) {
          count += $scope.propToTaxlot[data.id] && $scope.propToTaxlot[data.id].length > 0 ? 0 : 1;
        })
      } else {
        $scope.leftData.forEach(function (data) {
          count += $scope.taxlotToProp[data.id] && $scope.taxlotToProp[data.id].length > 0 ? 0 : 1;
        })
      }
      return count;
    };

    $scope.rightNumUnpaired = function () {
      var count = 0;
      if ($scope.inventoryType !== 'Property') {
        $scope.rightData.forEach(function (data) {
          count += $scope.propToTaxlot[data.id] && $scope.propToTaxlot[data.id].length > 0 ? 0 : 1;
        })
      } else {
        $scope.rightData.forEach(function (data) {
          count += $scope.taxlotToProp[data.id] && $scope.taxlotToProp[data.id].length > 0 ? 0 : 1;
        })
      }
      return count;
    };

    $scope.getLeftData = function () {
      var newLeftData = [];
      var leftMap = $scope.inventoryType === 'Property' ? $scope.propToTaxlot : $scope.taxlotToProp;
      if ($scope.showPaired === 'All') {
        newLeftData = $scope.leftData;
      } else if ($scope.showPaired === 'Show Paired') {
        $scope.leftData.forEach(function (data) {
          if (leftMap[data.id] && leftMap[data.id].length > 0) {
            newLeftData.push(data);
          }
        });
      } else {
        $scope.leftData.forEach(function (data) {
          if (leftMap[data.id] == undefined || leftMap[data.id].length == 0) {
            newLeftData.push(data);
          }
        });
      }
      // console.log('getLeftData', newLeftData)
      $scope.newLeftData = newLeftData;
    };

    var getIdsFromDOM = function (el) {
      var parentRow = el.scope().row;
      var parentId = parentRow.id;
      var parentAddr = parentRow.address_line_1;
      var parentNum = $scope.inventoryType === 'Property' ? parentRow.jurisdiction_tax_lot_id : parentRow.pm_property_id;
      var parentCus = parentRow.custom_id_1;
      var childAddr = el.children()[0].innerText.trim();
      var childNum = el.children()[1].innerText.trim();
      var childCus = el.children()[2].innerText.trim();
      // console.log('child, ',childAddr, childNum, childCus)
      // console.log('parent, ',parentAddr, parentNum, parentCus)

      var taxlotId;
      var propertyId;
      if ($scope.inventoryType === 'Property') {
        taxlotId = parentId;
        propertyId = _.findKey($scope.propertyMap, function (o) {
          return (o.address_line_1 == childAddr || o.pm_property_id == childNum || o.custom_id_1 == childCus)
        })
      } else {
        propertyId = parentId;
        taxlotId = _.findKey($scope.taxlotMap, function (o) {
          return (o.address_line_1 == childAddr || o.jurisdiction_tax_lot_id == childNum)
        })
      }
      return {'propertyId': +propertyId, 'taxlotId': +taxlotId};
    };

    $scope.leftSearch = function (value, index, array) {
      for (var i = 0; i < $scope.leftColumns.length; i++) {
        if ($scope.leftColumns[i].searchText && value[$scope.leftColumns[i].name]) {
          return value[$scope.leftColumns[i].name].indexOf($scope.leftColumns[i].searchText) > -1;
        }
      }
      return true;
    };
    $scope.rightSearch = function (value, index, array) {
      for (var i = 0; i < $scope.rightColumns.length; i++) {
        if ($scope.rightColumns[i].searchText && value[$scope.rightColumns[i].name]) {
          return value[$scope.rightColumns[i].name].indexOf($scope.rightColumns[i].searchText) > -1;
        }
      }
      return true;
    };

    $scope.updateLeftRight = function () {
      if ($scope.inventoryType === 'Property') {
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
      spinner_utility.hide();
    };
    // Set left right data initially
    $scope.updateLeftRight();

    //Dragula stuff:
    dragulaService.options($scope, 'drag-pairing-row', {
      copy: true,
      copySortSource: false,
      moves: function (el, container, handle) {
        // restrict dragging to designated handles
        return (container.className.indexOf('cant-move') === -1);
      },
      accepts: function (el, target, source, sibling) {
        //don't allow dropping in left column
        return (target.className.indexOf('pairing-data-left') === -1);
      }
    });

    $scope.$on('drag-pairing-row.drop', function (e, el) {
      if (!el.scope()) {
        return; //dropped in left side
      }
      el.removeClass('grab-pairing-left');
      el.removeClass('pairing-data-row');
      // el.children.removeClass('pairing-data-row-col');
      // el.children.addClass('pairing-data-row-col-indent');
      el.addClass('pairing-data-row-indent');
      el.attr('ng-repeat', 'id in whichChildren(row) track by $index');
      el.parent().attr('style', '');

      var ids = getIdsFromDOM(el);
      // call with PUT /api/v2/taxlots/1/pair/?property_id=1&organization_id=1
      if ($scope.inventoryType === 'Property') {
        var url = '/api/v2/taxlots/' + ids.taxlotId + '/pair/?property_id=' + ids.propertyId + '&organization_id=' + organization_id;
      } else {
        var url = '/api/v2/properties/' + ids.propertyId + '/pair/?taxlot_id=' + ids.taxlotId + '&organization_id=' + organization_id;
      }

      $http.put(url, {}).then(function (response) {
        addTtoP(ids.taxlotId, ids.propertyId);
        addPtoT(ids.taxlotId, ids.propertyId);
        $scope.getLeftData();
        // $scope.$apply();
        // console.log('tTop: ', $scope.taxlotToProp)
        // console.log('pTot: ', $scope.propToTaxlot)
      }).catch(function (response) {
        console.error(response);
      });

      el.remove();
    });

    spinner_utility.hide();
  }]);
