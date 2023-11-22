/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.goal', []).factory('goal_service', [
    '$http',
    'user_service',
    (
        $http, 
        user_service,
    ) => {
        const goal_service = {};

        goal_service.create_goal = (goal) => {
            return $http.post('/api/v3/goals/', goal)
                .then(response => response)
                .catch((response) => response);
        }

        goal_service.update_goal = (goal) => {
            return $http.put(`/api/v3/goals/${goal.id}/`, goal)
                .then(response => response)
                .catch(response => response)
        }

        goal_service.get_goals = () => {
            return $http.get('/api/v3/goals/', {
                params: {
                    organization_id: user_service.get_organization().id
                }
            })
            .then(response => response.data)
            .catch(response => response);
        }

        goal_service.delete_goal = (goal_id) => {
            return $http.delete(`/api/v3/goals/${goal_id}`, {
                params: {
                    organization_id: user_service.get_organization().id
                } 
            })
            .then(response => response)
            .catch(response => response)
        }
        
        return goal_service
        }
    ]
)