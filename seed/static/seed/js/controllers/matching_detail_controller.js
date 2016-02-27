/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.matching_detail', [])
.controller('matching_detail_controller', [
  '$scope',
  'building_services',
  'matching_service',
  function($scope, building_services, matching_service) {
    $scope.building = {};
    $scope.detail = $scope.detail || {};
    $scope.extra_matches = [];

    var save_match = function ( source, target, create ) {
        return building_services
            .save_match( source, target, create )
            .then( function ( data ) {
                $scope.update_number_matched();
                return create ? source : target;
            }
        );
    };
    $scope.filter_current_building = function (value, index) {
      var is_tip = false;
      if ($scope.tip) {
        is_tip = (value.id === $scope.tip.id);
      }
      return ((value !== $scope.building.id) && !is_tip);
    };
    var get_match_tree = function () {
        return matching_service
            .get_match_tree( $scope.building.id )
            .then( function ( data ) {
                $scope.tip = data.tip;
                $scope.detail.match_tree = data.coparents.map( function ( b ) {
                    b.matches_current = true;
                    return b;
                }).filter( function ( b ) {
                    if (b.id !== $scope.building.id) {
                        return b;
                    }
                });
                return data.match_tree;
            }
        );
    };
    var search_buildings = function ( match_tree ) {
        $scope.search.filter_params.exclude = {
            id__in: match_tree.map( function ( b ) { return b.id; })
        };
        return $scope.search.search_buildings();
    };
    var report_problems = function ( fault ) {
        console.log( String(fault) );
        $scope.$emit('app_error', { message: 'error with match'});
    };

     $scope.is_matched = function(building) {
       var result = false;
       for (var i = 0; i < $scope.detail.match_tree.length; ++i) {
         var temp = $scope.detail.match_tree[i];
         if (temp.id === building.id) {
           result = true;
         }
       }
       return result;
     };

    /**
     * toggle_match: calls $parent.toggle_match to create or destroy a match.
     *
     * - show saving indicator
     * - save match
     * - get new match_tree
     * - get updated search results
     * - stop showing save indicator
     *
     * @param {obj} building: the building to match or unmatch with $scope.building
     */
    $scope.detail.toggle_match = function( building ) {
        var source_target, create;
        $scope.$emit('show_saving');
        // if creating a match, source should be $scope.building, otherwise,
        // building should be removed from the tree
        // source_target = building.matched ? [$scope.building.id, building.id] : [building.id, $scope.building.id];
        source_target = [building.id, $scope.building.id];
        save_match( source_target[0], source_target[1], building.matches_current)
            .then( get_match_tree )
            .then( search_buildings )
            .then ( function ( data ) {
                // set the matching_list_table building as matched and add its
                // coparent, need access to ``building`` here
                $scope.building.matched = $scope.detail.match_tree.length > 0;
                if (building.matches_current) {
                    $scope.building.coparent = building;
                } else {
                    $scope.building.coparent = null;
                }
                $scope.$emit('finished_saving');
            })
            .catch ( report_problems );
    };

    /*
     * event from parent controller (matching_controller) to pass intial data
     * load.
     */
    $scope.$on('matching_loaded', function(event, data) {
        $scope.matching_buildings = data.matching_buildings.map(function (b) {
          b.matches_current = true;
        });
        $scope.building = data.building;
        angular.forEach($scope.search.buildings, function (building) {
          building.matches_current = $scope.is_matched(building);
        });
    });

    $scope.init = function() {
        // reload matches here
    };
}]);
