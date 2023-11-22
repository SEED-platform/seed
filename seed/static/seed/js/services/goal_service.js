/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.goal', []).factory('goal_service', [
    '$http',
    (
        $http, 
    ) => {
        const goal_service = {};

        goal_service.create_goal = (goal) => {
            return $http.post('/api/v3/goals/', goal)
                .then(response => response)
                .catch((response) => {
                    return response
                });

        }
        
        return goal_service
        }
    ]
)